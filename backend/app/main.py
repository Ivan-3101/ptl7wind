"""FastAPI app. Endpoints are listed in docs/DESIGN.md section 8; interactive docs at /api/docs."""

from datetime import date, time
from functools import lru_cache
from typing import Literal

import pandas as pd
from fastapi import FastAPI, HTTPException, Query

from app import schemas
from app.correction import WINDOW_DAYS, corrected_pairs
from app.data import load_actuals, load_forecasts
from app.metrics import by_hour_of_day, error_histogram, horizon_curve, summary
from app.selection import decision_cutoffs, decision_pairs, horizon_pairs

DEFAULT_GATE = time(9, 20)
GATE_PRESETS = [
    schemas.GatePreset(label="EPEX", time=time(9, 20)),
    schemas.GatePreset(label="N2EX", time=time(9, 50)),
]
MAX_HORIZON_H = 48

app = FastAPI(
    title="UK Wind Forecast Monitor API",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


# ---------- helpers ----------

def _date_range() -> tuple[date, date]:
    days = load_actuals().start_time.dt.date
    return days.min(), days.max()


def _check_in_range(*days: date) -> None:
    first, last = _date_range()
    for day in days:
        if not first <= day <= last:
            raise HTTPException(422, f"{day} is outside the available range {first} to {last}")


def _resolve_range(start: date | None, end: date | None) -> tuple[date, date]:
    """Missing start/end default to the whole snapshot."""
    first, last = _date_range()
    start, end = start or first, end or last
    _check_in_range(start, end)
    if start > end:
        raise HTTPException(422, "start must be on or before end")
    return start, end


def _in_dates(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    """Rows whose start_time falls on a day from start to end (inclusive)."""
    days = df.start_time.dt.date
    return df[(days >= start) & (days <= end)]


def _records(df: pd.DataFrame) -> list[dict]:
    """DataFrame rows as dicts, with NaN/NaT turned into None (JSON null)."""
    return df.astype(object).where(df.notna(), None).to_dict("records")


# ---------- endpoints ----------

@app.get("/api/meta", response_model=schemas.Meta)
def meta():
    first, last = _date_range()
    return schemas.Meta(
        first_date=first,
        last_date=last,
        default_gate=DEFAULT_GATE,
        gate_presets=GATE_PRESETS,
        max_horizon_h=MAX_HORIZON_H,
    )


@app.get("/api/day-ahead", response_model=schemas.DayAhead)
def day_ahead(day: date = Query(alias="date"), gate: time = DEFAULT_GATE):
    """One delivery day: actuals vs the latest forecast published before gate closure on D-1."""
    _check_in_range(day)
    day_actuals = _in_dates(load_actuals(), day, day)
    raw = _in_dates(_all_decision_pairs(gate), day, day)
    # The correction needs earlier days' errors, so it is computed over the whole snapshot.
    corrected = _in_dates(corrected_pairs(_all_decision_pairs(gate)), day, day)
    correction = corrected.bias_correction_mw.iloc[0]
    has_correction = bool(pd.notna(correction))
    cutoff = decision_cutoffs(pd.Series([pd.Timestamp(day, tz="UTC")]), gate).iloc[0]
    return {
        "date": day,
        "gate": gate,
        "cutoff": cutoff,
        "actuals": _records(day_actuals.rename(columns={"generation_mw": "actual_mw"})),
        "hours": _records(raw.assign(corrected_forecast_mw=corrected.forecast_mw)),
        "summary": summary(raw),
        "bias_correction_mw": float(correction) if has_correction else None,
        "corrected_summary": summary(corrected) if has_correction else None,
    }


@app.get("/api/accuracy", response_model=schemas.Accuracy)
def accuracy(
    mode: Literal["decision", "horizon"] = "decision",
    gate: time = DEFAULT_GATE,
    horizon: float = Query(24, ge=0, le=MAX_HORIZON_H),
    start: date | None = None,
    end: date | None = None,
):
    """Accuracy over a date range, using the forecast at gate closure or at a fixed horizon."""
    actuals = _in_dates(load_actuals(), *_resolve_range(start, end))
    if mode == "decision":
        pairs = decision_pairs(actuals, load_forecasts(), gate)
    else:
        pairs = horizon_pairs(actuals, load_forecasts(), horizon)
    return {
        "mode": mode,
        "summary": summary(pairs),
        "by_hour": _records(by_hour_of_day(pairs)),
        "histogram": _records(error_histogram(pairs)),
    }


@app.get("/api/accuracy/by-horizon", response_model=list[schemas.HorizonPoint])
def accuracy_by_horizon(start: date | None = None, end: date | None = None):
    """Bias and MAE for horizons 0..48h: how accuracy changes with lead time."""
    return _records(_horizon_curve(*_resolve_range(start, end)))


@app.get("/api/accuracy/bias-correction", response_model=schemas.BiasCorrection)
def bias_correction(gate: time = DEFAULT_GATE, start: date | None = None, end: date | None = None):
    """Experimental backtest: official forecast vs forecast corrected for its recent bias.

    Both are scored on the same hours: those in the period that have a full history window.
    """
    start, end = _resolve_range(start, end)
    raw = _all_decision_pairs(gate)
    corrected = corrected_pairs(raw)
    has_history = corrected.forecast_mw.notna()
    first_available = corrected[has_history].start_time.min().date()
    raw, corrected = _in_dates(raw[has_history], start, end), _in_dates(corrected[has_history], start, end)
    days = raw.start_time.dt.date.nunique()
    return {
        "window_days": WINDOW_DAYS,
        "first_available_date": first_available,
        "days": days,
        "raw": summary(raw) if days else None,
        "corrected": summary(corrected) if days else None,
    }


# Decision-mode pairs for the whole snapshot, per gate. Cached: the snapshot never changes.
@lru_cache(maxsize=16)
def _all_decision_pairs(gate: time) -> pd.DataFrame:
    return decision_pairs(load_actuals(), load_forecasts(), gate)


# 49 selection runs per call, so results are cached: the snapshot never changes.
@lru_cache(maxsize=32)
def _horizon_curve(start: date, end: date) -> pd.DataFrame:
    actuals = _in_dates(load_actuals(), start, end)
    return horizon_curve(actuals, load_forecasts(), list(range(MAX_HORIZON_H + 1)))
