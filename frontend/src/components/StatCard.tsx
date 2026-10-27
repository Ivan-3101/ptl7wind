interface Props {
  label: string
  value: string
  hint?: string
  tone?: 'default' | 'warn'
}

export function StatCard({ label, value, hint, tone = 'default' }: Props) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${tone === 'warn' ? 'text-amber-600' : 'text-slate-900'}`}>
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  )
}
