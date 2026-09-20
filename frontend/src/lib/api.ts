/**
 * Typed API client for the Pacioli backend.
 *
 * The Vite dev server proxies /api/* to http://localhost:8000.
 */

import type {
  AIConfig,
  Budget,
  BudgetVsActual,
  Category,
  CategorySpending,
  ChatMessage,
  ChatReply,
  ConnectionTest,
  MonthlySummary,
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
  deleteBudget: (categoryId: number, month: number, year: number) =>
    request<{ message: string }>(
      `/budgets?category_id=${categoryId}&month=${month}&year=${year}`,
      { method: 'DELETE' },
    ),

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
