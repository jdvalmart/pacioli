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

export interface KindMeta {
  label: string
  icon: LucideIcon
  /** Selected state of the kind button in the form. */
  activeClass: string
  /** Badge in the movements table. */
  badgeClass: string
  /** Color of the amount in the movements table. */
  amountClass: string
}

export const KIND_META: Record<TransactionKind, KindMeta> = {
  ingreso: {
    label: 'Ingreso',
    icon: ArrowDownLeft,
    activeClass: 'bg-emerald-500 border-emerald-700 text-white shadow-[0_4px_0_0_#047857]',
    badgeClass: 'bg-emerald-100 text-emerald-700',
    amountClass: 'text-emerald-600',
  },
  gasto: {
    label: 'Gasto',
    icon: ArrowUpRight,
    activeClass: 'bg-rose-500 border-rose-700 text-white shadow-[0_4px_0_0_#be123c]',
    badgeClass: 'bg-rose-100 text-rose-700',
    amountClass: 'text-red-600',
  },
  transferencia: {
    label: 'Transferencia',
    icon: ArrowLeftRight,
    activeClass: 'bg-blue-500 border-blue-700 text-white shadow-[0_4px_0_0_#1d4ed8]',
    badgeClass: 'bg-blue-100 text-blue-700',
    amountClass: 'text-blue-600',
  },
  gasto_tc: {
    label: 'Compra tarjeta',
    icon: CreditCard,
    activeClass: 'bg-orange-500 border-orange-700 text-white shadow-[0_4px_0_0_#c2410c]',
    badgeClass: 'bg-orange-100 text-orange-700',
    amountClass: 'text-red-600',
  },
  pago_tc: {
    label: 'Pago tarjeta',
    icon: Wallet,
    activeClass: 'bg-violet-500 border-violet-700 text-white shadow-[0_4px_0_0_#6d28d9]',
    badgeClass: 'bg-violet-100 text-violet-700',
    amountClass: 'text-red-600',
  },
  ahorro: {
    label: 'Ahorro',
    icon: PiggyBank,
    activeClass: 'bg-amber-500 border-amber-700 text-white shadow-[0_4px_0_0_#b45309]',
    badgeClass: 'bg-amber-100 text-amber-700',
    amountClass: 'text-red-600',
  },
  retiro: {
    label: 'Retiro',
    icon: HandCoins,
    activeClass: 'bg-teal-500 border-teal-700 text-white shadow-[0_4px_0_0_#0f766e]',
    badgeClass: 'bg-teal-100 text-teal-700',
    amountClass: 'text-red-600',
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
