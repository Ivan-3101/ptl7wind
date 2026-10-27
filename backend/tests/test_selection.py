from datetime import time

import pandas as pd

from app.data import clean_forecasts
from app.selection import decision_cutoffs, decision_pairs, horizon_pairs

GATE_EPEX = time(9, 20)
GATE_N2EX = time(9, 50)


def ts(value: str) -> pd.Timestamp:
    return pd.Timestamp(value, tz="UTC")


def actuals(*rows: tuple[str, float]) -> pd.DataFrame:
    return pd.DataFrame(
        {"start_time": [ts(t) for t, _ in rows], "generation_mw": [g for _, g in rows]}
    )


def forecasts(*rows: tuple[str, str, float]) -> pd.DataFrame:
    return pd.DataFrame({
        "publish_time": [ts(p) for p, _, _ in rows],
        "start_time": [ts(t) for _, t, _ in rows],
        "generation_mw": [g for _, _, g in rows],
    })


# Jan 10 14:00 target with the forecasts seen in the real data around the gate.
TARGET = "2026-01-10 14:00"
ACTUALS = actuals((TARGET, 8035))
FORECASTS = forecasts(
    ("2026-01-09 04:30", TARGET, 6797),
    ("2026-01-09 07:30", TARGET, 6882),
    ("2026-01-09 09:30", TARGET, 7000),
    ("2026-01-10 11:30", TARGET, 8788),
)


def test_decision_cutoff_is_gate_on_previous_day_for_every_hour():
    targets = pd.Series([ts("2026-01-10 00:00"), ts("2026-01-10 23:00")])
    assert list(decision_cutoffs(targets, GATE_EPEX)) == [ts("2026-01-09 09:20")] * 2


def test_picks_latest_forecast_before_gate():
    row = decision_pairs(ACTUALS, FORECASTS, GATE_EPEX).iloc[0]
    assert row.publish_time == ts("2026-01-09 07:30")
    assert row.forecast_mw == 6882


def test_later_gate_picks_later_forecast():
    row = decision_pairs(ACTUALS, FORECASTS, GATE_N2EX).iloc[0]
    assert row.publish_time == ts("2026-01-09 09:30")


def test_forecast_published_exactly_at_cutoff_is_usable():
    fc = forecasts(("2026-01-09 09:20", TARGET, 7100))
    assert decision_pairs(ACTUALS, fc, GATE_EPEX).iloc[0].forecast_mw == 7100


def test_forecast_published_one_minute_after_cutoff_is_never_used():
    fc = forecasts(("2026-01-09 09:21", TARGET, 7100))
    row = decision_pairs(ACTUALS, fc, GATE_EPEX).iloc[0]
    assert pd.isna(row.forecast_mw)
    assert pd.isna(row.publish_time)


def test_forecast_for_another_hour_is_never_used():
    fc = forecasts(("2026-01-09 07:30", "2026-01-10 15:00", 7100))
    assert pd.isna(decision_pairs(ACTUALS, fc, GATE_EPEX).iloc[0].forecast_mw)


def test_half_hour_actuals_are_not_scored():
    acts = actuals((TARGET, 8035), ("2026-01-10 14:30", 8100))
    pairs = decision_pairs(acts, FORECASTS, GATE_EPEX)
    assert list(pairs.start_time) == [ts(TARGET)]


def test_error_and_horizon():
    row = decision_pairs(ACTUALS, FORECASTS, GATE_EPEX).iloc[0]
    assert row.error_mw == 6882 - 8035  # negative: forecast too low
    assert row.horizon_h == 30.5         # Jan 9 07:30 -> Jan 10 14:00


def test_horizon_mode_uses_target_minus_hours():
    # 3h before 14:00 is 11:00, so the 11:30 forecast is too late and Jan 9 09:30 is latest.
    row = horizon_pairs(ACTUALS, FORECASTS, hours=3).iloc[0]
    assert row.publish_time == ts("2026-01-09 09:30")
    # 2h before is 12:00, so the 11:30 forecast becomes usable.
    row = horizon_pairs(ACTUALS, FORECASTS, hours=2).iloc[0]
    assert row.publish_time == ts("2026-01-10 11:30")


def test_clean_forecasts_drops_rows_not_in_the_future():
    fc = forecasts(
        ("2026-01-09 07:30", "2026-01-09 06:00", 1),  # target in the past
        ("2026-01-09 07:30", "2026-01-09 07:30", 2),  # target == publish
        ("2026-01-09 07:30", "2026-01-09 08:00", 3),  # real forecast
    )
    assert list(clean_forecasts(fc).generation_mw) == [3]
