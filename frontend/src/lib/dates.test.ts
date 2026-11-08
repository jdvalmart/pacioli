import { describe, expect, it } from 'vitest'

import { addDaysISO, defaultMovementDate, toISODate, todayISO } from '@/lib/dates'

describe('toISODate / todayISO', () => {
  it('uses the local calendar day, not UTC (evening in Colombia is still today)', () => {
    const evening = new Date(2026, 10, 8, 21, 30) // Nov 8, 21:30 local
    expect(toISODate(evening)).toBe('2026-11-08')
    expect(todayISO(evening)).toBe('2026-11-08')
  })

  it('pads month and day', () => {
    expect(toISODate(new Date(2027, 0, 5))).toBe('2027-01-05')
  })
})

describe('addDaysISO', () => {
  it.each([
    ['2026-11-10', 1, '2026-11-11'],
    ['2026-11-30', 1, '2026-12-01'],
    ['2026-12-31', 1, '2027-01-01'],
    ['2028-02-28', 1, '2028-02-29'], // leap year
    ['2026-03-01', -1, '2026-02-28'],
  ])('%s + %i -> %s', (iso, days, expected) => {
    expect(addDaysISO(iso, days)).toBe(expected)
  })
})

describe('defaultMovementDate', () => {
  const now = new Date(2026, 10, 8, 20, 0) // Nov 8 2026, 20:00 local

  it('proposes today in the current month', () => {
    expect(defaultMovementDate({ month: 11, year: 2026 }, now)).toBe('2026-11-08')
  })

  it('proposes the 15th when browsing another month', () => {
    expect(defaultMovementDate({ month: 9, year: 2026 }, now)).toBe('2026-09-15')
    expect(defaultMovementDate({ month: 11, year: 2025 }, now)).toBe('2025-11-15')
  })
})
