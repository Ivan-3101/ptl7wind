"""Response models: the API contract the frontend relies on. Shown at /api/docs."""

from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel


class GatePreset(BaseModel):
    label: str
    time: time


class Meta(BaseModel):
    first_date: date
    last_date: date
    default_gate: time
    gate_presets: list[GatePreset]
    max_horizon_h: int


class Summary(BaseModel):
    count: int
    bias_mw: float
    mae_mw: float
    rmse_mw: float
    nmae: float
    over_forecast_share: float  # fraction of hours where forecast > actual
    p10_mw: float
    p50_mw: float
    p90_mw: float
    safety_margin_mw: float


class ActualPoint(BaseModel):
    start_time: datetime
    actual_mw: float


class HourPoint(BaseModel):
    start_time: datetime
    actual_mw: float
    forecast_mw: float | None
    error_mw: float | None
    publish_time: datetime | None
    horizon_h: float | None
    corrected_forecast_mw: float | None  # experimental bias correction; None without history


class DayAhead(BaseModel):
    date: date
    gate: time
    cutoff: datetime
    actuals: list[ActualPoint]  # every half-hour, for the chart line
    hours: list[HourPoint]      # on-the-hour actual vs selected forecast
    summary: Summary
    bias_correction_mw: float | None  # None when there is not enough history yet
    corrected_summary: Summary | None


class BiasCorrection(BaseModel):
    window_days: int
    first_available_date: date
    days: int                   # delivery days in the requested period that could be corrected
    raw: Summary | None         # the official forecast, on those same days
    corrected: Summary | None


class HourOfDay(BaseModel):
    hour: int
    bias_mw: float
    mae_mw: float


class HistogramBin(BaseModel):
    bin_start_mw: int
    count: int


class Accuracy(BaseModel):
    mode: Literal["decision", "horizon"]
    summary: Summary
    by_hour: list[HourOfDay]
    histogram: list[HistogramBin]


class HorizonPoint(BaseModel):
    horizon_h: float
    bias_mw: float
    mae_mw: float
    count: int
