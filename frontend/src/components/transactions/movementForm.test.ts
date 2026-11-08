import { describe, expect, it } from 'vitest'

import {
  initialMovementValues,
  toMovementPayload,
  validateMovement,
  type MovementFormValues,
} from '@/components/transactions/movementForm'
import type { Transaction } from '@/lib/types'

const NOV_2026 = { month: 11, year: 2026 }
const NOW = new Date(2026, 10, 8, 20, 0)
const ctx = { savingsMaturesOn: null, today: '2026-11-08' }

const base = (overrides: Partial<MovementFormValues>): MovementFormValues => ({
  ...initialMovementValues(null, NOV_2026, NOW),
  amount: '50.000',
  ...overrides,
})

describe('initialMovementValues', () => {
  it('starts a new movement as an expense dated today in the current month', () => {
    const v = initialMovementValues(null, NOV_2026, NOW)
    expect(v.kind).toBe('gasto')
    expect(v.date).toBe('2026-11-08')
    expect(v.subcategoryId).toBe('none')
    expect(v.installments).toBe('1')
  })

  it('loads an existing card purchase for editing (interest back to percent)', () => {
    const tx = {
      kind: 'gasto_tc',
      date: '2026-09-05',
      amount: '300000.00',
      card_id: 3,
      category_id: 7,
      installments: 6,
      interest_bp: 1250,
    } as Transaction
    const v = initialMovementValues(tx, NOV_2026, NOW)
    expect(v).toMatchObject({
      kind: 'gasto_tc',
      date: '2026-09-05',
      cardId: '3',
      categoryId: '7',
      installments: '6',
      interest: '12.5',
    })
  })
})

describe('validateMovement', () => {
  it.each<[string, Partial<MovementFormValues>, string]>([
    ['expense without category', { kind: 'gasto', accountId: '1' }, 'Selecciona una categoría'],
    ['card purchase without card', { kind: 'gasto_tc', categoryId: '7' }, 'Selecciona una tarjeta de crédito'],
    ['savings move without pocket', { kind: 'ahorro', accountId: '1' }, 'Selecciona el bolsillo o la inversión'],
    ['income without account', { kind: 'ingreso', categoryId: '2' }, 'Selecciona una cuenta — todo movimiento sale o entra por una cuenta'],
    ['transfer missing destination', { kind: 'transferencia', accountId: '1' }, 'Selecciona la cuenta de origen y la de destino'],
    ['transfer to the same account', { kind: 'transferencia', accountId: '1', toAccountId: '1' }, 'La cuenta de origen y la de destino deben ser distintas'],
  ])('rejects %s', (_, overrides, message) => {
    expect(validateMovement(base(overrides), ctx)).toBe(message)
  })

  it('rejects moving money from a locked CDT before it matures', () => {
    const v = base({ kind: 'retiro', savingsId: '4', accountId: '1' })
    expect(validateMovement(v, { savingsMaturesOn: '2027-01-15', today: '2026-11-08' })).toBe(
      'Este ahorro está bloqueado hasta 2027-01-15',
    )
    expect(validateMovement(v, { savingsMaturesOn: '2026-11-08', today: '2026-11-08' })).toBeNull()
  })

  it.each<[string, Partial<MovementFormValues>]>([
    ['expense', { kind: 'gasto', categoryId: '7', accountId: '1' }],
    ['card purchase (no account needed)', { kind: 'gasto_tc', categoryId: '7', cardId: '3' }],
    ['transfer (no category needed)', { kind: 'transferencia', accountId: '1', toAccountId: '2' }],
    ['savings move (no category needed)', { kind: 'ahorro', savingsId: '4', accountId: '1' }],
  ])('accepts a complete %s', (_, overrides) => {
    expect(validateMovement(base(overrides), ctx)).toBeNull()
  })
})

describe('toMovementPayload', () => {
  it('sends a card purchase without account, with interest in basis points', () => {
    const payload = toMovementPayload(
      base({ kind: 'gasto_tc', categoryId: '7', cardId: '3', installments: '6', interest: '12.5', accountId: '1' }),
    )
    expect(payload).toMatchObject({
      kind: 'gasto_tc',
      amount: '50000.00',
      account_id: null,
      card_id: 3,
      category_id: 7,
      installments: 6,
      interest_bp: 1250,
    })
  })

  it('ignores interest on a single-installment purchase', () => {
    const payload = toMovementPayload(
      base({ kind: 'gasto_tc', categoryId: '7', cardId: '3', installments: '1', interest: '20' }),
    )
    expect(payload.interest_bp).toBe(0)
  })

  it('sends a transfer with both accounts and no category or subcategory', () => {
    const payload = toMovementPayload(
      base({ kind: 'transferencia', accountId: '1', toAccountId: '2', categoryId: '7', subcategoryId: '9' }),
    )
    expect(payload).toMatchObject({
      account_id: 1,
      to_account_id: 2,
      category_id: null,
      subcategory_id: null,
      card_id: null,
      installments: 1,
    })
  })

  it('sends a savings move with its pocket and no category', () => {
    const payload = toMovementPayload(base({ kind: 'ahorro', savingsId: '4', accountId: '1', categoryId: '7' }))
    expect(payload).toMatchObject({ savings_id: 4, account_id: 1, category_id: null })
  })

  it('only sends a recurring day for recurring movements', () => {
    const once = toMovementPayload(base({ kind: 'gasto', categoryId: '7', accountId: '1', recurringDay: '5' }))
    const monthly = toMovementPayload(
      base({ kind: 'gasto', categoryId: '7', accountId: '1', isRecurring: true, recurringDay: '5' }),
    )
    expect(once.recurring_day).toBeNull()
    expect(monthly).toMatchObject({ is_recurring: true, recurring_day: 5 })
  })
})
