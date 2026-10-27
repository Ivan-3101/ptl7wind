import { useState } from 'react'
import { useAccuracy, useHorizonCurve } from '../api/client'
import type { Meta, Summary } from '../api/types'
import { ErrorHistogram } from '../charts/ErrorHistogram'
import { HorizonChart } from '../charts/HorizonChart'
import { HourOfDayChart } from '../charts/HourOfDayChart'
import { BiasCorrectionPanel } from '../components/BiasCorrectionPanel'
import { ChartCard } from '../components/ChartCard'
import { GateComparison } from '../components/GateComparison'
import { StatCard } from '../components/StatCard'
import { formatGW, formatMW, formatPercent, formatSignedMW } from '../format'

interface Props {
  meta: Meta
  gate: string // "HH:MM"
}

type Mode = 'decision' | 'horizon'

/** Bids for hour 00:00 of D are placed (24 - gate) hours ahead, for 23:00 (47 - gate) hours ahead. */
function bidWindow(gate: string): [number, number] {
  const [h, m] = gate.split(':').map(Number)
  const gateHours = h + m / 60
  return [24 - gateHours, 47 - gateHours]
}

function headline(s: Summary, mode: Mode, gate: string, horizon: number): string {
  const when = mode === 'decision' ? `With bids due at ${gate} the day before` : `Using forecasts made ${horizon}h ahead`
  const tooHigh = s.bias_mw > 0
  const share = tooHigh ? s.over_forecast_share : 1 - s.over_forecast_share
  const margin = s.safety_margin_mw > 0
    ? ` To be covered in 90% of hours, plan for wind about ${formatGW(s.safety_margin_mw)} below the forecast.`
    : ''
  return `${when}, the forecast was too ${tooHigh ? 'high' : 'low'} in ${formatPercent(share)} of hours, ` +
    `by ${formatGW(Math.abs(s.bias_mw))} on average (typical miss ${formatGW(s.mae_mw)}).${margin}`
}

/** Purpose 2: how accurate are the forecasts, and how much margin should a buyer plan for? */
export function AccuracyView({ meta, gate }: Props) {
  const [start, setStart] = useState(meta.first_date)
  const [end, setEnd] = useState(meta.last_date)
  const [mode, setMode] = useState<Mode>('decision')
  const [horizon, setHorizon] = useState(24)

  const accuracy = useAccuracy(
    mode === 'decision' ? { mode, gate, start, end } : { mode, horizon, start, end },
  )
  const curve = useHorizonCurve(start, end)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3 text-sm">
        <label className="flex items-center gap-2">
          <span className="text-slate-500">Period</span>
          <input
            type="date" value={start} min={meta.first_date} max={end}
            onChange={(e) => e.target.value && setStart(e.target.value)}
            className="rounded-md border border-slate-300 bg-white px-2 py-1"
          />
          <span className="text-slate-400">to</span>
          <input
            type="date" value={end} min={start} max={meta.last_date}
            onChange={(e) => e.target.value && setEnd(e.target.value)}
            className="rounded-md border border-slate-300 bg-white px-2 py-1"
          />
        </label>

        <div className="flex items-center gap-2">
          <span className="text-slate-500">Score the forecast</span>
          {(['decision', 'horizon'] as const).map((m) => (
            <button
              key={m} onClick={() => setMode(m)}
              className={`rounded-md border px-2.5 py-1 font-medium ${
                mode === m ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-300 bg-white text-slate-700'
              }`}
            >
              {m === 'decision' ? 'available at gate closure' : 'at a fixed lead time'}
            </button>
          ))}
          {mode === 'horizon' && (
            <label className="flex items-center gap-2">
              <input
                type="range" min={0} max={meta.max_horizon_h} value={horizon}
                onChange={(e) => setHorizon(Number(e.target.value))}
              />
              <span className="w-10 font-medium tabular-nums">{horizon}h</span>
            </label>
          )}
        </div>
      </div>

      {accuracy.isError && <p className="text-red-600">{accuracy.error.message}</p>}
      {accuracy.data && (() => {
        const s = accuracy.data.summary
        return (
          <>
            <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-amber-950">
              {headline(s, mode, gate, horizon)}
            </p>

            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <StatCard label="Mean absolute error" value={formatMW(s.mae_mw)} hint={`over ${s.count} hours`} />
              <StatCard label="Normalised MAE" value={formatPercent(s.nmae)} hint="MAE ÷ average actual wind" />
              <StatCard
                label="Bias" value={formatSignedMW(s.bias_mw)} tone={s.bias_mw > 0 ? 'warn' : 'default'}
                hint={`too high in ${formatPercent(s.over_forecast_share)} of hours`}
              />
              <StatCard
                label="Safety margin (P90)" value={formatMW(s.safety_margin_mw)}
                hint="covers 90% of over-forecasts"
              />
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <ChartCard
                title="Error vs lead time"
                subtitle="Forecasts made further ahead are less accurate. The shaded band is where your bids sit."
              >
                {curve.data && (
                  <HorizonChart
                    data={curve.data} bidWindow={bidWindow(gate)}
                    selectedHorizon={mode === 'horizon' ? horizon : undefined}
                  />
                )}
              </ChartCard>
              <ChartCard
                title="How big are the misses?"
                subtitle="Hours per error size. Amber = forecast too high, blue = too low."
              >
                <ErrorHistogram bins={accuracy.data.histogram} p10={s.p10_mw} p90={s.p90_mw} />
              </ChartCard>
              <ChartCard title="Error by hour of day" subtitle="Which hours of the day are hardest to forecast.">
                <HourOfDayChart data={accuracy.data.by_hour} />
              </ChartCard>
              <ChartCard
                title="Does a later auction help?"
                subtitle="Accuracy of the forecast available at each auction's gate closure."
              >
                <GateComparison presets={meta.gate_presets} start={start} end={end} />
                <p className="mt-4 text-sm text-slate-500">
                  The later gate can use the 09:30 forecast, but it usually revises the 07:30 one by only a few
                  hundred MW, small next to the typical error.
                </p>
              </ChartCard>
            </div>

            <ChartCard
              title="What if you corrected for recent bias? (experimental)"
              subtitle="Backtest of a simple correction, scored on the same days as the official forecast."
            >
              <BiasCorrectionPanel gate={gate} start={start} end={end} />
            </ChartCard>
          </>
        )
      })()}
    </div>
  )
}
