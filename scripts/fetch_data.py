"""Download the January 2026 wind data from Elexon BMRS into data/*.csv.

Run once from the repo root:  python scripts/fetch_data.py

The CSVs are a faithful snapshot of the API: only column renaming and sorting happen
here. All business rules (dropping past targets, picking the forecast) live in the
backend so they are tested in one place.
"""

from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Decisions made 1-31 Jan 2026 are for delivery days 2 Jan - 1 Feb 2026.
ACTUALS_PARAMS = {
    "settlementDateFrom": "2026-01-02",
    "settlementDateTo": "2026-02-01",
    "fuelType": "WIND",
}
# Forecasts are filtered by publish time. Start 3 days early so 48h-ahead forecasts for
# 2 Jan exist; end on 1 Feb so forecasts close to the last delivery day are included.
FORECASTS_PARAMS = {
    "publishDateTimeFrom": "2025-12-30T00:00:00Z",
    "publishDateTimeTo": "2026-02-01T23:59:59Z",
}


def fetch(dataset: str, params: dict) -> pd.DataFrame:
    response = requests.get(f"{BASE_URL}/{dataset}/stream", params=params, timeout=60)
    response.raise_for_status()
    return pd.DataFrame(response.json())


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)

    actuals = (
        fetch("FUELHH", ACTUALS_PARAMS)
        .rename(columns={"startTime": "start_time", "generation": "generation_mw"})
        [["start_time", "generation_mw"]]
        .sort_values("start_time")
    )
    forecasts = (
        fetch("WINDFOR", FORECASTS_PARAMS)
        .rename(columns={
            "publishTime": "publish_time",
            "startTime": "start_time",
            "generation": "generation_mw",
        })
        [["publish_time", "start_time", "generation_mw"]]
        .sort_values(["publish_time", "start_time"])
    )

    actuals.to_csv(DATA_DIR / "actuals.csv", index=False)
    forecasts.to_csv(DATA_DIR / "forecasts.csv", index=False)

    print(f"actuals:   {len(actuals):>6} rows  {actuals.start_time.min()} -> {actuals.start_time.max()}")
    print(f"forecasts: {len(forecasts):>6} rows  {forecasts.publish_time.nunique()} publishes  "
          f"{forecasts.publish_time.min()} -> {forecasts.publish_time.max()}")


if __name__ == "__main__":
    main()
