import math

import pandas as pd
import pytest

from app.metrics import by_hour_of_day, error_histogram, summary


def pairs(*rows: tuple[str, float, float | None]) -> pd.DataFrame:
    """Build a pairs table like app.selection returns: (start_time, actual_mw, forecast_mw)."""
    df = pd.DataFrame({
        "start_time": [pd.Timestamp(t, tz="UTC") for t, _, _ in rows],
        "actual_mw": [a for _, a, _ in rows],
        "forecast_mw": [f for _, _, f in rows],
    })
    df["error_mw"] = df.forecast_mw - df.actual_mw
    return df


# Errors -100, 0, +100, +400 on an actual of 1000 MW, plus one hour with no forecast.
PAIRS = pairs(
    ("2026-01-10 00:00", 1000, 900),
    ("2026-01-10 01:00", 1000, 1000),
    ("2026-01-10 02:00", 1000, 1100),
    ("2026-01-10 03:00", 1000, 1400),
    ("2026-01-10 04:00", 1000, None),
)


def test_summary_matches_hand_calculation():
    s = summary(PAIRS)
    assert s["count"] == 4                                   # the hour without a forecast is skipped
    assert s["bias_mw"] == 100                               # (-100 + 0 + 100 + 400) / 4
    assert s["mae_mw"] == 150                                # (100 + 0 + 100 + 400) / 4
    assert s["rmse_mw"] == pytest.approx(math.sqrt(45_000))  # (10k + 0 + 10k + 160k) / 4
    assert s["nmae"] == 0.15                                 # 150 / 1000
    assert s["over_forecast_share"] == 0.5                   # +100 and +400; 0 is not "over"


def test_percentiles_use_linear_interpolation():
    # Sorted errors [-100, 0, 100, 400]; P90 sits 70% of the way from 100 to 400.
    s = summary(PAIRS)
    assert s["p10_mw"] == pytest.approx(-70)
    assert s["p50_mw"] == pytest.approx(50)
    assert s["p90_mw"] == pytest.approx(310)
    assert s["safety_margin_mw"] == pytest.approx(310)


def test_safety_margin_is_zero_when_forecast_is_usually_too_low():
    low = pairs(*[(f"2026-01-10 {h:02d}:00", 1000, 500) for h in range(10)])
    assert summary(low)["safety_margin_mw"] == 0


def test_by_hour_of_day():
    two_days = pairs(
        ("2026-01-10 05:00", 1000, 1200),  # +200
        ("2026-01-11 05:00", 1000, 900),   # -100
        ("2026-01-10 06:00", 1000, 1000),  #    0
    )
    result = by_hour_of_day(two_days).set_index("hour")
    assert result.loc[5, "bias_mw"] == 50   # (200 - 100) / 2
    assert result.loc[5, "mae_mw"] == 150   # (200 + 100) / 2
    assert result.loc[6, "mae_mw"] == 0


def test_error_histogram_bins():
    hist = error_histogram(PAIRS, bin_mw=500)
    # -100 falls in [-500, 0); 0, 100 and 400 fall in [0, 500).
    assert dict(zip(hist.bin_start_mw, hist["count"])) == {-500: 1, 0: 3}


def test_error_histogram_includes_empty_bins():
    gap = pairs(("2026-01-10 00:00", 1000, 1100), ("2026-01-10 01:00", 1000, 2200))  # +100, +1200
    hist = error_histogram(gap, bin_mw=500)
    assert dict(zip(hist.bin_start_mw, hist["count"])) == {0: 1, 500: 0, 1000: 1}
