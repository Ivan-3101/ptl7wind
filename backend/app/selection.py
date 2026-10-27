"""The core rule: for each target hour, use the latest forecast published at or before a cutoff.

Two ways to choose the cutoff (see docs/DESIGN.md section 5):
  decision mode - gate closure on the day before delivery (what the buyer actually had)
  horizon mode  - a fixed number of hours before the target (accuracy vs lead time)
"""

from datetime import time

import pandas as pd


def decision_cutoffs(targets: pd.Series, gate: time) -> pd.Series:
    """Gate closure on D-1 for each target, e.g. Jan 10 14:00 with 09:20 gate -> Jan 9 09:20."""
    day_before = targets.dt.normalize() - pd.Timedelta(days=1)
    return day_before + pd.Timedelta(hours=gate.hour, minutes=gate.minute)


def horizon_cutoffs(targets: pd.Series, hours: float) -> pd.Series:
    return targets - pd.Timedelta(hours=hours)


def decision_pairs(actuals: pd.DataFrame, forecasts: pd.DataFrame, gate: time) -> pd.DataFrame:
    hourly = _hourly_actuals(actuals)
    return _pair(hourly, forecasts, decision_cutoffs(hourly.start_time, gate))


def horizon_pairs(actuals: pd.DataFrame, forecasts: pd.DataFrame, hours: float) -> pd.DataFrame:
    hourly = _hourly_actuals(actuals)
    return _pair(hourly, forecasts, horizon_cutoffs(hourly.start_time, hours))


def _hourly_actuals(actuals: pd.DataFrame) -> pd.DataFrame:
    """Forecasts are hourly, so only on-the-hour actuals are scored (DESIGN.md A1)."""
    on_the_hour = actuals[actuals.start_time.dt.minute == 0]
    return on_the_hour.rename(columns={"generation_mw": "actual_mw"}).reset_index(drop=True)


def _pair(hourly: pd.DataFrame, forecasts: pd.DataFrame, cutoffs: pd.Series) -> pd.DataFrame:
    """Attach to each hourly actual the latest forecast with publish_time <= its cutoff.

    Returns one row per target hour with columns:
      start_time, actual_mw, cutoff, publish_time, forecast_mw, horizon_h, error_mw
    Targets with no forecast before their cutoff keep NaN/NaT instead of a later forecast.
    """
    # merge_asof needs both sides sorted by the time it matches on.
    left = hourly.assign(cutoff=cutoffs).sort_values("cutoff")
    right = forecasts.rename(columns={"generation_mw": "forecast_mw"}).sort_values("publish_time")

    paired = pd.merge_asof(
        left,
        right,
        left_on="cutoff",
        right_on="publish_time",
        by="start_time",          # only match forecasts for the same target hour
        direction="backward",     # latest publish_time <= cutoff, never after
    )

    paired = paired.sort_values("start_time").reset_index(drop=True)
    paired["horizon_h"] = (paired.start_time - paired.publish_time).dt.total_seconds() / 3600
    paired["error_mw"] = paired.forecast_mw - paired.actual_mw
    return paired
