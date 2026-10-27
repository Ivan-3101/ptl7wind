import { useBiasCorrection } from '../api/client'
import type { Summary } from '../api/types'
import { formatDate, formatMW, formatSignedMW } from '../format'

interface Props {
  gate: string
  start: string
  end: string
}

const ROWS: { label: string; pick: (s: Summary) => number; format: (mw: number) => string }[] = [
  { label: 'Mean absolute error', pick: (s) => s.mae_mw, format: formatMW },
  { label: 'Bias', pick: (s) => s.bias_mw, format: formatSignedMW },
  { label: 'Safety margin (P90)', pick: (s) => s.safety_margin_mw, format: formatMW },
  { label: 'Worst 10% too low (P10)', pick: (s) => s.p10_mw, format: formatSignedMW },
]

/** Experimental backtest: official forecast vs the same forecast corrected for its recent bias. */
export function BiasCorrectionPanel({ gate, start, end }: Props) {
  const { data, isError, error } = useBiasCorrection(gate, start, end)
  if (isError) return <p className="text-red-600">{error.message}</p>
  if (!data) return <p className="text-slate-500">Loading…</p>
  if (!data.raw || !data.corrected) {
    return (
      <p className="text-sm text-slate-600">
        The correction needs {data.window_days} complete days of history, so it is available from{' '}
        {formatDate(data.first_available_date)}. Extend the period to include those days.
      </p>
    )
  }
  const { raw, corrected } = data
  const maeChange = corrected.mae_mw / raw.mae_mw - 1

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <table className="w-full text-right text-sm tabular-nums">
        <thead className="text-xs uppercase text-slate-500">
          <tr>
            <th className="pb-2 text-left" />
            <th className="pb-2">Official</th>
            <th className="pb-2 text-emerald-700">Corrected</th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map(({ label, pick, format }) => (
            <tr key={label} className="border-t border-slate-100">
              <td className="py-2 text-left">{label}</td>
              <td>{format(pick(raw))}</td>
              <td className="font-medium text-emerald-700">{format(pick(corrected))}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="space-y-2 text-sm text-slate-600">
        <p>
          <strong className={maeChange <= 0 ? 'text-emerald-700' : 'text-amber-700'}>
            {Math.round(Math.abs(maeChange) * 100)}% {maeChange <= 0 ? 'smaller' : 'larger'} typical miss
          </strong>{' '}over{' '}
          {data.days} delivery days (from {formatDate(data.first_available_date)}).
        </p>
        <p>
          How it works: subtract the forecast's average error over the {data.window_days} complete days before
          the bid (D-{data.window_days + 1} to D-2). Only data known when bids were due is used.
        </p>
        <p className="text-slate-500">
          Caveats: a small sample from one month, so promising rather than proven. The corrected forecast is
          sometimes too low (see P10), which would mean over-buying.
        </p>
      </div>
    </div>
  )
}
