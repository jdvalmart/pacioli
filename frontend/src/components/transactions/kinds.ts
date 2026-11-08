/**
 * Presentation of each movement kind: label, icon and colors, in one table.
 * The kinds themselves come from the API contract (TxKind).
 */
import {
  ArrowDownLeft,
  ArrowLeftRight,
  ArrowUpRight,
  CreditCard,
  HandCoins,
  PiggyBank,
  Wallet,
  type LucideIcon,
} from 'lucide-react'

import type { Transaction, TransactionKind } from '@/lib/types'

/** Selected kind in the form: the brand accent, same for every kind. */
const SELECTED = 'border-primary bg-brand-soft text-foreground ring-1 ring-primary/40'

export interface KindMeta {
  label: string
  icon: LucideIcon
  /** Selected state of the kind button in the form. */
  activeClass: string
  /** Color of the amount in the movements table. */
  amountClass: string
  /** Effect on the user's cash accounts: '+' money in, '-' money out, '' moved between own accounts. */
  sign: '+' | '-' | ''
}

export const KIND_META: Record<TransactionKind, KindMeta> = {
  ingreso: {
    label: 'Ingreso',
    icon: ArrowDownLeft,
    activeClass: SELECTED,
    amountClass: 'text-positive',
    sign: '+',
  },
  gasto: {
    label: 'Gasto',
    icon: ArrowUpRight,
    activeClass: SELECTED,
    amountClass: 'text-foreground',
    sign: '-',
  },
  transferencia: {
    label: 'Transferencia',
    icon: ArrowLeftRight,
    activeClass: SELECTED,
    amountClass: 'text-muted-foreground',
    sign: '',
  },
  gasto_tc: {
    label: 'Compra tarjeta',
    icon: CreditCard,
    activeClass: SELECTED,
    amountClass: 'text-foreground',
    sign: '-',
  },
  pago_tc: {
    label: 'Pago tarjeta',
    icon: Wallet,
    activeClass: SELECTED,
    amountClass: 'text-foreground',
    sign: '-',
  },
  ahorro: {
    label: 'Ahorro',
    icon: PiggyBank,
    activeClass: SELECTED,
    amountClass: 'text-foreground',
    sign: '-',
  },
  retiro: {
    label: 'Retiro',
    icon: HandCoins,
    activeClass: SELECTED,
    amountClass: 'text-positive',
    sign: '+',
  },
}

/** Display order of the kinds (filters, lists). */
export const KIND_ORDER: TransactionKind[] = [
  'ingreso',
  'gasto',
  'transferencia',
  'gasto_tc',
  'pago_tc',
  'ahorro',
  'retiro',
]

/** Kinds the movement form offers; card payments are made from the card ("Pagar"). */
export const FORM_KINDS: TransactionKind[] = KIND_ORDER.filter((kind) => kind !== 'pago_tc')

export const amountClass = (tx: Transaction) => KIND_META[tx.kind].amountClass
