// Display formatting. All times are shown in UK local time (equal to UTC in January).

const UK = 'Europe/London'

const dateTime = new Intl.DateTimeFormat('en-GB', {
  weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: UK,
})
const longDate = new Intl.DateTimeFormat('en-GB', {
  weekday: 'short', day: 'numeric', month: 'short', year: 'numeric', timeZone: UK,
})
const hourMinute = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: UK })

export const formatDateTime = (iso: string) => dateTime.format(new Date(iso))
export const formatHour = (iso: string | number) => hourMinute.format(new Date(iso))
/** "2026-01-10" -> "Sat 10 Jan 2026" */
export const formatDate = (day: string) => longDate.format(new Date(`${day}T12:00:00Z`))

export const formatMW = (mw: number) => `${Math.round(mw).toLocaleString('en-GB')} MW`
export const formatSignedMW = (mw: number) => `${mw > 0 ? '+' : ''}${formatMW(mw)}`
export const formatGW = (mw: number) => `${(mw / 1000).toFixed(1)} GW`
/** Compact chart-axis label: 20000 -> "20 GW", 2400 -> "2.4 GW". */
export const formatAxisGW = (mw: number) => `${Number((mw / 1000).toFixed(1))} GW`
export const formatPercent = (fraction: number) => `${(fraction * 100).toFixed(1)}%`

/** "2026-01-10", 1 -> "2026-01-11" */
export function addDays(day: string, days: number): string {
  const date = new Date(`${day}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

/** "09:20:00" -> "09:20" */
export const shortTime = (time: string) => time.slice(0, 5)
