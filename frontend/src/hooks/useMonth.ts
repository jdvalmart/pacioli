/**
 * Hook that reads and updates the selected month from the URL.
 * The month lives in the query string (?month=9&year=2026) so the
 * selection survives reloads and can be shared as a link. It is also
 * mirrored in localStorage so it survives navigation between pages,
 * which drops the query string.
 */

import { useCallback, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'

export interface Month {
  month: number
  year: number
}

const STORAGE_KEY = 'pacioli-month'

/** The current month. Read on every call: the app stays open across months. */
export function currentMonth(today: Date = new Date()): Month {
  return { month: today.getMonth() + 1, year: today.getFullYear() }
}

/** Move a month by ``delta`` months, rolling over years. */
export function shiftMonthValue(m: Month, delta: number): Month {
  const index = m.year * 12 + (m.month - 1) + delta
  return { month: (((index % 12) + 12) % 12) + 1, year: Math.floor(index / 12) }
}

export function isValidMonth(m: unknown): m is Month {
  if (typeof m !== 'object' || m === null) return false
  const { month, year } = m as Partial<Month>
  return (
    typeof month === 'number' &&
    month >= 1 &&
    month <= 12 &&
    typeof year === 'number' &&
    year >= 2000 &&
    year <= 2100
  )
}

function readSavedMonth(): Month | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return isValidMonth(parsed) ? parsed : null
  } catch {
    return null
  }
}

/** Month from the URL, else the last one used, else the current month. */
export function parseMonth(params: URLSearchParams, saved: Month | null = readSavedMonth()): Month {
  const month = Number(params.get('month'))
  const year = Number(params.get('year'))
  if (isValidMonth({ month, year })) return { month, year }
  return saved ?? currentMonth()
}

export function useMonth(): {
  month: Month
  setMonth: (m: Month) => void
  shiftMonth: (delta: number) => void
} {
  const [searchParams, setSearchParams] = useSearchParams()
  const month = parseMonth(searchParams)
  const { month: monthNumber, year } = month

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ month: monthNumber, year }))
    } catch {
      // ignore storage errors
    }
  }, [monthNumber, year])

  const setMonth = useCallback(
    (m: Month) => {
      setSearchParams({ month: String(m.month), year: String(m.year) })
    },
    [setSearchParams],
  )

  const shiftMonth = useCallback(
    (delta: number) => setMonth(shiftMonthValue(month, delta)),
    [month, setMonth],
  )

  return { month, setMonth, shiftMonth }
}

const MONTH_NAMES = [
  'enero',
  'febrero',
  'marzo',
  'abril',
  'mayo',
  'junio',
  'julio',
  'agosto',
  'septiembre',
  'octubre',
  'noviembre',
  'diciembre',
]

export function monthLabel(m: Month): string {
  const name = MONTH_NAMES[m.month - 1]
  const label = name.charAt(0).toUpperCase() + name.slice(1)
  return `${label} ${m.year}`
}
