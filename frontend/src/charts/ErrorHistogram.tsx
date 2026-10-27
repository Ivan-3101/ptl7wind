import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { HistogramBin } from '../api/types'
import { formatAxisGW, formatGW } from '../format'

interface Props {
  bins: HistogramBin[]
  p10: number
  p90: number
  binMw?: number // must match the backend's bin width
}

export function ErrorHistogram({ bins, p10, p90, binMw = 500 }: Props) {
  // Percentile lines are drawn on the bar (bin) that contains them.
  const binOf = (mw: number) => Math.floor(mw / binMw) * binMw

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={bins} margin={{ top: 24, right: 16, bottom: 16, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
        <XAxis
          dataKey="bin_start_mw" tickFormatter={formatAxisGW}
          label={{ value: 'Error (forecast − actual)', position: 'insideBottom', offset: -10 }}
        />
        <YAxis width={40} allowDecimals={false} />
        <Tooltip
          labelFormatter={(b) => `${formatGW(Number(b))} to ${formatGW(Number(b) + binMw)}`}
          formatter={(v) => [`${v} hours`, 'Count']}
        />
        <Bar dataKey="count" isAnimationActive={false}>
          {bins.map((b) => (
            <Cell key={b.bin_start_mw} fill={b.bin_start_mw >= 0 ? '#f59e0b' : '#0ea5e9'} />
          ))}
        </Bar>
        <ReferenceLine
          x={binOf(p10)} stroke="#334155" strokeDasharray="4 4"
          label={{ value: `P10 ${formatGW(p10)}`, position: 'top', fontSize: 12 }}
        />
        <ReferenceLine
          x={binOf(p90)} stroke="#334155" strokeDasharray="4 4"
          label={{ value: `P90 ${formatGW(p90)}`, position: 'top', fontSize: 12 }}
        />
      </BarChart>
    </ResponsiveContainer>
  )
}
