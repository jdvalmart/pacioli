import { describe, expect, it } from 'vitest'

import { budgetTotals } from '@/lib/budget'
import type { BudgetVsActual } from '@/lib/types'

const row = (
  name: string,
  budget: string,
  actual: string,
  role: 'savings' | null = null,
): BudgetVsActual => ({
  category_id: name.length,
  name,
  color: '#888',
  icon: '•',
  budget,
  actual,
  reserved: '0.00',
  remaining: String(Number(budget) - Number(actual)),
  percent: Number(budget) > 0 ? (Number(actual) / Number(budget)) * 100 : 0,
  role,
})

// The demo month: savings beat the goal by far, spending is within budget.
const ROWS = [
  row('Vivienda', '2600000', '2200000'),
  row('Alimentación', '1200000', '420000'),
  row('Compras', '0', '708000'), // spent without a budget
  row('Ahorro', '1000000', '5900000', 'savings'),
]

describe('budgetTotals', () => {
  const totals = budgetTotals(ROWS, { month: 11, year: 2026, total: '9000000', source: 'saved' }, 9_000_000)

  it('never counts savings as spending', () => {
    expect(totals.spent).toBe(2_200_000 + 420_000 + 708_000)
    expect(totals.categories.map((c) => c.row.name)).toEqual(['Vivienda', 'Alimentación'])
  })

  it('available is the total minus every expense, budgeted or not', () => {
    expect(totals.spentWithoutBudget).toBe(708_000)
    expect(totals.available).toBe(9_000_000 - 3_328_000)
  })

  it('treats savings as a goal that can be beaten', () => {
    expect(totals.savings).toEqual({ goal: 1_000_000, saved: 5_900_000, percent: 590 })
  })

  it('assigns the savings goal as part of the plan', () => {
    expect(totals.assigned).toBe(2_600_000 + 1_200_000 + 1_000_000)
    expect(totals.unassigned).toBe(9_000_000 - 4_800_000)
  })

  it('falls back to the month income when there is no plan at all', () => {
    const none = budgetTotals(ROWS, { month: 11, year: 2026, total: null, source: 'none' }, 7_500_000)
    expect(none.totalSource).toBe('none')
    expect(none.total).toBe(7_500_000)
  })

  it('has no savings goal when there is neither a goal nor savings', () => {
    expect(budgetTotals([row('Vivienda', '100', '50')], undefined, 0).savings).toBeNull()
  })
})
