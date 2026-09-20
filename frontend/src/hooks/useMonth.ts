/**
 * Hook that reads and updates the selected month from the URL.
 * The month lives in the query string (?month=9&year=2026) so the
 * selection survives reloads and can be shared as a link.
 */

import { useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'

export interface Month {
  month: number
  year: number
}

const now = new Date()

function parseMonth(params: URLSearchParams): Month {
  const month = Number(params.get('month'))
  const year = Number(params.get('year'))
  const validMonth = month >= 1 && month <= 12 ? month : now.getMonth() + 1
  const validYear = year >= 2000 && year <= 2100 ? year : now.getFullYear()
  return { month: validMonth, year: validYear }
}

export function useMonth(): {
  month: Month
  setMonth: (m: Month) => void
  shiftMonth: (delta: number) => void
} {
  const [searchParams, setSearchParams] = useSearchParams()
  const month = parseMonth(searchParams)

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
  'Enero',
  'Febrero',
  'Marzo',
  'Abril',
  'Mayo',
  'Junio',
  'Julio',
  'Agosto',
  'Septiembre',
  'Octubre',
  'Noviembre',
  'Diciembre',
]

export function monthLabel(m: Month): string {
  return `${MONTH_NAMES[m.month - 1]} ${m.year}`
}
