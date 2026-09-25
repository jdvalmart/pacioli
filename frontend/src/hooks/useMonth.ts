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

const now = new Date()
const STORAGE_KEY = 'pacioli-month'

function isValid(m: unknown): m is Month {
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
    return isValid(parsed) ? parsed : null
  } catch {
    return null
  }
}

function parseMonth(params: URLSearchParams): Month {
  const month = Number(params.get('month'))
  const year = Number(params.get('year'))
  if (isValid({ month, year })) return { month, year }
  return readSavedMonth() ?? { month: now.getMonth() + 1, year: now.getFullYear() }
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
    (delta: number) => {
      const date = new Date(month.year, month.month - 1 + delta, 1)
      setMonth({ month: date.getMonth() + 1, year: date.getFullYear() })
    },
    [month, setMonth],
  )

  return { month, setMonth, shiftMonth }
}

const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
]

export function monthLabel(m: Month): string {
  return `${MONTH_NAMES[m.month - 1]} ${m.year}`
}
