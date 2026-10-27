// Mirrors backend/app/schemas.py. Dates are "YYYY-MM-DD", times "HH:MM:SS", datetimes ISO 8601 UTC.

export interface GatePreset {
  label: string
  time: string
}

export interface Meta {
  first_date: string
  last_date: string
  default_gate: string
  gate_presets: GatePreset[]
  max_horizon_h: number
}

export interface Summary {
  count: number
  bias_mw: number
  mae_mw: number
  rmse_mw: number
  nmae: number
  over_forecast_share: number
  p10_mw: number
  p50_mw: number
  p90_mw: number
  safety_margin_mw: number
}

export interface ActualPoint {
  start_time: string
  actual_mw: number
}

export interface HourPoint {
  start_time: string
  actual_mw: number
  forecast_mw: number | null
  error_mw: number | null
  publish_time: string | null
  horizon_h: number | null
  corrected_forecast_mw: number | null
}

export interface DayAhead {
  date: string
  gate: string
  cutoff: string
  actuals: ActualPoint[]
  hours: HourPoint[]
  summary: Summary
  bias_correction_mw: number | null
  corrected_summary: Summary | null
}

export interface BiasCorrection {
  window_days: number
  first_available_date: string
  days: number
  raw: Summary | null
  corrected: Summary | null
}

export interface HourOfDay {
  hour: number
  bias_mw: number
  mae_mw: number
}

export interface HistogramBin {
  bin_start_mw: number
  count: number
}

export interface Accuracy {
  mode: 'decision' | 'horizon'
  summary: Summary
  by_hour: HourOfDay[]
  histogram: HistogramBin[]
}

export interface HorizonPoint {
  horizon_h: number
  bias_mw: number
  mae_mw: number
  count: number
}
