/**
 * TypeScript types mirroring the Pacioli API schemas.
 *
 * Money amounts arrive as fixed-precision strings (e.g. "1234.56")
 * from the API to avoid JSON float64 precision loss.
 */

export type CategoryType = 'income' | 'expense'

export interface Category {
  id: number
  name: string
  type: CategoryType
  color: string
  icon: string
}

export interface Subcategory {
  id: number
  category_id: number
  name: string
  icon: string
}

export interface Transaction {
  id: number
  date: string
  amount: string
  category_id: number
  description: string
  is_recurring: boolean
  recurring_day: number | null
  subcategory_id: number | null
  subcategory_name: string | null
  subcategory_icon: string | null
  generated_from: number | null
  category_name: string
  category_type: CategoryType
  color: string
  icon: string
  account_id: number | null
  account_name: string | null
  account_icon: string | null
}

export interface TransactionInput {
  date: string
  amount: string
  category_id: number
  account_id: number
  description?: string
  is_recurring?: boolean
  recurring_day?: number | null
  subcategory_id?: number | null
}

export type AccountType = 'efectivo' | 'digital' | 'ahorros' | 'banco'

export interface Account {
  id: number
  name: string
  type: AccountType
  icon: string
  color: string
  balance: string
}

export interface Budget {
  id: number
  category_id: number
  month: number
  year: number
  amount: string
}

export interface MonthlySummary {
  month: number
  year: number
  total_income: string
  total_expense: string
  balance: string
  carryover: string
  accumulated_balance: string
  by_category: Record<string, string>
}

export interface CategorySpending {
  name: string
  total: string
  color: string
  icon: string
}

export interface BudgetVsActual {
  category_id: number
  name: string
  color: string
  icon: string
  budget: string
  actual: string
  remaining: string
  percent: number
}

export interface ChatMessage {
  role: 'user' | 'ai'
  message: string
  created_at: string
}

export interface ChatReply {
  answer: string
  error: string | null
}

export interface AIConfig {
  model: string
  url: string
  timeout: number
  temperature: number
  max_tokens: number
  think: 'off' | 'low' | 'medium' | 'high'
}

export interface ConnectionTest {
  success: boolean
  message: string
}
