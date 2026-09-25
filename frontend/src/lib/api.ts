/**
 * Typed API client for the Pacioli backend.
 *
 * The Vite dev server proxies /api/* to http://localhost:8000.
 */

import type {
  AIConfig,
  Account,
  AccountType,
  Budget,
  BudgetPlan,
  BudgetVsActual,
  Category,
  CategorySpending,
  ChatMessage,
  ChatReply,
  ConnectionTest,
  CreditCard,
  MonthlySummary,
  SavingsItem,
  SavingsKind,
  Subcategory,
  Transaction,
  TransactionInput,
} from '@/lib/types'

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
  createCategory: (payload: { name: string; type: string; color: string; icon: string }) =>
    request<{ id: number }>('/categories', { method: 'POST', body: JSON.stringify(payload) }),
  updateCategory: (id: number, payload: { name: string; color: string; icon: string }) =>
    request<{ message: string }>(`/categories/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  deleteCategory: (id: number) =>
    request<{ message: string }>(`/categories/${id}`, { method: 'DELETE' }),

  // Subcategories
  listSubcategories: (categoryId: number) =>
    request<Subcategory[]>(`/categories/${categoryId}/subcategories`),
  createSubcategory: (categoryId: number, payload: { name: string; icon: string }) =>
    request<{ id: number }>(`/categories/${categoryId}/subcategories`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  deleteSubcategory: (id: number) =>
    request<{ message: string }>(`/categories/subcategories/${id}`, { method: 'DELETE' }),

  // Transactions
  listTransactions: (month: number, year: number) =>
    request<Transaction[]>(`/transactions${query(month, year)}`),
  createTransaction: (payload: TransactionInput) =>
    request<{ id: number }>('/transactions', { method: 'POST', body: JSON.stringify(payload) }),
  updateTransaction: (id: number, payload: TransactionInput) =>
    request<{ message: string }>(`/transactions/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  deleteTransaction: (id: number) =>
    request<{ message: string }>(`/transactions/${id}`, { method: 'DELETE' }),
  materializeRecurring: (month: number, year: number) =>
    request<{ created: number }>(`/transactions/materialize${query(month, year)}`, {
      method: 'POST',
    }),

  // Budgets
  listBudgets: (month: number, year: number) =>
    request<Budget[]>(`/budgets${query(month, year)}`),
  upsertBudget: (payload: { category_id: number; month: number; year: number; amount: string }) =>
    request<{ message: string }>('/budgets', { method: 'PUT', body: JSON.stringify(payload) }),
  replaceBudgets: (payload: {
    month: number
    year: number
    budgets: { category_id: number; amount: string }[]
  }) =>
    request<{ message: string }>('/budgets/bulk', { method: 'PUT', body: JSON.stringify(payload) }),
  deleteBudget: (categoryId: number, month: number, year: number) =>
    request<{ message: string }>(
      `/budgets?category_id=${categoryId}&month=${month}&year=${year}`,
      { method: 'DELETE' },
    ),
  getBudgetPlan: (month: number, year: number) =>
    request<BudgetPlan>(`/budgets/plan${query(month, year)}`),
  setBudgetPlan: (payload: { month: number; year: number; total: string }) =>
    request<{ message: string }>('/budgets/plan', {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  // Accounts
  listAccounts: () => request<Account[]>('/accounts'),
  createAccount: (payload: { name: string; type: AccountType; starting_amount: string }) =>
    request<{ id: number }>('/accounts', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateAccount: (
    id: number,
    payload: { name: string; type?: AccountType; starting_amount?: string },
  ) =>
    request<{ message: string }>(`/accounts/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  deleteAccount: (id: number) =>
    request<{ message: string }>(`/accounts/${id}`, { method: 'DELETE' }),

  // Credit cards
  listCreditCards: () => request<CreditCard[]>('/credit-cards'),
  createCreditCard: (payload: {
    name: string
    limit: string
    cutoff_day: number
    payment_day: number
  }) => request<{ id: number }>('/credit-cards', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  updateCreditCard: (
    id: number,
    payload: { name: string; limit: string; cutoff_day: number; payment_day: number },
  ) =>
    request<{ message: string }>(`/credit-cards/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  deleteCreditCard: (id: number) =>
    request<{ message: string }>(`/credit-cards/${id}`, { method: 'DELETE' }),

  // Savings
  listSavings: () => request<SavingsItem[]>('/savings'),
  createSavings: (payload: {
    name: string
    kind: SavingsKind
    target?: string | null
    rate_bp?: number | null
    term_days?: number | null
    current_value?: string | null
    scheduled_day?: number | null
    scheduled_amount?: string | null
    source_account_id?: number | null
    initial_amount?: string | null
    initial_account_id?: number | null
  }) => request<{ id: number }>('/savings', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  updateSavings: (
    id: number,
    payload: {
      name: string
      kind: SavingsKind
      target?: string | null
      rate_bp?: number | null
      term_days?: number | null
      current_value?: string | null
      scheduled_day?: number | null
      scheduled_amount?: string | null
      source_account_id?: number | null
    },
  ) =>
    request<{ message: string }>(`/savings/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  deleteSavings: (id: number) =>
    request<{ message: string }>(`/savings/${id}`, { method: 'DELETE' }),

  // Reports
  summary: (month: number, year: number) =>
    request<MonthlySummary>(`/reports/summary${query(month, year)}`),
  yearlySummaries: (year: number) => request<MonthlySummary[]>(`/reports/monthly?year=${year}`),
  categorySpending: (month: number, year: number, type: string = 'expense') =>
    request<CategorySpending[]>(`/reports/category-spending${query(month, year)}&type=${type}`),
  budgetVsActual: (month: number, year: number) =>
    request<BudgetVsActual[]>(`/reports/budget-vs-actual${query(month, year)}`),
  exportCsvUrl: (month: number, year: number) => `${BASE}/reports/export${query(month, year)}`,

  // Chat
  chatHistory: (month: number, year: number) =>
    request<ChatMessage[]>(`/chat${query(month, year)}`),
  sendChat: (question: string, month: number, year: number) =>
    request<ChatReply>('/chat', {
      method: 'POST',
      body: JSON.stringify({ question, month, year }),
    }),
  clearChat: (month: number, year: number) =>
    request<{ message: string }>(`/chat${query(month, year)}`, { method: 'DELETE' }),

  // AI configuration
  getAIConfig: () => request<AIConfig>('/ai/config'),
  updateAIConfig: (config: AIConfig) =>
    request<{ message: string }>('/ai/config', { method: 'PUT', body: JSON.stringify(config) }),
  testAIConnection: () =>
    request<ConnectionTest>('/ai/test-connection', { method: 'POST' }),
}
