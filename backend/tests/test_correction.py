from datetime import date, timedelta

import pandas as pd
import pytest

from app.correction import corrected_pairs, daily_corrections

FIRST_DAY = date(2026, 1, 1)


def pairs_with_daily_errors(errors: list[float]) -> pd.DataFrame:
    """Two hours per day; every hour on day i has error errors[i] (actual 1000 MW)."""
    rows = []
    for i, error in enumerate(errors):
        day = pd.Timestamp(FIRST_DAY + timedelta(days=i), tz="UTC")
        for hour in (0, 12):
            rows.append({"start_time": day + pd.Timedelta(hours=hour), "actual_mw": 1000.0,
                         "forecast_mw": 1000.0 + error, "error_mw": float(error)})
    return pd.DataFrame(rows)


def test_window_is_the_14_days_ending_two_days_before_delivery():
    errors = list(range(20))  # day i has error i
    corrections = daily_corrections(pairs_with_daily_errors(errors))
    # Day 16 uses days 1..14 (16-15 .. 16-2): mean of 1..14 = 7.5
    assert corrections[FIRST_DAY + timedelta(days=16)] == pytest.approx(7.5)


def test_no_correction_until_a_full_window_exists():
    corrections = daily_corrections(pairs_with_daily_errors([100] * 20))
    assert pd.isna(corrections[FIRST_DAY + timedelta(days=14)])
    assert corrections[FIRST_DAY + timedelta(days=15)] == 100


def test_day_before_delivery_and_later_days_do_not_affect_the_correction():
    # Bids for day D are made on D-1, before D-1's actuals are complete: no look-ahead.
    base = [100.0] * 20
    changed = base.copy()
    d = 17
    changed[d - 1] = 99_999  # D-1
    changed[d] = 99_999      # D itself
    changed[d + 1] = 99_999  # after D
    target = FIRST_DAY + timedelta(days=d)
    assert daily_corrections(pairs_with_daily_errors(changed))[target] == \
        daily_corrections(pairs_with_daily_errors(base))[target]


def test_corrected_pairs_subtracts_the_correction():
    pairs = pairs_with_daily_errors([200.0] * 16 + [500.0])
    last = corrected_pairs(pairs).iloc[-1]  # day 16, window days 1..14 all have error 200
    assert last.bias_correction_mw == 200
    assert last.forecast_mw == 1000 + 500 - 200
    assert last.error_mw == 300


def test_hours_without_history_stay_uncorrected_as_nan():
    first = corrected_pairs(pairs_with_daily_errors([200.0] * 16)).iloc[0]
    assert pd.isna(first.forecast_mw) and pd.isna(first.error_mw)
