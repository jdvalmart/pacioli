/** Presentation of each savings kind (pocket, programmed pocket, CDT, stocks). */
import type { SavingsKind } from '@/lib/types'

export const SAVINGS_KIND_META: Record<SavingsKind, { label: string; icon: string }> = {
  bolsillo: { label: 'Bolsillo', icon: '👝' },
  bolsillo_programado: { label: 'Bolsillo programado', icon: '📆' },
  cdt: { label: 'CDT', icon: '🏦' },
  acciones: { label: 'Acciones', icon: '📈' },
}
