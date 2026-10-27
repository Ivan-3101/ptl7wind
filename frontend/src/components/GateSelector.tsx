import type { GatePreset } from '../api/types'
import { shortTime } from '../format'

interface Props {
  presets: GatePreset[]
  value: string // "HH:MM"
  onChange: (gate: string) => void
}

/** Gate-closure time on D-1: preset buttons for the two GB auctions, or any custom time. */
export function GateSelector({ presets, value, onChange }: Props) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-slate-500">Bids due D-1 at</span>
      {presets.map((preset) => {
        const time = shortTime(preset.time)
        const active = time === value
        return (
          <button
            key={preset.label}
            onClick={() => onChange(time)}
            className={`rounded-md border px-2.5 py-1 font-medium transition ${
              active
                ? 'border-sky-600 bg-sky-600 text-white'
                : 'border-slate-300 bg-white text-slate-700 hover:border-sky-400'
            }`}
          >
            {preset.label} {time}
          </button>
        )
      })}
      <input
        type="time"
        value={value}
        onChange={(e) => e.target.value && onChange(e.target.value)}
        className="rounded-md border border-slate-300 bg-white px-2 py-1"
        aria-label="Custom gate closure time"
      />
    </div>
  )
}
