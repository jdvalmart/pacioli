import { describe, expect, it } from 'vitest'

import { currentMonth, isValidMonth, monthLabel, parseMonth, shiftMonthValue } from '@/hooks/useMonth'

describe('shiftMonthValue', () => {
  it.each([
    [{ month: 11, year: 2026 }, 1, { month: 12, year: 2026 }],
    [{ month: 12, year: 2026 }, 1, { month: 1, year: 2027 }],
    [{ month: 1, year: 2027 }, -1, { month: 12, year: 2026 }],
    [{ month: 3, year: 2026 }, -15, { month: 12, year: 2024 }],
    [{ month: 6, year: 2026 }, 0, { month: 6, year: 2026 }],
  ])('%o shifted by %i -> %o', (start, delta, expected) => {
    expect(shiftMonthValue(start, delta)).toEqual(expected)
  })
})

describe('currentMonth', () => {
  it('reads the date it is given (not a value frozen at load time)', () => {
    expect(currentMonth(new Date(2026, 10, 30, 23, 59))).toEqual({ month: 11, year: 2026 })
    expect(currentMonth(new Date(2026, 11, 1, 0, 0))).toEqual({ month: 12, year: 2026 })
  })
})

describe('parseMonth', () => {
  const saved = { month: 3, year: 2025 }

  it('prefers a valid month in the URL', () => {
    expect(parseMonth(new URLSearchParams('month=9&year=2026'), saved)).toEqual({
      month: 9,
      year: 2026,
    })
  })

  it('falls back to the saved month when the URL is invalid', () => {
    expect(parseMonth(new URLSearchParams('month=13&year=2026'), saved)).toEqual(saved)
    expect(parseMonth(new URLSearchParams(''), saved)).toEqual(saved)
  })

  it('falls back to the current month with nothing saved', () => {
    expect(parseMonth(new URLSearchParams(''), null)).toEqual(currentMonth())
  })
})

describe('isValidMonth', () => {
  it.each([
    [{ month: 1, year: 2000 }, true],
    [{ month: 12, year: 2100 }, true],
    [{ month: 0, year: 2026 }, false],
    [{ month: 5, year: 1999 }, false],
    [{ month: '5', year: 2026 }, false],
    [null, false],
  ])('%o -> %s', (value, expected) => {
    expect(isValidMonth(value)).toBe(expected)
  })
})

describe('monthLabel', () => {
  it('capitalizes the Spanish month name', () => {
    expect(monthLabel({ month: 11, year: 2026 })).toBe('Noviembre 2026')
  })
})
