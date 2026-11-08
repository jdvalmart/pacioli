/**
 * Server state: query keys, one hook per resource and cache invalidation.
 *
 * Components never write query keys or call invalidateQueries themselves.
 * They read through the hooks below and, after a write, call
 * `useInvalidate()(change)` with WHAT changed; the dependency map decides
 * which cached views are stale. Adding a new view means adding it to the
 * map once, instead of hunting down every mutation that might affect it.
 */
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'

import type { Month } from '@/hooks/useMonth'
import { api } from '@/lib/api'
import type { CategoryType } from '@/lib/types'

// ── Keys ───────────────────────────────────────────────────────
// Each key starts with its resource name; invalidating ['budgets'] marks
// every month of budgets stale.

const m = (month: Month) => [month.year, month.month] as const

export const queryKeys = {
  accounts: () => ['accounts'] as const,
  categories: () => ['categories'] as const,
  subcategories: (categoryId: number) => ['subcategories', categoryId] as const,
  savings: () => ['savings'] as const,
  /** Without a month the card is computed as of today. */
  creditCards: (month?: Month) => ['creditCards', month ? m(month) : 'today'] as const,
  transactions: (month: Month) => ['transactions', m(month)] as const,
  summary: (month: Month) => ['summary', m(month)] as const,
  yearly: (year: number) => ['yearly', year] as const,
  categorySpending: (month: Month, type: CategoryType) =>
    ['categorySpending', m(month), type] as const,
  budgets: (month: Month) => ['budgets', m(month)] as const,
  budgetPlan: (month: Month) => ['budgetPlan', m(month)] as const,
  budgetVsActual: (month: Month) => ['budgetVsActual', m(month)] as const,
}

type Resource = keyof typeof queryKeys

// ── What changed → which views are stale ──────────────────────

/** Views derived from movements: lists, balances, cards, savings and reports. */
const MOVEMENT_VIEWS: Resource[] = [
  'transactions',
  'accounts',
  'creditCards',
  'savings',
  'summary',
  'yearly',
  'categorySpending',
  'budgetVsActual',
]

export const STALE_AFTER = {
  /** A transaction was created, edited or deleted (incl. card payments and savings moves). */
  movement: MOVEMENT_VIEWS,
  /** Opening balances and names show in balances, lists and the accumulated summary. */
  account: ['accounts', 'transactions', 'summary', 'yearly'],
  /** Cutoff/payment days decide in which month each installment counts. */
  card: ['creditCards', ...MOVEMENT_VIEWS],
  /** Creating a pocket may move money (initial deposit) and reserve budget. */
  savings: MOVEMENT_VIEWS,
  /** Names, colors and icons appear everywhere; deleting one changes budgets. */
  category: ['categories', 'subcategories', 'budgets', ...MOVEMENT_VIEWS],
  subcategory: ['subcategories', 'transactions'],
  budget: ['budgets', 'budgetPlan', 'budgetVsActual'],
} satisfies Record<string, Resource[]>

export type Change = keyof typeof STALE_AFTER

/** Returns `invalidate(change)`: marks every view that depends on `change` stale. */
export function useInvalidate(): (change: Change) => Promise<void> {
  const client = useQueryClient()
  return useCallback(
    async (change: Change) => {
      const roots = [...new Set(STALE_AFTER[change])]
      await Promise.all(roots.map((root) => client.invalidateQueries({ queryKey: [root] })))
    },
    [client],
  )
}

// ── Hooks ──────────────────────────────────────────────────────

export const useAccounts = () =>
  useQuery({ queryKey: queryKeys.accounts(), queryFn: api.listAccounts })

export const useCategories = () =>
  useQuery({ queryKey: queryKeys.categories(), queryFn: () => api.listCategories() })

export const useSubcategories = (categoryId: number | null) =>
  useQuery({
    queryKey: queryKeys.subcategories(categoryId ?? 0),
    queryFn: () => api.listSubcategories(categoryId ?? 0),
    enabled: categoryId != null,
  })

export const useSavings = () =>
  useQuery({ queryKey: queryKeys.savings(), queryFn: api.listSavings })

export const useCreditCards = (month?: Month) =>
  useQuery({
    queryKey: queryKeys.creditCards(month),
    queryFn: () => (month ? api.listCreditCards(month.month, month.year) : api.listCreditCards()),
  })

export const useTransactions = (month: Month) =>
  useQuery({
    queryKey: queryKeys.transactions(month),
    queryFn: () => api.listTransactions(month.month, month.year),
  })

export const useSummary = (month: Month, options: { enabled?: boolean } = {}) =>
  useQuery({
    queryKey: queryKeys.summary(month),
    queryFn: () => api.summary(month.month, month.year),
    ...options,
  })

export const useYearlySummaries = (year: number) =>
  useQuery({ queryKey: queryKeys.yearly(year), queryFn: () => api.yearlySummaries(year) })

export const useCategorySpending = (month: Month, type: CategoryType = 'expense') =>
  useQuery({
    queryKey: queryKeys.categorySpending(month, type),
    queryFn: () => api.categorySpending(month.month, month.year, type),
  })

export const useBudgets = (month: Month, options: { enabled?: boolean } = {}) =>
  useQuery({
    queryKey: queryKeys.budgets(month),
    queryFn: () => api.listBudgets(month.month, month.year),
    ...options,
  })

export const useBudgetPlan = (month: Month, options: { enabled?: boolean } = {}) =>
  useQuery({
    queryKey: queryKeys.budgetPlan(month),
    queryFn: () => api.getBudgetPlan(month.month, month.year),
    ...options,
  })

export const useBudgetVsActual = (month: Month) =>
  useQuery({
    queryKey: queryKeys.budgetVsActual(month),
    queryFn: () => api.budgetVsActual(month.month, month.year),
  })
