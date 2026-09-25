import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import {
  ArrowDownLeft,
  ArrowLeftRight,
  ArrowUpRight,
  CreditCard,
  HandCoins,
  Pencil,
  PiggyBank,
  Plus,
  Trash2,
  Wallet,
} from 'lucide-react'
import { toast } from 'sonner'
import { useSearchParams } from 'react-router-dom'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useMonth } from '@/hooks/useMonth'
import { api } from '@/lib/api'
import { SavingsFormDialog } from '@/components/SavingsFormDialog'
import { fmtCopDecimals, normalizeAmount } from '@/lib/money'
import type { Transaction, TransactionInput, TransactionKind } from '@/lib/types'

const KIND_OPTIONS: {
  value: TransactionKind
  label: string
  icon: typeof ArrowDownLeft
  activeClass: string
}[] = [
  {
    value: 'ingreso',
    label: 'Income',
    icon: ArrowDownLeft,
    activeClass: 'bg-emerald-500 border-emerald-700 text-white shadow-[0_4px_0_0_#047857]',
  },
  {
    value: 'gasto',
    label: 'Expense',
    icon: ArrowUpRight,
    activeClass: 'bg-rose-500 border-rose-700 text-white shadow-[0_4px_0_0_#be123c]',
  },
  {
    value: 'transferencia',
    label: 'Transfer',
    icon: ArrowLeftRight,
    activeClass: 'bg-blue-500 border-blue-700 text-white shadow-[0_4px_0_0_#1d4ed8]',
  },
  {
    value: 'gasto_tc',
    label: 'Card Expense',
    icon: CreditCard,
    activeClass: 'bg-orange-500 border-orange-700 text-white shadow-[0_4px_0_0_#c2410c]',
  },
  {
    value: 'ahorro',
    label: 'Saving',
    icon: PiggyBank,
    activeClass: 'bg-amber-500 border-amber-700 text-white shadow-[0_4px_0_0_#b45309]',
  },
  {
    value: 'retiro',
    label: 'Withdrawal',
    icon: HandCoins,
    activeClass: 'bg-teal-500 border-teal-700 text-white shadow-[0_4px_0_0_#0f766e]',
  },
]

interface TransactionFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  transaction: Transaction | null
}

function TransactionForm({ open, onOpenChange, transaction }: TransactionFormProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {open && <TransactionFormBody transaction={transaction} onOpenChange={onOpenChange} />}
      </DialogContent>
    </Dialog>
  )
}

function TransactionFormBody({
  transaction,
  onOpenChange,
}: {
  transaction: Transaction | null
  onOpenChange: (open: boolean) => void
}) {
  const { month } = useMonth()
  const queryClient = useQueryClient()
  const categories = useQuery({ queryKey: ['categories'], queryFn: () => api.listCategories() })
  const accounts = useQuery({ queryKey: ['accounts'], queryFn: api.listAccounts })
  const creditCards = useQuery({
    queryKey: ['creditCards'],
    queryFn: () => api.listCreditCards(),
  })
  const savings = useQuery({ queryKey: ['savings'], queryFn: api.listSavings })

  const [kind, setKind] = useState<TransactionKind>(transaction?.kind ?? 'gasto')
  const [date, setDate] = useState(
    transaction?.date ?? `${month.year}-${String(month.month).padStart(2, '0')}-15`,
  )
  const [amount, setAmount] = useState(transaction?.amount ?? '')
  const [categoryId, setCategoryId] = useState(
    transaction?.category_id ? String(transaction.category_id) : '',
  )
  const [subcategoryId, setSubcategoryId] = useState(
    transaction?.subcategory_id ? String(transaction.subcategory_id) : 'none',
  )
  const [accountId, setAccountId] = useState(
    transaction?.account_id ? String(transaction.account_id) : '',
  )
  const [toAccountId, setToAccountId] = useState(
    transaction?.to_account_id ? String(transaction.to_account_id) : '',
  )
  const [cardId, setCardId] = useState(transaction?.card_id ? String(transaction.card_id) : '')
  const [installments, setInstallments] = useState(String(transaction?.installments ?? 1))
  const [interest, setInterest] = useState(
    transaction?.interest_bp ? String(transaction.interest_bp / 100) : '',
  )
  const [savingsId, setSavingsId] = useState(
    transaction?.savings_id ? String(transaction.savings_id) : '',
  )
  const [savingsFormOpen, setSavingsFormOpen] = useState(false)
  const [description, setDescription] = useState(transaction?.description ?? '')
  const [isRecurring, setIsRecurring] = useState(transaction?.is_recurring ?? false)
  const [recurringDay, setRecurringDay] = useState(String(transaction?.recurring_day ?? 1))

  const incomeCategories = (categories.data ?? []).filter((c) => c.type === 'income')
  const expenseCategories = (categories.data ?? []).filter((c) => c.type === 'expense')
  const visibleCategories = kind === 'ingreso' ? incomeCategories : expenseCategories
  const selectedSavings = (savings.data ?? []).find((s) => String(s.id) === savingsId)
  const savingsIsBolsillo = (selectedSavings?.kind ?? 'bolsillo') === 'bolsillo'
  const todayStr = new Date().toISOString().slice(0, 10)
  const selectedSavingsLocked =
    selectedSavings?.matures_on != null && selectedSavings.matures_on > todayStr

  const subcategories = useQuery({
    queryKey: ['subcategories', categoryId],
    queryFn: () => api.listSubcategories(Number(categoryId)),
    enabled: !!categoryId,
  })

  const mutation = useMutation({
    mutationFn: async (payload: TransactionInput) => {
      if (transaction) {
        await api.updateTransaction(transaction.id, payload)
      } else {
        await api.createTransaction(payload)
      }
    },
    onSuccess: () => {
      toast.success(transaction ? 'Transaction updated' : 'Transaction created')
      onOpenChange(false)
      void queryClient.invalidateQueries({ queryKey: ['transactions'] })
      void queryClient.invalidateQueries({ queryKey: ['summary'] })
      void queryClient.invalidateQueries({ queryKey: ['categorySpending'] })
      void queryClient.invalidateQueries({ queryKey: ['budgetVsActual'] })
      void queryClient.invalidateQueries({ queryKey: ['accounts'] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const accountList = accounts.data ?? []
  const hasAccounts = accountList.length > 0

  const isSavingsKind = kind === 'ahorro' || kind === 'retiro'
  const needsAccount = kind === 'ingreso' || kind === 'gasto' || isSavingsKind
  const needsTwoAccounts = kind === 'transferencia'

  const handleKindChange = (next: TransactionKind) => {
    setKind(next)
    setCategoryId('')
    setSubcategoryId('none')
    setSavingsId('')
  }

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    if (kind !== 'transferencia' && !isSavingsKind && !categoryId) {
      toast.error('Select a category')
      return
    }
    if (kind === 'gasto_tc' && !cardId) {
      toast.error('Select a credit card')
      return
    }
    if (isSavingsKind && !savingsId) {
      toast.error('Select the pocket or investment')
      return
    }
    if (isSavingsKind && selectedSavingsLocked) {
      toast.error(`This savings is locked until ${selectedSavings?.matures_on}`)
      return
    }
    if (needsAccount && !accountId) {
      toast.error('Select an account — every transaction comes from or goes to an account')
      return
    }
    if (needsTwoAccounts) {
      if (!accountId || !toAccountId) {
        toast.error('Select the source and destination accounts')
        return
      }
      if (accountId === toAccountId) {
        toast.error('Source and destination accounts must be different')
        return
      }
    }
    mutation.mutate({
      date,
      amount: normalizeAmount(amount),
      kind,
      category_id: kind === 'transferencia' || isSavingsKind ? null : Number(categoryId),
      subcategory_id: kind === 'transferencia' || subcategoryId === 'none' ? null : Number(subcategoryId),
      account_id: kind === 'gasto_tc' ? null : Number(accountId),
      to_account_id: kind === 'transferencia' ? Number(toAccountId) : null,
      card_id: kind === 'gasto_tc' ? Number(cardId) : null,
      savings_id: isSavingsKind ? Number(savingsId) : null,
      installments: kind === 'gasto_tc' ? Number(installments) || 1 : 1,
      interest_bp:
        kind === 'gasto_tc' && Number(installments) > 1
          ? Math.round(Number(interest || '0') * 100)
          : 0,
      description,
      is_recurring: isRecurring,
      recurring_day: isRecurring ? Number(recurringDay) : null,
    })
  }

  const filteredSubcategories = subcategories.data ?? []
  const subValue = filteredSubcategories.some((s) => String(s.id) === subcategoryId)
    ? subcategoryId
    : 'none'

  const accountLabel =
    kind === 'ingreso' ? 'Destination account' : kind === 'gasto' ? 'Source account' : 'Account'

  return (
    <>
      <DialogHeader>
        <DialogTitle>{transaction ? 'Edit transaction' : 'New transaction'}</DialogTitle>
        <DialogDescription>
          {transaction ? 'Update the details and save.' : 'Record a transaction for this month.'}
        </DialogDescription>
      </DialogHeader>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-3 gap-2">
          {KIND_OPTIONS.map(({ value, label, icon: Icon, activeClass }) => (
            <button
              key={value}
              type="button"
              onClick={() => handleKindChange(value)}
              className={`flex flex-col items-center gap-1 rounded-xl border px-2 py-2.5 text-xs font-bold transition-all ${
                kind === value
                  ? activeClass
                  : 'border-border bg-background text-muted-foreground hover:bg-muted'
              }`}
            >
              <Icon className="size-4" />
              {label}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="tx-date">Date</Label>
            <Input
              id="tx-date"
              type="date"
              required
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="tx-amount">Amount</Label>
            <Input
              id="tx-amount"
              required
              placeholder="50.000"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </div>
        </div>

        {kind === 'transferencia' ? (
          <>
            <div className="space-y-1.5">
              <Label>From</Label>
              <Select value={accountId} onValueChange={(v) => setAccountId(v ?? '')}>
                <SelectTrigger>
                  <SelectValue placeholder="Source account" />
                </SelectTrigger>
                <SelectContent>
                  {accountList.map((account) => (
                    <SelectItem key={account.id} value={String(account.id)}>
                      {account.icon} {account.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>To</Label>
              <Select value={toAccountId} onValueChange={(v) => setToAccountId(v ?? '')}>
                <SelectTrigger>
                  <SelectValue placeholder="Destination account" />
                </SelectTrigger>
                <SelectContent>
                  {accountList.map((account) => (
                    <SelectItem key={account.id} value={String(account.id)}>
                      {account.icon} {account.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Moving money between your accounts doesn't affect income or expenses.
              </p>
            </div>
          </>
        ) : isSavingsKind ? (
          <>
            <div className="space-y-1.5">
              <Label>{kind === 'ahorro' ? 'Destination pocket' : 'Source pocket'}</Label>
              {(savings.data ?? []).length > 0 && (
                <Select value={savingsId} onValueChange={(v) => setSavingsId(v ?? '')}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select the pocket" />
                  </SelectTrigger>
                  <SelectContent>
                    {(savings.data ?? []).map((item) => {
                      const isLocked = item.matures_on != null && item.matures_on > todayStr
                      return (
                        <SelectItem key={item.id} value={String(item.id)} disabled={isLocked}>
                          {item.kind === 'cdt' ? '🏦' : item.kind === 'acciones' ? '📈' : item.kind === 'bolsillo_programado' ? '📆' : '👝'}{' '}
                          {item.name}
                          {isLocked ? ' 🔒' : ''}
                        </SelectItem>
                      )
                    })}
                  </SelectContent>
                </Select>
              )}
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="w-full"
                onClick={() => setSavingsFormOpen(true)}
              >
                <Plus /> Create pocket, CD or stocks
              </Button>
              {selectedSavingsLocked && (
                <p className="text-xs font-bold text-amber-600">
                  🔒 Locked until {selectedSavings?.matures_on} — you can't move money until maturity.
                </p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label>{kind === 'ahorro' ? 'Source account' : 'Destination account'}</Label>
              {!hasAccounts ? (
                <div className="rounded-xl border border-dashed border-primary/50 bg-primary/10 p-3 text-sm font-semibold text-muted-foreground">
                  You don't have any accounts yet. Create one in the Dashboard.
                </div>
              ) : (
                <Select value={accountId} onValueChange={(v) => setAccountId(v ?? '')}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select an account" />
                  </SelectTrigger>
                  <SelectContent>
                    {accountList.map((account) => (
                      <SelectItem key={account.id} value={String(account.id)}>
                        {account.icon} {account.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <p className="text-xs text-muted-foreground">
                {kind === 'ahorro'
                  ? savingsIsBolsillo
                    ? 'Assigned to pocket: money stays in your account, just set aside.'
                    : 'Money leaves your account to savings (not counted as an expense).'
                  : savingsIsBolsillo
                    ? 'Released from pocket: money stays in your account.'
                    : 'Money returns to your account.'}
              </p>
            </div>
          </>
        ) : (
          <>
            <div className="space-y-1.5">
              <Label>Category</Label>
              <Select value={categoryId} onValueChange={(v) => setCategoryId(v ?? '')}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a category" />
                </SelectTrigger>
                <SelectContent>
                  {visibleCategories.map((cat) => (
                    <SelectItem key={cat.id} value={String(cat.id)}>
                      {cat.icon} {cat.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {categoryId !== '' && kind !== 'gasto_tc' && (
              <div className="space-y-1.5">
                <Label>Subcategory (optional)</Label>
                <Select value={subValue} onValueChange={(v) => setSubcategoryId(v ?? 'none')}>
                  <SelectTrigger>
                    <SelectValue placeholder="No subcategory" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No subcategory</SelectItem>
                    {filteredSubcategories.map((sub) => (
                      <SelectItem key={sub.id} value={String(sub.id)}>
                        {sub.icon} {sub.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {kind === 'gasto_tc' ? (
              <div className="space-y-1.5">
                <Label>Credit card</Label>
                {(creditCards.data ?? []).length === 0 ? (
                  <div className="rounded-xl border border-dashed border-orange-400/60 bg-orange-500/10 p-3 text-sm font-semibold text-muted-foreground">
                    💳 You don't have any cards yet. Create one in the Dashboard (Credit
                    Cards section) to record card expenses.
                  </div>
                ) : (
                  <>
                    <Select value={cardId} onValueChange={(v) => setCardId(v ?? '')}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select the card" />
                      </SelectTrigger>
                      <SelectContent>
                        {(creditCards.data ?? []).map((card) => (
                          <SelectItem key={card.id} value={String(card.id)}>
                            💳 {card.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      Deducted from the card's available credit.
                    </p>
                    <div className="grid grid-cols-2 gap-3 pt-1">
                      <div className="space-y-1.5">
                        <Label htmlFor="tx-installments">Installments</Label>
                        <Input
                          id="tx-installments"
                          type="number"
                          min={1}
                          max={60}
                          value={installments}
                          onChange={(e) => setInstallments(e.target.value)}
                        />
                      </div>
                      {Number(installments) > 1 && (
                        <div className="space-y-1.5">
                          <Label htmlFor="tx-interest">Total interest (%)</Label>
                          <Input
                            id="tx-interest"
                            type="number"
                            min={0}
                            step={0.1}
                            placeholder="0"
                            value={interest}
                            onChange={(e) => setInterest(e.target.value)}
                          />
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {Number(installments) > 1
                        ? `Installment: ${fmtCopDecimals(
                            (Number(normalizeAmount(amount || '0')) *
                              (1 + Number(interest || '0') / 100)) /
                              (Number(installments) || 1),
                          )} per month`
                        : 'No interest charged for 1 installment.'}
                    </p>
                  </>
                )}
              </div>
            ) : (
              <div className="space-y-1.5">
                <Label>{accountLabel}</Label>
                {!hasAccounts ? (
                  <div className="rounded-xl border border-dashed border-primary/50 bg-primary/10 p-3 text-sm font-semibold text-muted-foreground">
                    You don't have any accounts yet. Create one in the Dashboard (wallet,
                    bank, savings…) to record transactions.
                  </div>
                ) : (
                  <>
                    <Select value={accountId} onValueChange={(v) => setAccountId(v ?? '')}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select an account" />
                      </SelectTrigger>
                      <SelectContent>
                        {accountList.map((account) => (
                          <SelectItem key={account.id} value={String(account.id)}>
                            {account.icon} {account.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      {kind === 'ingreso'
                        ? 'Which account the money goes into.'
                        : 'Which account the money comes from.'}
                    </p>
                  </>
                )}
              </div>
            )}
          </>
        )}

        <div className="space-y-1.5">
          <Label htmlFor="tx-description">Description</Label>
          <Input
            id="tx-description"
            placeholder="E.g. Weekly groceries"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-3">
          <input
            id="tx-recurring"
            type="checkbox"
            checked={isRecurring}
            onChange={(e) => setIsRecurring(e.target.checked)}
          />
          <Label htmlFor="tx-recurring">Recurring (rent, utilities, savings…)</Label>
        </div>
        {isRecurring && (
          <div className="space-y-1.5">
            <Label htmlFor="tx-day">Day of the month</Label>
            <Input
              id="tx-day"
              type="number"
              min={1}
              max={31}
              value={recurringDay}
              onChange={(e) => setRecurringDay(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Will be created automatically each month on this day.
            </p>
          </div>
        )}

        <Button
          type="submit"
          className="w-full"
          disabled={
            mutation.isPending ||
            (needsAccount && !hasAccounts) ||
            (isSavingsKind && (savings.data ?? []).length === 0) ||
            (kind === 'gasto_tc' && (creditCards.data ?? []).length === 0)
          }
        >
          {mutation.isPending ? 'Saving…' : 'Save'}
        </Button>
      </form>

      <SavingsFormDialog
        open={savingsFormOpen}
        onOpenChange={setSavingsFormOpen}
        item={null}
        onCreated={(id) => setSavingsId(String(id))}
      />
    </>
  )
}

const KIND_BADGES: Record<TransactionKind, { label: string; className: string }> = {
  ingreso: { label: 'Income', className: 'bg-emerald-100 text-emerald-700' },
  gasto: { label: 'Expense', className: 'bg-rose-100 text-rose-700' },
  transferencia: { label: 'Transfer', className: 'bg-blue-100 text-blue-700' },
  gasto_tc: { label: 'Card Expense', className: 'bg-orange-100 text-orange-700' },
  pago_tc: { label: 'Card Payment', className: 'bg-violet-100 text-violet-700' },
  ahorro: { label: 'Saving', className: 'bg-amber-100 text-amber-700' },
  retiro: { label: 'Withdrawal', className: 'bg-teal-100 text-teal-700' },
}

const amountClass = (tx: Transaction) =>
  tx.kind === 'ingreso'
    ? 'text-emerald-600'
    : tx.kind === 'transferencia'
      ? 'text-blue-600'
      : 'text-red-600'

const KIND_LABELS: Record<TransactionKind, string> = {
  ingreso: 'Income',
  gasto: 'Expense',
  transferencia: 'Transfer',
  gasto_tc: 'Card Expense',
  pago_tc: 'Card Payment',
  ahorro: 'Saving',
  retiro: 'Withdrawal',
}

const KIND_FILTERS: { value: TransactionKind | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'ingreso', label: KIND_LABELS.ingreso },
  { value: 'gasto', label: KIND_LABELS.gasto },
  { value: 'transferencia', label: KIND_LABELS.transferencia },
  { value: 'gasto_tc', label: KIND_LABELS.gasto_tc },
  { value: 'pago_tc', label: KIND_LABELS.pago_tc },
  { value: 'ahorro', label: KIND_LABELS.ahorro },
  { value: 'retiro', label: KIND_LABELS.retiro },
]

function TransactionsTable({
  rows,
  emptyMessage,
  onEdit,
  onDelete,
}: {
  rows: Transaction[]
  emptyMessage: string
  onEdit: (tx: Transaction) => void
  onDelete: (tx: Transaction) => void
}) {
  return (
    <div className="rounded-2xl border border-border bg-card shadow-[0_4px_0_0_rgba(0,0,0,0.05)]">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Date</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Details</TableHead>
            <TableHead className="text-right">Amount</TableHead>
            <TableHead className="w-24" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="py-10 text-center text-muted-foreground">
                {emptyMessage}
              </TableCell>
            </TableRow>
          )}
          {rows.map((tx) => (
            <TableRow key={tx.id}>
              <TableCell className="whitespace-nowrap">
                {new Date(`${tx.date}T00:00:00`).toLocaleDateString('es-CO', {
                  day: '2-digit',
                  month: 'short',
                })}
                {(tx.is_recurring || tx.generated_from) && (
                  <Badge variant="outline" className="ml-2">
                    recurring
                  </Badge>
                )}
              </TableCell>
              <TableCell>
                <Badge className={KIND_BADGES[tx.kind]?.className ?? ''}>
                  {KIND_BADGES[tx.kind]?.label ?? tx.kind}
                </Badge>
                {tx.kind !== 'transferencia' && (
                  <span className="ml-2">
                    <span
                      className="inline-block size-2.5 rounded-full align-middle"
                      style={{ backgroundColor: tx.color || '#888' }}
                    />
                    <span className="ml-1.5">
                      {tx.icon} {tx.category_name}
                    </span>
                  </span>
                )}
              </TableCell>
              <TableCell className="max-w-64 truncate">
                <div className="truncate">{tx.description || '—'}</div>
                <div className="mt-0.5 truncate text-xs font-bold text-muted-foreground">
                  {tx.kind === 'transferencia'
                    ? `${tx.account_icon} ${tx.account_name ?? '—'} → ${tx.to_account_icon} ${tx.to_account_name ?? '—'}`
                    : tx.kind === 'gasto_tc'
                      ? `💳 ${tx.card_name ?? 'Credit card'}`
                      : tx.kind === 'pago_tc'
                        ? `${tx.account_icon} ${tx.account_name ?? '—'} → 💳 ${tx.card_name ?? 'Card'}`
                        : tx.kind === 'ahorro' || tx.kind === 'retiro'
                          ? `${tx.account_icon} ${tx.account_name ?? '—'} ⇄ 👝 ${tx.savings_name ?? 'Savings'}`
                          : tx.account_name
                            ? `${tx.account_icon} ${tx.account_name}`
                            : '—'}
                  {tx.subcategory_name && ` · ${tx.subcategory_name}`}
                </div>
              </TableCell>
              <TableCell className={`text-right font-bold ${amountClass(tx)}`}>
                {tx.kind === 'ingreso' ? '+' : tx.kind === 'transferencia' ? '⇄' : '−'}
                {fmtCopDecimals(tx.amount)}
              </TableCell>
              <TableCell>
                <div className="flex justify-end gap-1">
                  <Button variant="ghost" size="icon" onClick={() => onEdit(tx)}>
                    <Pencil />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => onDelete(tx)}>
                    <Trash2 className="text-red-500" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

export function TransactionsPage() {
  const { month } = useMonth()
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  // ?new=1 (from the dashboard button) opens the create form directly.
  const [formOpen, setFormOpen] = useState(() => searchParams.get('new') === '1')
  const [editing, setEditing] = useState<Transaction | null>(null)
  const [deleting, setDeleting] = useState<Transaction | null>(null)
  const [kindFilter, setKindFilter] = useState<TransactionKind | 'all'>('all')

  const handleFormOpenChange = (open: boolean) => {
    setFormOpen(open)
    if (!open && searchParams.get('new') === '1') {
      searchParams.delete('new')
      setSearchParams(searchParams, { replace: true })
    }
  }

  // The floating "new transaction" button links here with ?new=1;
  // open the form even when we are already on this page.
  useEffect(() => {
    if (searchParams.get('new') === '1') setFormOpen(true)
  }, [searchParams])

  const transactions = useQuery({
    queryKey: ['transactions', month],
    queryFn: () => api.listTransactions(month.month, month.year),
  })

  useEffect(() => {
    let cancelled = false
    api
      .materializeRecurring(month.month, month.year)
      .then((result) => {
        if (!cancelled && result.created > 0) {
          void queryClient.invalidateQueries({ queryKey: ['transactions', month] })
        }
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [month, queryClient])

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteTransaction(id),
    onSuccess: () => {
      toast.success('Transaction deleted')
      setDeleting(null)
      void queryClient.invalidateQueries({ queryKey: ['transactions', month] })
      void queryClient.invalidateQueries({ queryKey: ['summary', month] })
      void queryClient.invalidateQueries({ queryKey: ['accounts'] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const openCreate = () => {
    setEditing(null)
    setFormOpen(true)
  }
  const openEdit = (transaction: Transaction) => {
    setEditing(transaction)
    setFormOpen(true)
  }

  const allTransactions = transactions.data ?? []
  const accountTransactions = allTransactions.filter((tx) => tx.kind !== 'gasto_tc')
  const cardTransactions = allTransactions.filter((tx) => tx.kind === 'gasto_tc')
  const filteredTransactions =
    kindFilter === 'all'
      ? allTransactions
      : allTransactions.filter((tx) => tx.kind === kindFilter)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-extrabold">Transactions</h1>
          <p className="text-sm font-semibold text-muted-foreground">
            All transactions for the month
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus /> New transaction
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        {KIND_FILTERS.map(({ value, label }) => {
          const active = kindFilter === value
          const count =
            value === 'all'
              ? allTransactions.length
              : allTransactions.filter((tx) => tx.kind === value).length
          return (
            <button
              key={value}
              type="button"
              onClick={() => setKindFilter(value)}
              className={`rounded-xl border px-3 py-1.5 text-xs font-bold transition-colors ${
                active
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-border bg-background text-muted-foreground hover:bg-muted'
              }`}
            >
              {label}
              <span className={`ml-1.5 ${active ? 'opacity-80' : 'opacity-60'}`}>{count}</span>
            </button>
          )
        })}
      </div>

      {kindFilter === 'all' ? (
        <>
          <section className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Wallet className="size-4 text-primary" />
              <h2 className="text-base font-extrabold">Accounts</h2>
              <Badge variant="secondary">{accountTransactions.length}</Badge>
              <span className="text-xs font-semibold text-muted-foreground">
                Income, expenses, transfers, savings and card payments
              </span>
            </div>
            <TransactionsTable
              rows={accountTransactions}
              emptyMessage="No account transactions this month."
              onEdit={openEdit}
              onDelete={setDeleting}
            />
          </section>

          <section className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <CreditCard className="size-4 text-orange-500" />
              <h2 className="text-base font-extrabold">Credit Cards</h2>
              <Badge variant="secondary">{cardTransactions.length}</Badge>
              <span className="text-xs font-semibold text-muted-foreground">
                Card purchases (not deducted from your accounts until you pay them)
              </span>
            </div>
            <TransactionsTable
              rows={cardTransactions}
              emptyMessage="No card purchases this month."
              onEdit={openEdit}
              onDelete={setDeleting}
            />
          </section>
        </>
      ) : (
        <section className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-base font-extrabold">{KIND_LABELS[kindFilter]}</h2>
            <Badge variant="secondary">{filteredTransactions.length}</Badge>
            <span className="text-xs font-semibold text-muted-foreground">
              Transactions of type {KIND_LABELS[kindFilter].toLowerCase()}
            </span>
          </div>
          <TransactionsTable
            rows={filteredTransactions}
            emptyMessage={`No transactions of type ${KIND_LABELS[kindFilter].toLowerCase()} this month.`}
            onEdit={openEdit}
            onDelete={setDeleting}
          />
        </section>
      )}

      <TransactionForm
        open={formOpen}
        onOpenChange={handleFormOpenChange}
        transaction={editing}
      />

      <AlertDialog open={!!deleting} onOpenChange={(open) => !open && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete transaction?</AlertDialogTitle>
            <AlertDialogDescription>
              This will delete &quot;{deleting?.description || 'this transaction'}&quot; for{' '}
              {deleting ? fmtCopDecimals(deleting.amount) : ''}. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleting && deleteMutation.mutate(deleting.id)}
              className="bg-red-600 hover:bg-red-700"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
