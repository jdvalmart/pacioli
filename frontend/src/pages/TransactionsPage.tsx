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
    label: 'Ingreso',
    icon: ArrowDownLeft,
    activeClass: 'bg-emerald-500 border-emerald-700 text-white shadow-[0_4px_0_0_#047857]',
  },
  {
    value: 'gasto',
    label: 'Gasto',
    icon: ArrowUpRight,
    activeClass: 'bg-rose-500 border-rose-700 text-white shadow-[0_4px_0_0_#be123c]',
  },
  {
    value: 'transferencia',
    label: 'Transferencia',
    icon: ArrowLeftRight,
    activeClass: 'bg-blue-500 border-blue-700 text-white shadow-[0_4px_0_0_#1d4ed8]',
  },
  {
    value: 'gasto_tc',
    label: 'Gasto TC',
    icon: CreditCard,
    activeClass: 'bg-orange-500 border-orange-700 text-white shadow-[0_4px_0_0_#c2410c]',
  },
  {
    value: 'ahorro',
    label: 'Ahorro',
    icon: PiggyBank,
    activeClass: 'bg-amber-500 border-amber-700 text-white shadow-[0_4px_0_0_#b45309]',
  },
  {
    value: 'retiro',
    label: 'Retiro',
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
  const creditCards = useQuery({ queryKey: ['creditCards'], queryFn: api.listCreditCards })
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
      toast.success(transaction ? 'Transacción actualizada' : 'Transacción creada')
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
      toast.error('Selecciona una categoría')
      return
    }
    if (kind === 'gasto_tc' && !cardId) {
      toast.error('Selecciona la tarjeta de crédito')
      return
    }
    if (isSavingsKind && !savingsId) {
      toast.error('Selecciona el bolsillo o inversión')
      return
    }
    if (isSavingsKind && selectedSavingsLocked) {
      toast.error(`Este ahorro está bloqueado hasta el ${selectedSavings?.matures_on}`)
      return
    }
    if (needsAccount && !accountId) {
      toast.error('Selecciona una cuenta — todo movimiento sale o entra a una cuenta')
      return
    }
    if (needsTwoAccounts) {
      if (!accountId || !toAccountId) {
        toast.error('Selecciona la cuenta de origen y la de destino')
        return
      }
      if (accountId === toAccountId) {
        toast.error('La cuenta de origen y destino deben ser diferentes')
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
    kind === 'ingreso' ? 'Cuenta destino' : kind === 'gasto' ? 'Cuenta origen' : 'Cuenta'

  return (
    <>
      <DialogHeader>
        <DialogTitle>{transaction ? 'Editar transacción' : 'Nueva transacción'}</DialogTitle>
        <DialogDescription>
          {transaction ? 'Modifica los datos y guarda.' : 'Registra un movimiento del mes.'}
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
            <Label htmlFor="tx-date">Fecha</Label>
            <Input
              id="tx-date"
              type="date"
              required
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="tx-amount">Monto</Label>
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
              <Label>Desde</Label>
              <Select value={accountId} onValueChange={(v) => setAccountId(v ?? '')}>
                <SelectTrigger>
                  <SelectValue placeholder="Cuenta de origen" />
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
              <Label>Hacia</Label>
              <Select value={toAccountId} onValueChange={(v) => setToAccountId(v ?? '')}>
                <SelectTrigger>
                  <SelectValue placeholder="Cuenta de destino" />
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
                Mover dinero entre tus cuentas no afecta ingresos ni gastos.
              </p>
            </div>
          </>
        ) : isSavingsKind ? (
          <>
            <div className="space-y-1.5">
              <Label>{kind === 'ahorro' ? 'Bolsillo destino' : 'Bolsillo origen'}</Label>
              {(savings.data ?? []).length > 0 && (
                <Select value={savingsId} onValueChange={(v) => setSavingsId(v ?? '')}>
                  <SelectTrigger>
                    <SelectValue placeholder="Selecciona el bolsillo" />
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
                <Plus /> Crear bolsillo, CDT o acciones
              </Button>
              {selectedSavingsLocked && (
                <p className="text-xs font-bold text-amber-600">
                  🔒 Bloqueado hasta el {selectedSavings?.matures_on} — no puedes mover dinero hasta el vencimiento.
                </p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label>{kind === 'ahorro' ? 'Cuenta origen' : 'Cuenta destino'}</Label>
              {!hasAccounts ? (
                <div className="rounded-xl border border-dashed border-primary/50 bg-primary/10 p-3 text-sm font-semibold text-muted-foreground">
                  Aún no tienes cuentas. Crea una en el Dashboard.
                </div>
              ) : (
                <Select value={accountId} onValueChange={(v) => setAccountId(v ?? '')}>
                  <SelectTrigger>
                    <SelectValue placeholder="Selecciona una cuenta" />
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
                    ? 'Se asigna al bolsillo: el dinero sigue en tu cuenta, solo queda apartado.'
                    : 'El dinero sale de tu cuenta hacia el ahorro (no cuenta como gasto).'
                  : savingsIsBolsillo
                    ? 'Se libera del bolsillo: el dinero sigue en tu cuenta.'
                    : 'El dinero vuelve a tu cuenta.'}
              </p>
            </div>
          </>
        ) : (
          <>
            <div className="space-y-1.5">
              <Label>Categoría</Label>
              <Select value={categoryId} onValueChange={(v) => setCategoryId(v ?? '')}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona una categoría" />
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
                <Label>Subcategoría (opcional)</Label>
                <Select value={subValue} onValueChange={(v) => setSubcategoryId(v ?? 'none')}>
                  <SelectTrigger>
                    <SelectValue placeholder="Sin subcategoría" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Sin subcategoría</SelectItem>
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
                <Label>Tarjeta de crédito</Label>
                {(creditCards.data ?? []).length === 0 ? (
                  <div className="rounded-xl border border-dashed border-orange-400/60 bg-orange-500/10 p-3 text-sm font-semibold text-muted-foreground">
                    💳 Aún no tienes tarjetas. Crea una en el Dashboard (sección Tarjetas
                    de crédito) para registrar gastos TC.
                  </div>
                ) : (
                  <>
                    <Select value={cardId} onValueChange={(v) => setCardId(v ?? '')}>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecciona la tarjeta" />
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
                      Se descuenta del cupo disponible de la tarjeta.
                    </p>
                    <div className="grid grid-cols-2 gap-3 pt-1">
                      <div className="space-y-1.5">
                        <Label htmlFor="tx-installments">Cuotas</Label>
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
                          <Label htmlFor="tx-interest">Interés total (%)</Label>
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
                        ? `Cuota: ${fmtCopDecimals(
                            (Number(normalizeAmount(amount || '0')) *
                              (1 + Number(interest || '0') / 100)) /
                              (Number(installments) || 1),
                          )} por mes`
                        : 'A 1 cuota no se cobra interés.'}
                    </p>
                  </>
                )}
              </div>
            ) : (
              <div className="space-y-1.5">
                <Label>{accountLabel}</Label>
                {!hasAccounts ? (
                  <div className="rounded-xl border border-dashed border-primary/50 bg-primary/10 p-3 text-sm font-semibold text-muted-foreground">
                    Aún no tienes cuentas. Crea una en el Dashboard (billetera, banco,
                    ahorros…) para poder registrar movimientos.
                  </div>
                ) : (
                  <>
                    <Select value={accountId} onValueChange={(v) => setAccountId(v ?? '')}>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecciona una cuenta" />
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
                        ? 'A qué cuenta entra el dinero.'
                        : 'De qué cuenta sale el dinero.'}
                    </p>
                  </>
                )}
              </div>
            )}
          </>
        )}

        <div className="space-y-1.5">
          <Label htmlFor="tx-description">Descripción</Label>
          <Input
            id="tx-description"
            placeholder="Ej. Mercado semanal"
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
          <Label htmlFor="tx-recurring">Es recurrente (arriendo, servicios, ahorro…)</Label>
        </div>
        {isRecurring && (
          <div className="space-y-1.5">
            <Label htmlFor="tx-day">Día del mes</Label>
            <Input
              id="tx-day"
              type="number"
              min={1}
              max={31}
              value={recurringDay}
              onChange={(e) => setRecurringDay(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Se creará automáticamente cada mes en este día.
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
          {mutation.isPending ? 'Guardando…' : 'Guardar'}
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
  ingreso: { label: 'Ingreso', className: 'bg-emerald-100 text-emerald-700' },
  gasto: { label: 'Gasto', className: 'bg-rose-100 text-rose-700' },
  transferencia: { label: 'Transferencia', className: 'bg-blue-100 text-blue-700' },
  gasto_tc: { label: 'Gasto TC', className: 'bg-orange-100 text-orange-700' },
  pago_tc: { label: 'Pago TC', className: 'bg-violet-100 text-violet-700' },
  ahorro: { label: 'Ahorro', className: 'bg-amber-100 text-amber-700' },
  retiro: { label: 'Retiro', className: 'bg-teal-100 text-teal-700' },
}

const amountClass = (tx: Transaction) =>
  tx.kind === 'ingreso'
    ? 'text-emerald-600'
    : tx.kind === 'transferencia'
      ? 'text-blue-600'
      : 'text-red-600'

const KIND_LABELS: Record<TransactionKind, string> = {
  ingreso: 'Ingreso',
  gasto: 'Gasto',
  transferencia: 'Transferencia',
  gasto_tc: 'Gasto TC',
  pago_tc: 'Pago TC',
  ahorro: 'Ahorro',
  retiro: 'Retiro',
}

const KIND_FILTERS: { value: TransactionKind | 'all'; label: string }[] = [
  { value: 'all', label: 'Todos' },
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
            <TableHead>Fecha</TableHead>
            <TableHead>Movimiento</TableHead>
            <TableHead>Detalle</TableHead>
            <TableHead className="text-right">Monto</TableHead>
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
                    recurrente
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
                      ? `💳 ${tx.card_name ?? 'Tarjeta de crédito'}`
                      : tx.kind === 'pago_tc'
                        ? `${tx.account_icon} ${tx.account_name ?? '—'} → 💳 ${tx.card_name ?? 'TC'}`
                        : tx.kind === 'ahorro' || tx.kind === 'retiro'
                          ? `${tx.account_icon} ${tx.account_name ?? '—'} ⇄ 👝 ${tx.savings_name ?? 'Ahorro'}`
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
      toast.success('Transacción eliminada')
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
          <h1 className="text-xl font-extrabold">Transacciones</h1>
          <p className="text-sm font-semibold text-muted-foreground">
            Todos los movimientos del mes
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus /> Nueva transacción
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
              <h2 className="text-base font-extrabold">Cuentas</h2>
              <Badge variant="secondary">{accountTransactions.length}</Badge>
              <span className="text-xs font-semibold text-muted-foreground">
                Ingresos, gastos, transferencias, ahorros y pagos TC
              </span>
            </div>
            <TransactionsTable
              rows={accountTransactions}
              emptyMessage="No hay movimientos de cuentas este mes."
              onEdit={openEdit}
              onDelete={setDeleting}
            />
          </section>

          <section className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <CreditCard className="size-4 text-orange-500" />
              <h2 className="text-base font-extrabold">Tarjetas de crédito</h2>
              <Badge variant="secondary">{cardTransactions.length}</Badge>
              <span className="text-xs font-semibold text-muted-foreground">
                Compras con tarjeta (no descuentan de tus cuentas hasta que las pagues)
              </span>
            </div>
            <TransactionsTable
              rows={cardTransactions}
              emptyMessage="No hay compras con tarjeta este mes."
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
              Movimientos de tipo {KIND_LABELS[kindFilter].toLowerCase()}
            </span>
          </div>
          <TransactionsTable
            rows={filteredTransactions}
            emptyMessage={`No hay movimientos de tipo ${KIND_LABELS[kindFilter].toLowerCase()} este mes.`}
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
            <AlertDialogTitle>¿Eliminar transacción?</AlertDialogTitle>
            <AlertDialogDescription>
              Se eliminará &quot;{deleting?.description || 'esta transacción'}&quot; de{' '}
              {deleting ? fmtCopDecimals(deleting.amount) : ''}. Esta acción no se puede deshacer.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleting && deleteMutation.mutate(deleting.id)}
              className="bg-red-600 hover:bg-red-700"
            >
              Eliminar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
