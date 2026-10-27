"""Endpoint tests against the real January snapshot in data/."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_meta():
    body = client.get("/api/meta").json()
    assert body["first_date"] == "2026-01-02"
    assert body["last_date"] == "2026-02-01"
    assert body["default_gate"] == "09:20:00"
    assert [p["label"] for p in body["gate_presets"]] == ["EPEX", "N2EX"]


def test_day_ahead_uses_forecast_from_before_gate():
    body = client.get("/api/day-ahead", params={"date": "2026-01-10", "gate": "09:20"}).json()
    assert body["cutoff"].startswith("2026-01-09T09:20")
    assert len(body["actuals"]) == 48   # half-hourly
    assert len(body["hours"]) == 24     # scored on the hour
    for hour in body["hours"]:
        assert hour["publish_time"] <= body["cutoff"]
    two_pm = next(h for h in body["hours"] if h["start_time"].startswith("2026-01-10T14:00"))
    assert two_pm["forecast_mw"] == 6882


def test_day_ahead_rejects_date_outside_snapshot():
    response = client.get("/api/day-ahead", params={"date": "2026-03-01"})
    assert response.status_code == 422
    assert "outside the available range" in response.json()["detail"]


def test_day_ahead_rejects_bad_gate():
    assert client.get("/api/day-ahead", params={"date": "2026-01-10", "gate": "25:99"}).status_code == 422


def test_accuracy_decision_mode():
    body = client.get("/api/accuracy").json()
    assert body["mode"] == "decision"
    assert body["summary"]["count"] == 744  # 31 days x 24 hours
    assert len(body["by_hour"]) == 24
    assert sum(b["count"] for b in body["histogram"]) == 744


def test_accuracy_horizon_mode_with_date_range():
    params = {"mode": "horizon", "horizon": 6, "start": "2026-01-10", "end": "2026-01-11"}
    body = client.get("/api/accuracy", params=params).json()
    assert body["mode"] == "horizon"
    assert body["summary"]["count"] == 48


def test_accuracy_rejects_horizon_above_48():
    assert client.get("/api/accuracy", params={"mode": "horizon", "horizon": 49}).status_code == 422


def test_accuracy_rejects_start_after_end():
    response = client.get("/api/accuracy", params={"start": "2026-01-20", "end": "2026-01-10"})
    assert response.status_code == 422


def test_day_ahead_bias_correction_only_with_full_history():
    early = client.get("/api/day-ahead", params={"date": "2026-01-10"}).json()
    assert early["bias_correction_mw"] is None
    assert early["corrected_summary"] is None
    assert all(h["corrected_forecast_mw"] is None for h in early["hours"])

    later = client.get("/api/day-ahead", params={"date": "2026-01-20"}).json()
    correction = later["bias_correction_mw"]
    for h in later["hours"]:
        assert h["corrected_forecast_mw"] == pytest.approx(h["forecast_mw"] - correction)


def test_bias_correction_backtest():
    body = client.get("/api/accuracy/bias-correction", params={"gate": "09:20"}).json()
    assert body["window_days"] == 14
    assert body["first_available_date"] == "2026-01-17"  # Jan 2 + 15 days
    assert body["days"] == 16                             # Jan 17 .. Feb 1
    assert body["raw"]["count"] == body["corrected"]["count"] == 16 * 24
    assert body["corrected"]["mae_mw"] < body["raw"]["mae_mw"]


def test_bias_correction_period_before_history_is_empty():
    body = client.get("/api/accuracy/bias-correction", params={"start": "2026-01-02", "end": "2026-01-10"}).json()
    assert body["days"] == 0
    assert body["raw"] is None and body["corrected"] is None


def test_accuracy_by_horizon():
    body = client.get("/api/accuracy/by-horizon").json()
    assert [p["horizon_h"] for p in body] == list(range(49))
    assert body[48]["mae_mw"] > body[0]["mae_mw"]  # further ahead = less accurate
