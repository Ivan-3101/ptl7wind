import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { HourOfDay } from '../api/types'
import { formatAxisGW, formatSignedMW } from '../format'

const pad = (h: number) => String(h).padStart(2, '0')
const hourLabel = (h: number) => `${pad(h)}:00`

export function HourOfDayChart({ data }: { data: HourOfDay[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
        <XAxis dataKey="hour" tickFormatter={pad} interval={2} />
        <YAxis tickFormatter={formatAxisGW} width={64} />
        <Tooltip labelFormatter={(h) => hourLabel(Number(h))} formatter={(v, name) => [formatSignedMW(Number(v)), name]} />
        <Legend verticalAlign="top" />
        <Bar dataKey="bias_mw" name="Bias" fill="#f59e0b" isAnimationActive={false} />
        <Line dataKey="mae_mw" name="Mean absolute error" stroke="#0f172a" strokeWidth={2} dot={false} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
