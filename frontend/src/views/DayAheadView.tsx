import { useState } from 'react'
import { useBiasCorrection, useDayAhead } from '../api/client'
import type { DayAhead, HourPoint, Meta } from '../api/types'
import { ForecastVsActualChart } from '../charts/ForecastVsActualChart'
import { ChartCard } from '../components/ChartCard'
import { StatCard } from '../components/StatCard'
import { addDays, formatDate, formatDateTime, formatHour, formatMW, formatSignedMW } from '../format'

interface Props {
  meta: Meta
  gate: string
}

/** Explains the experimental correction for this day, or why it is not available yet. */
function CorrectionNote({ data, gate }: { data: DayAhead; gate: string }) {
  const backtest = useBiasCorrection(gate)
  const window = backtest.data?.window_days ?? 14
  if (data.bias_correction_mw === null || data.corrected_summary === null) {
    return (
      <p className="mb-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
        Needs {window} complete days of history before the bid
        {backtest.data && <>, so it is available from {formatDate(backtest.data.first_available_date)}</>}.
      </p>
    )
  }
  const correction = data.bias_correction_mw
  return (
    <p className="mb-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
      Over the {window} complete days known when bids were due, the forecast ran{' '}
      <strong>{formatMW(Math.abs(correction))} too {correction > 0 ? 'high' : 'low'}</strong> on average, so the
      corrected forecast {correction > 0 ? 'lowers' : 'raises'} it by that amount. Typical miss today:{' '}
      <strong>{formatMW(data.corrected_summary.mae_mw)}</strong> corrected vs{' '}
      <strong>{formatMW(data.summary.mae_mw)}</strong> official.
    </p>
  )
}

/** Purpose 1: what did the forecast say when the bids for this delivery day were due? */
export function DayAheadView({ meta, gate }: Props) {
  const [day, setDay] = useState(meta.first_date)
  const [showCorrected, setShowCorrected] = useState(false)
  const dayAhead = useDayAhead(day, gate)

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <span className="text-sm text-slate-500">Delivery day</span>
        <button
          onClick={() => setDay(addDays(day, -1))} disabled={day <= meta.first_date}
          className="rounded-md border border-slate-300 bg-white px-2 py-1 disabled:opacity-40" aria-label="Previous day"
        >◀</button>
        <input
          type="date" value={day} min={meta.first_date} max={meta.last_date}
          onChange={(e) => e.target.value && setDay(e.target.value)}
          className="rounded-md border border-slate-300 bg-white px-2 py-1"
        />
        <button
          onClick={() => setDay(addDays(day, 1))} disabled={day >= meta.last_date}
          className="rounded-md border border-slate-300 bg-white px-2 py-1 disabled:opacity-40" aria-label="Next day"
        >▶</button>
        <span className="font-medium text-slate-900">{formatDate(day)}</span>
      </div>

      {dayAhead.isPending && <p className="text-slate-500">Loading…</p>}
      {dayAhead.isError && <p className="text-red-600">{dayAhead.error.message}</p>}
      {dayAhead.data && (() => {
        const { cutoff, hours, actuals, summary } = dayAhead.data
        const scored = hours.filter((h): h is HourPoint & { error_mw: number } => h.error_mw !== null)
        if (scored.length === 0) {
          return <p className="text-slate-500">No forecast had been published before this gate closure.</p>
        }
        const worst = scored.reduce((a, b) => (Math.abs(b.error_mw) > Math.abs(a.error_mw) ? b : a))
        const publishTimes = [...new Set(scored.map((h) => h.publish_time!))]
        return (
          <>
            <div className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
              Bids for this day were due <strong>{formatDateTime(cutoff)}</strong>. The latest wind forecast
              available then was published <strong>{publishTimes.map(formatDateTime).join(', ')}</strong>.
              Later forecasts are ignored: they did not exist when the decision was made.
            </div>

            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <StatCard label="Mean absolute error" value={formatMW(summary.mae_mw)} hint="typical miss per hour" />
              <StatCard
                label="Bias" value={formatSignedMW(summary.bias_mw)} tone={summary.bias_mw > 0 ? 'warn' : 'default'}
                hint={summary.bias_mw > 0 ? 'forecast too high on average' : 'forecast too low on average'}
              />
              <StatCard
                label="Largest miss" value={formatSignedMW(worst.error_mw)}
                hint={`at ${formatHour(worst.start_time)}`}
              />
              <StatCard
                label="Hours over-forecast" value={`${scored.filter((h) => h.error_mw > 0).length} / ${scored.length}`}
                hint="forecast above actual"
              />
            </div>

            <ChartCard title="Forecast vs actual wind generation" subtitle="Shaded area = forecast error. Times in UK time.">
              <label className="mb-3 flex w-fit cursor-pointer items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={showCorrected} onChange={(e) => setShowCorrected(e.target.checked)} />
                Show bias-corrected forecast <span className="text-xs text-emerald-700">(experimental)</span>
              </label>
              {showCorrected && <CorrectionNote data={dayAhead.data} gate={gate} />}
              <ForecastVsActualChart actuals={actuals} hours={hours} showCorrected={showCorrected} />
            </ChartCard>

            <details className="rounded-xl border border-slate-200 bg-white p-4 text-sm shadow-sm">
              <summary className="cursor-pointer font-medium text-slate-700">Hourly table</summary>
              <table className="mt-3 w-full text-right tabular-nums">
                <thead className="text-xs uppercase text-slate-500">
                  <tr>
                    <th className="text-left">Hour</th><th>Actual</th><th>Forecast</th><th>Error</th><th>Horizon</th>
                  </tr>
                </thead>
                <tbody>
                  {scored.map((h) => (
                    <tr key={h.start_time} className="border-t border-slate-100">
                      <td className="py-1 text-left">{formatHour(h.start_time)}</td>
                      <td>{formatMW(h.actual_mw)}</td>
                      <td>{formatMW(h.forecast_mw!)}</td>
                      <td className={h.error_mw > 0 ? 'text-amber-600' : 'text-slate-700'}>{formatSignedMW(h.error_mw)}</td>
                      <td>{h.horizon_h}h</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          </>
        )
      })()}
    </div>
  )
}
