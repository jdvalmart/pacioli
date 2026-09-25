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

export type TransactionKind =
  | 'ingreso'
  | 'gasto'
  | 'transferencia'
  | 'gasto_tc'
  | 'pago_tc'
  | 'ahorro'
  | 'retiro'

export interface Transaction {
  id: number
  date: string
  amount: string
  kind: TransactionKind
  category_id: number | null
  description: string
  is_recurring: boolean
  recurring_day: number | null
  subcategory_id: number | null
  subcategory_name: string | null
  subcategory_icon: string | null
  generated_from: number | null
  category_name: string | null
  category_type: CategoryType | null
  color: string | null
  icon: string | null
  account_id: number | null
  account_name: string | null
  account_icon: string | null
  to_account_id: number | null
  to_account_name: string | null
  to_account_icon: string | null
  card_id: number | null
  card_name: string | null
  installments: number
  interest_bp: number
  savings_id: number | null
  savings_name: string | null
}

export interface TransactionInput {
  date: string
  amount: string
  kind: TransactionKind
  category_id: number | null
  account_id: number | null
  to_account_id: number | null
  card_id?: number | null
  savings_id?: number | null
  installments?: number
  interest_bp?: number
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
  starting: string
  balance: string
}

export interface CreditCard {
  id: number
  name: string
  limit: string
  cutoff_day: number
  payment_day: number
  pending: string
  debt: string
  outstanding: string
  available: string
  cycle_start: string
  cycle_end: string
  payment_date: string
}

export type SavingsKind = 'bolsillo' | 'bolsillo_programado' | 'cdt' | 'acciones'

export interface SavingsItem {
  id: number
  name: string
  kind: SavingsKind
  target: string | null
  rate_bp: number | null
  term_days: number | null
  current_value: string | null
  dividends: string
  scheduled_day: number | null
  scheduled_amount: string | null
  source_account_id: number | null
  opening: string
  balance: string
  invested: string
  matures_on: string | null
}

export interface Budget {
  id: number
  category_id: number
  month: number
  year: number
  amount: string
}

export interface BudgetPlan {
  month: number
  year: number
  total: string | null
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
