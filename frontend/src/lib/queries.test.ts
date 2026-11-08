import { describe, expect, it } from 'vitest'

import { STALE_AFTER, queryKeys } from '@/lib/queries'

const resources = Object.keys(queryKeys)

describe('queryKeys', () => {
  it('starts every key with its resource name (invalidation matches by prefix)', () => {
    const month = { month: 11, year: 2026 }
    expect(queryKeys.transactions(month)[0]).toBe('transactions')
    expect(queryKeys.categorySpending(month, 'expense')).toEqual([
      'categorySpending',
      [2026, 11],
      'expense',
    ])
    expect(queryKeys.creditCards()).toEqual(['creditCards', 'today'])
  })
})

describe('STALE_AFTER', () => {
  it('lets every cached resource be refreshed by some change', () => {
    const refreshable = new Set(Object.values(STALE_AFTER).flat())
    expect(resources.filter((r) => !refreshable.has(r as never))).toEqual([])
  })

  it('refreshes everything derived from movements after a movement', () => {
    expect(STALE_AFTER.movement).toEqual(
      expect.arrayContaining([
        'transactions',
        'accounts',
        'creditCards',
        'savings',
        'summary',
        'yearly',
        'categorySpending',
        'budgetVsActual',
      ]),
    )
  })

  it('treats card settings as affecting budgets (they move installments between months)', () => {
    expect(STALE_AFTER.card).toEqual(expect.arrayContaining(['budgetVsActual', 'categorySpending']))
  })

  it('refreshes movement lists after renaming a category', () => {
    expect(STALE_AFTER.category).toContain('transactions')
  })
})
