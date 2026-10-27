import { useState } from 'react'
import { useMeta } from './api/client'
import { GateSelector } from './components/GateSelector'
import { shortTime } from './format'
import { AccuracyView } from './views/AccuracyView'
import { DayAheadView } from './views/DayAheadView'

type Tab = 'day-ahead' | 'accuracy'

const TABS: { id: Tab; label: string }[] = [
  { id: 'day-ahead', label: 'Day-ahead view' },
  { id: 'accuracy', label: 'Forecast accuracy' },
]

export default function App() {
  const meta = useMeta()
  const [tab, setTab] = useState<Tab>('day-ahead')
  const [gate, setGate] = useState<string | null>(null) // null until the user picks one

  if (meta.isPending) return <p className="p-8 text-slate-500">Loading…</p>
  if (meta.isError) return <p className="p-8 text-red-600">Could not reach the API: {meta.error.message}</p>

  const activeGate = gate ?? shortTime(meta.data.default_gate)

  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Wind<span className="text-sky-600">Sight</span>
          </h1>
          <p className="text-sm text-slate-500">GB wind forecast monitor for day-ahead purchasing</p>
        </div>
        <GateSelector presets={meta.data.gate_presets} value={activeGate} onChange={setGate} />
      </header>

      <nav className="mt-4 flex gap-1">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
              tab === id ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-200'
            }`}
          >
            {label}
          </button>
        ))}
      </nav>

      <main className="mt-6">
        {tab === 'day-ahead' ? (
          <DayAheadView meta={meta.data} gate={activeGate} />
        ) : (
          <AccuracyView meta={meta.data} gate={activeGate} />
        )}
      </main>
    </div>
  )
}
