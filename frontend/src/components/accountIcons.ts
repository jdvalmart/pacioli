import { Banknote, Landmark, PiggyBank, Smartphone, type LucideIcon } from 'lucide-react'

import type { AccountType } from '@/lib/types'

/** Neutral icon per account type (the stored emoji is kept for the API). */
export const ACCOUNT_ICON: Record<AccountType, LucideIcon> = {
  banco: Landmark,
  digital: Smartphone,
  efectivo: Banknote,
  ahorros: PiggyBank,
}
