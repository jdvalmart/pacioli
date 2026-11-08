/**
 * Pure rules of the movement form: initial values, validation and the
 * request payload. No React here, so every rule is unit-tested.
 */
import type { Month } from '@/hooks/useMonth'
import { defaultMovementDate } from '@/lib/dates'
import { normalizeAmount } from '@/lib/money'
import type { Transaction, TransactionInput, TransactionKind } from '@/lib/types'

/** Form state; select values are strings ('' = nothing chosen). */
export interface MovementFormValues {
  kind: TransactionKind
  date: string
  amount: string
  categoryId: string
  /** 'none' = no subcategory. */
  subcategoryId: string
  accountId: string
  toAccountId: string
  cardId: string
  installments: string
  /** Total plan interest in percent, as typed (e.g. "12.5"). */
  interest: string
  savingsId: string
  description: string
  isRecurring: boolean
  recurringDay: string
}

export const isSavingsKind = (kind: TransactionKind) => kind === 'ahorro' || kind === 'retiro'
/** Transfers and savings moves have no category. */
export const needsCategory = (kind: TransactionKind) =>
  kind !== 'transferencia' && !isSavingsKind(kind)
/** Money goes in or out of one account (card purchases hit the card instead). */
export const needsAccount = (kind: TransactionKind) =>
  kind === 'ingreso' || kind === 'gasto' || isSavingsKind(kind)

const idOrEmpty = (id: number | null | undefined) => (id ? String(id) : '')

export function initialMovementValues(
  transaction: Transaction | null,
  month: Month,
  now: Date = new Date(),
): MovementFormValues {
  return {
    kind: transaction?.kind ?? 'gasto',
    date: transaction?.date ?? defaultMovementDate(month, now),
    amount: transaction?.amount ?? '',
    categoryId: idOrEmpty(transaction?.category_id),
    subcategoryId: transaction?.subcategory_id ? String(transaction.subcategory_id) : 'none',
    accountId: idOrEmpty(transaction?.account_id),
    toAccountId: idOrEmpty(transaction?.to_account_id),
    cardId: idOrEmpty(transaction?.card_id),
    installments: String(transaction?.installments ?? 1),
    interest: transaction?.interest_bp ? String(transaction.interest_bp / 100) : '',
    savingsId: idOrEmpty(transaction?.savings_id),
    description: transaction?.description ?? '',
    isRecurring: transaction?.is_recurring ?? false,
    recurringDay: String(transaction?.recurring_day ?? 1),
  }
}

/**
 * First rule the form breaks, as a message for the user, or null if valid.
 * ``savingsMaturesOn`` is the lock date of the chosen savings item, if any.
 */
export function validateMovement(
  v: MovementFormValues,
  context: { savingsMaturesOn: string | null; today: string },
): string | null {
  const savings = isSavingsKind(v.kind)
  if (needsCategory(v.kind) && !v.categoryId) return 'Selecciona una categoría'
  if (v.kind === 'gasto_tc' && !v.cardId) return 'Selecciona una tarjeta de crédito'
  if (savings && !v.savingsId) return 'Selecciona el bolsillo o la inversión'
  if (savings && context.savingsMaturesOn != null && context.savingsMaturesOn > context.today) {
    return `Este ahorro está bloqueado hasta ${context.savingsMaturesOn}`
  }
  if (needsAccount(v.kind) && !v.accountId) {
    return 'Selecciona una cuenta — todo movimiento sale o entra por una cuenta'
  }
  if (v.kind === 'transferencia') {
    if (!v.accountId || !v.toAccountId) return 'Selecciona la cuenta de origen y la de destino'
    if (v.accountId === v.toAccountId) return 'La cuenta de origen y la de destino deben ser distintas'
  }
  return null
}

/** Request body for a valid form: fields that do not apply to the kind are null. */
export function toMovementPayload(v: MovementFormValues): TransactionInput {
  const isCard = v.kind === 'gasto_tc'
  const isTransfer = v.kind === 'transferencia'
  const installments = isCard ? Number(v.installments) || 1 : 1
  return {
    date: v.date,
    amount: normalizeAmount(v.amount),
    kind: v.kind,
    category_id: needsCategory(v.kind) ? Number(v.categoryId) : null,
    subcategory_id: isTransfer || v.subcategoryId === 'none' ? null : Number(v.subcategoryId),
    account_id: isCard ? null : Number(v.accountId),
    to_account_id: isTransfer ? Number(v.toAccountId) : null,
    card_id: isCard ? Number(v.cardId) : null,
    savings_id: isSavingsKind(v.kind) ? Number(v.savingsId) : null,
    installments,
    // Interest only applies to plans of more than one installment (basis points).
    interest_bp: isCard && installments > 1 ? Math.round(Number(v.interest || '0') * 100) : 0,
    description: v.description,
    is_recurring: v.isRecurring,
    recurring_day: v.isRecurring ? Number(v.recurringDay) : null,
  }
}
