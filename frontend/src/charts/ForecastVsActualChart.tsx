import {
  Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { ActualPoint, HourPoint } from '../api/types'
import { formatAxisGW, formatHour, formatMW } from '../format'

interface Props {
  actuals: ActualPoint[] // half-hourly
  hours: HourPoint[]     // hourly, with the forecast selected at gate closure
  showCorrected?: boolean
}

interface Row {
  t: number
  actual: number
  forecast?: number
  corrected?: number
  gap?: [number, number] // shaded band between forecast and actual
}

const THREE_HOURS = 3 * 60 * 60 * 1000

export function ForecastVsActualChart({ actuals, hours, showCorrected = false }: Props) {
  // One row per half-hour; forecasts exist only on the hour (they are hourly).
  const hourByTime = new Map(hours.map((h) => [Date.parse(h.start_time), h]))
  const rows: Row[] = actuals.map(({ start_time, actual_mw }) => {
    const t = Date.parse(start_time)
    const hour = hourByTime.get(t)
    const forecast = hour?.forecast_mw ?? undefined
    return {
      t,
      actual: actual_mw,
      forecast,
      corrected: hour?.corrected_forecast_mw ?? undefined,
      gap: forecast === undefined ? undefined : [Math.min(actual_mw, forecast), Math.max(actual_mw, forecast)],
    }
  })
  const ticks = rows.map((r) => r.t).filter((t) => (t - rows[0].t) % THREE_HOURS === 0)

  return (
    <ResponsiveContainer width="100%" height={340}>
      <ComposedChart data={rows} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="t" type="number" domain={['dataMin', 'dataMax']} ticks={ticks} tickFormatter={formatHour} />
        <YAxis tickFormatter={formatAxisGW} width={64} />
        <Tooltip labelFormatter={(t) => formatHour(Number(t))} formatter={(v) => formatMW(Number(v))} />
        <Legend />
        <Area
          dataKey="gap" name="Forecast error" fill="#fbbf24" fillOpacity={0.3} stroke="none"
          connectNulls tooltipType="none" isAnimationActive={false}
        />
        <Line dataKey="actual" name="Actual (half-hourly)" stroke="#0f172a" strokeWidth={2} dot={false} />
        <Line
          dataKey="forecast" name="Forecast available at gate" stroke="#0284c7" strokeWidth={2}
          strokeDasharray="6 4" dot={{ r: 2 }} connectNulls
        />
        {showCorrected && (
          <Line
            dataKey="corrected" name="Bias-corrected (experimental)" stroke="#059669" strokeWidth={2}
            strokeDasharray="2 3" dot={{ r: 2 }} connectNulls
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  )
}
