"""Accuracy metrics over (forecast, actual) pairs from app.selection (see docs/DESIGN.md section 6).

Error = forecast - actual, so a positive error means the forecast was too high.
"""

import numpy as np
import pandas as pd

from app.selection import horizon_pairs


def _scored(pairs: pd.DataFrame) -> pd.DataFrame:
    """Hours with no forecast before the cutoff cannot be scored."""
    return pairs.dropna(subset=["forecast_mw"])


def summary(pairs: pd.DataFrame) -> dict[str, float]:
    scored = _scored(pairs)
    error = scored.error_mw
    p10, p50, p90 = error.quantile([0.1, 0.5, 0.9])
    mae = error.abs().mean()
    return {
        "count": len(scored),
        "bias_mw": float(error.mean()),
        "mae_mw": float(mae),
        "rmse_mw": float(np.sqrt((error**2).mean())),
        "nmae": float(mae / scored.actual_mw.mean()),
        "over_forecast_share": float((error > 0).mean()),
        "p10_mw": float(p10),
        "p50_mw": float(p50),
        "p90_mw": float(p90),
        # In 90% of hours the forecast was at most p90 too high, so planning for wind this
        # much below forecast covers 90% of hours. Never negative: a forecast that is
        # usually too low needs no downward margin.
        "safety_margin_mw": float(max(p90, 0.0)),
    }


def by_hour_of_day(pairs: pd.DataFrame) -> pd.DataFrame:
    scored = _scored(pairs)
    return (
        scored.assign(hour=scored.start_time.dt.hour, abs_error=scored.error_mw.abs())
        .groupby("hour")
        .agg(bias_mw=("error_mw", "mean"), mae_mw=("abs_error", "mean"))
        .reset_index()
    )


def error_histogram(pairs: pd.DataFrame, bin_mw: int = 500) -> pd.DataFrame:
    """Count of hours per error bin, e.g. bin 500 = errors in [500, 1000) MW.

    Empty bins between the smallest and largest error are included with count 0, so a
    chart of the result shows the true shape of the distribution.
    """
    error = _scored(pairs).error_mw
    bins = (np.floor(error / bin_mw) * bin_mw).astype(int)
    all_bins = range(bins.min(), bins.max() + bin_mw, bin_mw)
    counts = bins.value_counts().reindex(all_bins, fill_value=0)
    return pd.DataFrame({"bin_start_mw": counts.index, "count": counts.values})


def horizon_curve(actuals: pd.DataFrame, forecasts: pd.DataFrame, hours: list[float]) -> pd.DataFrame:
    """Bias and MAE when using the latest forecast made at least h hours before each target."""
    rows = []
    for h in hours:
        s = summary(horizon_pairs(actuals, forecasts, h))
        rows.append({"horizon_h": h, "bias_mw": s["bias_mw"], "mae_mw": s["mae_mw"], "count": s["count"]})
    return pd.DataFrame(rows)
