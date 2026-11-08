/**
 * Budget figures shared by the Budgets page and the dashboard, so both
 * always show the same numbers.
 *
 * - Spending: every real expense of the month, budgeted or not. Savings are
 *   NOT spending; the savings category (role "savings") is a goal.
 * - Available: total budget minus all spending.
 * - Assigned: sum of category budgets, savings goal included (it is part of
 *   how the month's money is planned); unassigned = total − assigned.
 */
import type { BudgetPlan, BudgetVsActual } from '@/lib/types'

export interface CategoryBudget {
  row: BudgetVsActual
  budget: number
  spent: number
  percent: number
  over: boolean
}

export interface SavingsGoal {
  goal: number
  saved: number
  /** Progress towards the goal; above 100 means the goal was beaten. */
  percent: number
}

export interface BudgetTotals {
  total: number
  totalSource: BudgetPlan['source']
  assigned: number
  unassigned: number
  spent: number
  spentWithoutBudget: number
  available: number
  /** Expense categories with a budget, largest budget first. */
  categories: CategoryBudget[]
  savings: SavingsGoal | null
}

export function budgetTotals(
  rows: BudgetVsActual[],
  plan: BudgetPlan | undefined,
  monthIncome: number,
): BudgetTotals {
  const savingsRow = rows.find((row) => row.role === 'savings')
  const expenseRows = rows.filter((row) => row.role !== 'savings')

  // Without any plan ever saved nor income history, fall back to this month's income.
  const total = plan?.total != null ? Number(plan.total) : monthIncome
  const totalSource = plan?.total != null ? (plan.source ?? 'saved') : 'none'

  const categories = expenseRows
    .filter((row) => Number(row.budget) > 0)
    .map((row) => {
      const budget = Number(row.budget)
      const spent = Number(row.actual)
      const percent = (spent / budget) * 100
      return { row, budget, spent, percent, over: percent > 100 }
    })
    .sort((a, b) => b.budget - a.budget || b.spent - a.spent)

  const spent = expenseRows.reduce((sum, row) => sum + Number(row.actual), 0)
  const spentWithoutBudget = expenseRows
    .filter((row) => Number(row.budget) <= 0)
    .reduce((sum, row) => sum + Number(row.actual), 0)

  const savingsGoal = savingsRow ? Number(savingsRow.budget) : 0
  const saved = savingsRow ? Number(savingsRow.actual) : 0
  const savings =
    savingsGoal > 0 || saved !== 0
      ? { goal: savingsGoal, saved, percent: savingsGoal > 0 ? (saved / savingsGoal) * 100 : 0 }
      : null

  const assigned = categories.reduce((sum, c) => sum + c.budget, 0) + savingsGoal
  return {
    total,
    totalSource,
    assigned,
    unassigned: total - assigned,
    spent,
    spentWithoutBudget,
    available: total - spent,
    categories,
    savings,
  }
}

/** One line explaining where the month's total budget comes from. */
export function totalSourceLabel(source: BudgetTotals['totalSource']): string {
  switch (source) {
    case 'saved':
      return 'Definido para este mes'
    case 'inherited':
      return 'Heredado del último mes definido'
    case 'income_average':
      return 'Promedio de tus ingresos recientes'
    default:
      return 'Igual a tus ingresos del mes'
  }
}
