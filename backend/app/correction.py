"""Experimental: correct the forecast for its recent bias (see docs/DESIGN.md section 6).

corrected forecast = forecast - mean daily error over the previous WINDOW_DAYS complete days.

No look-ahead: bids for delivery day D are due on the morning of D-1, when D-1 is not yet
over, so the most recent complete day is D-2. The window for D is D-(WINDOW_DAYS+1) .. D-2.
"""

import pandas as pd

WINDOW_DAYS = 14


def daily_corrections(pairs: pd.DataFrame, window_days: int = WINDOW_DAYS) -> pd.Series:
    """Correction (MW) per delivery day, indexed by date. NaN until a full window exists.

    `pairs` must be decision-mode pairs covering every day, so the history is the forecast
    the buyer actually had on each earlier day.
    """
    daily_bias = pairs.groupby(pairs.start_time.dt.normalize()).error_mw.mean()
    daily_bias = daily_bias.asfreq("D")  # a missing day becomes NaN instead of being skipped
    rolling = daily_bias.rolling(window_days, min_periods=window_days).mean()
    corrections = rolling.shift(2)       # value for D uses days up to D-2
    corrections.index = corrections.index.date
    return corrections


def corrected_pairs(pairs: pd.DataFrame, window_days: int = WINDOW_DAYS) -> pd.DataFrame:
    """Same rows as `pairs`, with forecast_mw and error_mw replaced by the corrected values.

    Adds bias_correction_mw. Hours without enough history get NaN, so metrics skip them.
    """
    corrections = daily_corrections(pairs, window_days)
    correction = pairs.start_time.dt.date.map(corrections).astype(float)
    return pairs.assign(
        bias_correction_mw=correction,
        forecast_mw=pairs.forecast_mw - correction,
        error_mw=pairs.error_mw - correction,
    )
