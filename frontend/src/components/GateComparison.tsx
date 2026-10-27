import { useAccuracy } from '../api/client'
import type { GatePreset } from '../api/types'
import { formatMW, formatSignedMW, shortTime } from '../format'

interface Props {
  presets: GatePreset[]
  start: string
  end: string
}

/** Accuracy of the forecast available at each auction's gate closure, side by side. */
export function GateComparison({ presets, start, end }: Props) {
  return (
    <table className="w-full text-right text-sm tabular-nums">
      <thead className="text-xs uppercase text-slate-500">
        <tr>
          <th className="pb-2 text-left">Auction (gate)</th><th className="pb-2">MAE</th><th className="pb-2">Bias</th>
        </tr>
      </thead>
      <tbody>
        {presets.map((preset) => <GateRow key={preset.label} preset={preset} start={start} end={end} />)}
      </tbody>
    </table>
  )
}

// One component per row so each row can call its own query hook.
function GateRow({ preset, start, end }: { preset: GatePreset; start: string; end: string }) {
  const gate = shortTime(preset.time)
  const { data } = useAccuracy({ mode: 'decision', gate, start, end })
  return (
    <tr className="border-t border-slate-100">
      <td className="py-2 text-left font-medium">{preset.label} ({gate})</td>
      <td>{data ? formatMW(data.summary.mae_mw) : '…'}</td>
      <td>{data ? formatSignedMW(data.summary.bias_mw) : '…'}</td>
    </tr>
  )
}
