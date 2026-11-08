/**
 * Frontend names for the API types.
 *
 * Every type comes from src/lib/api-schema.ts, which is generated from the
 * backend's OpenAPI contract (`npm run gen:api`); never edit that file by
 * hand. Changing a backend schema and regenerating is the only way these
 * types change, and CI fails if the generated file is stale.
 *
 * Money amounts are fixed-precision strings (e.g. "1234.56") to avoid
 * JSON float64 precision loss.
 */
import type { components } from '@/lib/api-schema'

type Schemas = components['schemas']

export type Category = Schemas['CategoryOut']
export type CategoryType = Category['type']
export type Subcategory = Schemas['SubcategoryOut']

export type TransactionKind = Schemas['TxKind']
export type Transaction = Schemas['TransactionOut']
export type TransactionInput = Schemas['TransactionIn']

export type Account = Schemas['AccountOut']
export type AccountType = Account['type']

export type CreditCard = Schemas['CreditCardOut']

export type SavingsItem = Schemas['SavingsOut']
export type SavingsKind = SavingsItem['kind']

export type Budget = Schemas['BudgetOut']
export type BudgetPlan = Schemas['BudgetPlanOut']

export type MonthlySummary = Schemas['MonthlySummaryOut']
export type CategorySpending = Schemas['CategorySpendingOut']
export type BudgetVsActual = Schemas['BudgetVsActualOut']
