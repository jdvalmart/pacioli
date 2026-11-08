/**
 * State and behaviour of the movement form: field state, the data it
 * offers (accounts, cards, categories, savings), validation and saving.
 * The rules themselves are pure functions in ./movementForm.
 */
import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'

import {
  initialMovementValues,
  isSavingsKind as kindIsSavings,
  needsAccount as kindNeedsAccount,
  toMovementPayload,
  validateMovement,
  type MovementFormValues,
} from '@/components/transactions/movementForm'
import { useMonth } from '@/hooks/useMonth'
import { api } from '@/lib/api'
import { todayISO } from '@/lib/dates'
import {
  useAccounts,
  useCategories,
  useCreditCards,
  useInvalidate,
  useSavings,
  useSubcategories,
} from '@/lib/queries'
import type { Transaction, TransactionInput, TransactionKind } from '@/lib/types'

export function useTransactionForm(transaction: Transaction | null, onSaved: () => void) {
  const { month } = useMonth()
  const invalidate = useInvalidate()
  const categories = useCategories()
  const accounts = useAccounts()
  const creditCards = useCreditCards()
  const savings = useSavings()

  const [initial] = useState(() => initialMovementValues(transaction, month))
  const [kind, setKind] = useState<TransactionKind>(initial.kind)
  const [date, setDate] = useState(initial.date)
  const [amount, setAmount] = useState(initial.amount)
  const [categoryId, setCategoryId] = useState(initial.categoryId)
  const [subcategoryId, setSubcategoryId] = useState(initial.subcategoryId)
  const [accountId, setAccountId] = useState(initial.accountId)
  const [toAccountId, setToAccountId] = useState(initial.toAccountId)
  const [cardId, setCardId] = useState(initial.cardId)
  const [installments, setInstallments] = useState(initial.installments)
  const [interest, setInterest] = useState(initial.interest)
  const [savingsId, setSavingsId] = useState(initial.savingsId)
  const [description, setDescription] = useState(initial.description)
  const [isRecurring, setIsRecurring] = useState(initial.isRecurring)
  const [recurringDay, setRecurringDay] = useState(initial.recurringDay)
  const [savingsFormOpen, setSavingsFormOpen] = useState(false)

  const values: MovementFormValues = {
    kind,
    date,
    amount,
    categoryId,
    subcategoryId,
    accountId,
    toAccountId,
    cardId,
    installments,
    interest,
    savingsId,
    description,
    isRecurring,
    recurringDay,
  }

  const visibleCategories = (categories.data ?? []).filter((c) =>
    kind === 'ingreso' ? c.type === 'income' : c.type === 'expense',
  )
  const selectedSavings = (savings.data ?? []).find((s) => String(s.id) === savingsId)
  const savingsIsBolsillo = (selectedSavings?.kind ?? 'bolsillo') === 'bolsillo'
  const todayStr = todayISO()
  const selectedSavingsLocked =
    selectedSavings?.matures_on != null && selectedSavings.matures_on > todayStr

  const subcategories = useSubcategories(categoryId ? Number(categoryId) : null)
  const filteredSubcategories = subcategories.data ?? []
  const subValue = filteredSubcategories.some((s) => String(s.id) === subcategoryId)
    ? subcategoryId
    : 'none'

  const accountList = accounts.data ?? []
  const hasAccounts = accountList.length > 0
  const isSavingsKind = kindIsSavings(kind)
  const needsAccount = kindNeedsAccount(kind)
  const accountLabel =
    kind === 'ingreso' ? 'Cuenta destino' : kind === 'gasto' ? 'Cuenta origen' : 'Cuenta'

  const mutation = useMutation({
    mutationFn: async (payload: TransactionInput) => {
      if (transaction) {
        await api.updateTransaction(transaction.id, payload)
      } else {
        await api.createTransaction(payload)
      }
    },
    onSuccess: () => {
      toast.success(transaction ? 'Movimiento actualizado' : 'Movimiento creado')
      onSaved()
      void invalidate('movement')
    },
    onError: (error: Error) => toast.error(error.message),
  })

  /** Changing the kind clears the choices that only made sense for the old one. */
  const handleKindChange = (next: TransactionKind) => {
    setKind(next)
    setCategoryId('')
    setSubcategoryId('none')
    setSavingsId('')
  }

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    const error = validateMovement(values, {
      savingsMaturesOn: selectedSavings?.matures_on ?? null,
      today: todayStr,
    })
    if (error) {
      toast.error(error)
      return
    }
    mutation.mutate(toMovementPayload(values))
  }

  return {
    // Field state
    kind,
    date,
    setDate,
    amount,
    setAmount,
    categoryId,
    setCategoryId,
    setSubcategoryId,
    accountId,
    setAccountId,
    toAccountId,
    setToAccountId,
    cardId,
    setCardId,
    installments,
    setInstallments,
    interest,
    setInterest,
    savingsId,
    setSavingsId,
    description,
    setDescription,
    isRecurring,
    setIsRecurring,
    recurringDay,
    setRecurringDay,
    savingsFormOpen,
    setSavingsFormOpen,
    // Data and derived state
    creditCards,
    savings,
    accountList,
    hasAccounts,
    visibleCategories,
    filteredSubcategories,
    subValue,
    selectedSavings,
    selectedSavingsLocked,
    savingsIsBolsillo,
    isSavingsKind,
    needsAccount,
    accountLabel,
    todayStr,
    // Actions
    mutation,
    handleKindChange,
    handleSubmit,
  }
}
