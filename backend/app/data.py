"""Load the January snapshot from data/*.csv (see scripts/fetch_data.py)."""

from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def clean_forecasts(forecasts: pd.DataFrame) -> pd.DataFrame:
    """Drop rows whose target is not after the publish time: those are not forecasts."""
    return forecasts[forecasts.start_time > forecasts.publish_time].reset_index(drop=True)


# Loaded once per process and shared between requests. Callers must not modify the result.
@lru_cache(maxsize=1)
def load_actuals() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "actuals.csv", parse_dates=["start_time"])


@lru_cache(maxsize=1)
def load_forecasts() -> pd.DataFrame:
    forecasts = pd.read_csv(DATA_DIR / "forecasts.csv", parse_dates=["publish_time", "start_time"])
    return clean_forecasts(forecasts)
