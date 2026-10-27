"""Cross-check on the full January snapshot.

The forecast-selection rule is re-implemented here as simply as possible (csv module and
loops, no pandas, no merge_asof). The pandas pipeline must give the same answers. If a
future change to app.selection or app.metrics breaks the rule, these tests fail.
"""

import csv
import math
from datetime import datetime, time, timedelta

import pytest

from app.data import DATA_DIR, load_actuals, load_forecasts
from app.metrics import summary
from app.selection import decision_pairs, horizon_pairs


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _load() -> tuple[dict, dict]:
    with open(DATA_DIR / "actuals.csv", newline="") as f:
        actual = {_ts(r["start_time"]): float(r["generation_mw"]) for r in csv.DictReader(f)}
    forecasts_by_target: dict[datetime, list[tuple[datetime, float]]] = {}
    with open(DATA_DIR / "forecasts.csv", newline="") as f:
        for r in csv.DictReader(f):
            published, target = _ts(r["publish_time"]), _ts(r["start_time"])
            if target > published:
                forecasts_by_target.setdefault(target, []).append((published, float(r["generation_mw"])))
    return actual, forecasts_by_target


ACTUAL, FORECASTS_BY_TARGET = _load()
TARGET_HOURS = sorted(t for t in ACTUAL if t.minute == 0)


def _naive_errors(cutoff_for) -> list[float]:
    """For each hour: the latest forecast published at or before its cutoff, minus actual."""
    errors = []
    for target in TARGET_HOURS:
        usable = [f for f in FORECASTS_BY_TARGET.get(target, []) if f[0] <= cutoff_for(target)]
        if usable:
            _, forecast = max(usable)  # max by publish time
            errors.append(forecast - ACTUAL[target])
    return errors


def _naive_quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = q * (len(ordered) - 1)
    low = math.floor(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _assert_matches(errors: list[float], result: dict) -> None:
    n = len(errors)
    assert result["count"] == n
    assert result["bias_mw"] == pytest.approx(sum(errors) / n)
    assert result["mae_mw"] == pytest.approx(sum(abs(e) for e in errors) / n)
    assert result["rmse_mw"] == pytest.approx(math.sqrt(sum(e * e for e in errors) / n))
    assert result["p90_mw"] == pytest.approx(_naive_quantile(errors, 0.9))


@pytest.mark.parametrize("gate", [time(9, 20), time(9, 50), time(0, 0), time(23, 59)])
def test_decision_mode_matches_reference(gate):
    def gate_on_day_before(target: datetime) -> datetime:
        midnight = target.replace(hour=0, minute=0)
        return midnight - timedelta(days=1) + timedelta(hours=gate.hour, minutes=gate.minute)

    expected = _naive_errors(gate_on_day_before)
    _assert_matches(expected, summary(decision_pairs(load_actuals(), load_forecasts(), gate)))


@pytest.mark.parametrize("hours", range(0, 49, 6))
def test_horizon_mode_matches_reference(hours):
    expected = _naive_errors(lambda target: target - timedelta(hours=hours))
    _assert_matches(expected, summary(horizon_pairs(load_actuals(), load_forecasts(), hours)))
