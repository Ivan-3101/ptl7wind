import {
  CartesianGrid, Legend, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { HorizonPoint } from '../api/types'
import { formatAxisGW, formatSignedMW } from '../format'

interface Props {
  data: HorizonPoint[]
  bidWindow: [number, number] // lead times at which day-ahead bids are placed
  selectedHorizon?: number    // highlighted when scoring at a fixed lead time
}

export function HorizonChart({ data, bidWindow, selectedHorizon }: Props) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 16, right: 16, bottom: 16, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="horizon_h" type="number" domain={[0, 48]} ticks={[0, 6, 12, 18, 24, 30, 36, 42, 48]}
          label={{ value: 'Lead time (hours ahead)', position: 'insideBottom', offset: -10 }}
        />
        <YAxis tickFormatter={formatAxisGW} width={64} />
        <Tooltip
          labelFormatter={(h) => `${h}h ahead`}
          formatter={(v, name) => [formatSignedMW(Number(v)), name]}
        />
        <Legend verticalAlign="top" />
        <ReferenceArea
          x1={bidWindow[0]} x2={bidWindow[1]} fill="#0ea5e9" fillOpacity={0.08}
          label={{ value: 'Your day-ahead bids', position: 'insideTop', fill: '#0369a1', fontSize: 12 }}
        />
        {selectedHorizon !== undefined && <ReferenceLine x={selectedHorizon} stroke="#0369a1" strokeDasharray="4 4" />}
        <Line dataKey="mae_mw" name="Mean absolute error" stroke="#0f172a" strokeWidth={2} dot={false} />
        <Line dataKey="bias_mw" name="Bias (forecast − actual)" stroke="#d97706" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}
