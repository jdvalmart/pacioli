/**
 * Typed API client for the Pacioli backend.
 *
 * The Vite dev server proxies /api/* to http://localhost:8000.
 */

import type { components } from '@/lib/api-schema'
import type {
  Account,
  Budget,
  BudgetPlan,
  BudgetVsActual,
  Category,
  CategorySpending,
  CreditCard,
  MonthlySummary,
  SavingsItem,
  Subcategory,
  Transaction,
  TransactionInput,
} from '@/lib/types'

type In = components['schemas']
type Created = In['CreatedOut']
type Message = In['MessageOut']

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      // Non-JSON error body; keep the status text
    }
    throw new Error(detail)
  }
  return (await response.json()) as T
}

function query(month: number, year: number): string {
  return `?month=${month}&year=${year}`
}

export const api = {
  // Categories
  listCategories: (type?: string) =>
    request<Category[]>(`/categories${type ? `?type=${type}` : ''}`),
  createCategory: (payload: In['CategoryIn']) =>
    request<Created>('/categories', { method: 'POST', body: JSON.stringify(payload) }),
  updateCategory: (id: number, payload: In['CategoryUpdate']) =>
    request<Message>(`/categories/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  deleteCategory: (id: number) =>
    request<Message>(`/categories/${id}`, { method: 'DELETE' }),

  // Subcategories
  listSubcategories: (categoryId: number) =>
    request<Subcategory[]>(`/categories/${categoryId}/subcategories`),
  createSubcategory: (categoryId: number, payload: In['SubcategoryIn']) =>
    request<Created>(`/categories/${categoryId}/subcategories`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  deleteSubcategory: (id: number) =>
    request<Message>(`/categories/subcategories/${id}`, { method: 'DELETE' }),

  // Transactions
  listTransactions: (month: number, year: number) =>
    request<Transaction[]>(`/transactions${query(month, year)}`),
  createTransaction: (payload: TransactionInput) =>
    request<Created>('/transactions', { method: 'POST', body: JSON.stringify(payload) }),
  updateTransaction: (id: number, payload: TransactionInput) =>
    request<Message>(`/transactions/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  deleteTransaction: (id: number) =>
    request<Message>(`/transactions/${id}`, { method: 'DELETE' }),
  materializeRecurring: (month: number, year: number) =>
    request<In['MaterializeResult']>(`/transactions/materialize${query(month, year)}`, {
      method: 'POST',
    }),

  // Budgets
  listBudgets: (month: number, year: number) =>
    request<Budget[]>(`/budgets${query(month, year)}`),
  upsertBudget: (payload: In['BudgetIn']) =>
    request<Message>('/budgets', { method: 'PUT', body: JSON.stringify(payload) }),
  replaceBudgets: (payload: In['BudgetBulkIn']) =>
    request<Message>('/budgets/bulk', { method: 'PUT', body: JSON.stringify(payload) }),
  deleteBudget: (categoryId: number, month: number, year: number) =>
    request<Message>(
      `/budgets?category_id=${categoryId}&month=${month}&year=${year}`,
      { method: 'DELETE' },
    ),
  getBudgetPlan: (month: number, year: number) =>
    request<BudgetPlan>(`/budgets/plan${query(month, year)}`),
  setBudgetPlan: (payload: In['BudgetPlanIn']) =>
    request<Message>('/budgets/plan', {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  // Accounts
  listAccounts: () => request<Account[]>('/accounts'),
  createAccount: (payload: In['AccountIn']) =>
    request<Created>('/accounts', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateAccount: (id: number, payload: In['AccountUpdate']) =>
    request<Message>(`/accounts/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  deleteAccount: (id: number) =>
    request<Message>(`/accounts/${id}`, { method: 'DELETE' }),

  // Credit cards
  listCreditCards: (month?: number, year?: number) =>
    request<CreditCard[]>(
      month != null && year != null ? `/credit-cards?month=${month}&year=${year}` : '/credit-cards',
    ),
  createCreditCard: (payload: In['CreditCardIn']) => request<Created>('/credit-cards', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  updateCreditCard: (id: number, payload: In['CreditCardIn']) =>
    request<Message>(`/credit-cards/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  deleteCreditCard: (id: number) =>
    request<Message>(`/credit-cards/${id}`, { method: 'DELETE' }),

  // Savings
  listSavings: () => request<SavingsItem[]>('/savings'),
  createSavings: (payload: In['SavingsIn']) => request<Created>('/savings', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  updateSavings: (id: number, payload: In['SavingsUpdate']) =>
    request<Message>(`/savings/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  deleteSavings: (id: number) =>
    request<Message>(`/savings/${id}`, { method: 'DELETE' }),

  // Reports
  summary: (month: number, year: number) =>
    request<MonthlySummary>(`/reports/summary${query(month, year)}`),
  yearlySummaries: (year: number) => request<MonthlySummary[]>(`/reports/monthly?year=${year}`),
  categorySpending: (month: number, year: number, type: string = 'expense') =>
    request<CategorySpending[]>(`/reports/category-spending${query(month, year)}&type=${type}`),
  budgetVsActual: (month: number, year: number) =>
    request<BudgetVsActual[]>(`/reports/budget-vs-actual${query(month, year)}`),
  exportCsvUrl: (month: number, year: number) => `${BASE}/reports/export${query(month, year)}`,

}
