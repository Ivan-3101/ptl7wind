import { keepPreviousData, useQuery } from '@tanstack/react-query'
import type { Accuracy, BiasCorrection, DayAhead, HorizonPoint, Meta } from './types'

type Params = Record<string, string | number | undefined>

async function get<T>(path: string, params: Params = {}): Promise<T> {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) query.set(key, String(value))
  }
  const response = await fetch(`/api/${path}?${query}`)
  if (!response.ok) {
    // Our own errors have a string "detail"; FastAPI's validation errors have a list.
    const body = await response.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : `Request failed (${response.status})`
    throw new Error(detail)
  }
  return response.json()
}

export const useMeta = () =>
  useQuery({ queryKey: ['meta'], queryFn: () => get<Meta>('meta') })

// keepPreviousData: while the next day/gate loads, keep showing the current chart instead of a spinner.
export const useDayAhead = (date: string, gate: string) =>
  useQuery({
    queryKey: ['day-ahead', date, gate],
    queryFn: () => get<DayAhead>('day-ahead', { date, gate }),
    placeholderData: keepPreviousData,
  })

export interface AccuracyParams {
  mode: 'decision' | 'horizon'
  gate?: string
  horizon?: number
  start: string
  end: string
}

export const useAccuracy = (params: AccuracyParams) =>
  useQuery({
    queryKey: ['accuracy', params],
    queryFn: () => get<Accuracy>('accuracy', { ...params }),
    placeholderData: keepPreviousData,
  })

export const useBiasCorrection = (gate: string, start?: string, end?: string) =>
  useQuery({
    queryKey: ['bias-correction', gate, start, end],
    queryFn: () => get<BiasCorrection>('accuracy/bias-correction', { gate, start, end }),
    placeholderData: keepPreviousData,
  })

export const useHorizonCurve = (start: string, end: string) =>
  useQuery({
    queryKey: ['by-horizon', start, end],
    queryFn: () => get<HorizonPoint[]>('accuracy/by-horizon', { start, end }),
    placeholderData: keepPreviousData,
  })
