import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import {
  ArrowDownLeft,
  ArrowLeftRight,
  ArrowUpRight,
  CreditCard,
  Pencil,
  Plus,
  Trash2,
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
  const [description, setDescription] = useState(transaction?.description ?? '')
  const [isRecurring, setIsRecurring] = useState(transaction?.is_recurring ?? false)
  const [recurringDay, setRecurringDay] = useState(String(transaction?.recurring_day ?? 1))

  const incomeCategories = (categories.data ?? []).filter((c) => c.type === 'income')
  const expenseCategories = (categories.data ?? []).filter((c) => c.type === 'expense')
  const visibleCategories = kind === 'ingreso' ? incomeCategories : expenseCategories

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

  const needsAccount = kind === 'ingreso' || kind === 'gasto'
  const needsTwoAccounts = kind === 'transferencia'

  const handleKindChange = (next: TransactionKind) => {
    setKind(next)
    setCategoryId('')
    setSubcategoryId('none')
  }

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    if (kind !== 'transferencia' && !categoryId) {
      toast.error('Selecciona una categoría')
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
      category_id: kind === 'transferencia' ? null : Number(categoryId),
      subcategory_id: kind === 'transferencia' || subcategoryId === 'none' ? null : Number(subcategoryId),
      account_id: kind === 'gasto_tc' ? null : Number(accountId),
      to_account_id: kind === 'transferencia' ? Number(toAccountId) : null,
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
        <div className="grid grid-cols-4 gap-2">
          {KIND_OPTIONS.map(({ value, label, icon: Icon, activeClass }) => (
            <button
              key={value}
              type="button"
              onClick={() => handleKindChange(value)}
              className={`flex flex-col items-center gap-1 rounded-xl border-2 px-2 py-2.5 text-xs font-bold transition-all ${
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
              <div className="rounded-xl border-2 border-dashed border-orange-400/60 bg-orange-500/10 p-3 text-sm font-semibold text-muted-foreground">
                💳 Se registrará como deuda de la tarjeta de crédito (próxima funcionalidad).
                No afecta tus cuentas de efectivo.
              </div>
            ) : (
              <div className="space-y-1.5">
                <Label>{accountLabel}</Label>
                {!hasAccounts ? (
                  <div className="rounded-xl border-2 border-dashed border-primary/50 bg-primary/10 p-3 text-sm font-semibold text-muted-foreground">
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
          disabled={mutation.isPending || (needsAccount && !hasAccounts)}
        >
          {mutation.isPending ? 'Guardando…' : 'Guardar'}
        </Button>
      </form>
    </>
  )
}

const KIND_BADGES: Record<TransactionKind, { label: string; className: string }> = {
  ingreso: { label: 'Ingreso', className: 'bg-emerald-100 text-emerald-700' },
  gasto: { label: 'Gasto', className: 'bg-rose-100 text-rose-700' },
  transferencia: { label: 'Transferencia', className: 'bg-blue-100 text-blue-700' },
  gasto_tc: { label: 'Gasto TC', className: 'bg-orange-100 text-orange-700' },
}

export function TransactionsPage() {
  const { month } = useMonth()
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  // ?new=1 (from the dashboard button) opens the create form directly.
  const [formOpen, setFormOpen] = useState(() => searchParams.get('new') === '1')
  const [editing, setEditing] = useState<Transaction | null>(null)
  const [deleting, setDeleting] = useState<Transaction | null>(null)

  const handleFormOpenChange = (open: boolean) => {
    setFormOpen(open)
    if (!open && searchParams.get('new') === '1') {
      searchParams.delete('new')
      setSearchParams(searchParams, { replace: true })
    }
  }

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

  const amountClass = (tx: Transaction) =>
    tx.kind === 'ingreso'
      ? 'text-emerald-600'
      : tx.kind === 'transferencia'
        ? 'text-blue-600'
        : 'text-red-600'

  return (
    <div className="space-y-4">
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

      <div className="rounded-2xl border-2 border-border bg-card shadow-[0_4px_0_0_rgba(0,0,0,0.05)]">
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
            {transactions.data?.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="py-10 text-center text-muted-foreground">
                  No hay transacciones este mes. Crea la primera con el botón de arriba.
                </TableCell>
              </TableRow>
            )}
            {transactions.data?.map((tx) => (
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
                      : tx.account_name
                        ? `${tx.account_icon} ${tx.account_name}`
                        : 'Tarjeta de crédito'}
                    {tx.subcategory_name && ` · ${tx.subcategory_name}`}
                  </div>
                </TableCell>
                <TableCell className={`text-right font-bold ${amountClass(tx)}`}>
                  {tx.kind === 'ingreso' ? '+' : tx.kind === 'transferencia' ? '⇄' : '−'}
                  {fmtCopDecimals(tx.amount)}
                </TableCell>
                <TableCell>
                  <div className="flex justify-end gap-1">
                    <Button variant="ghost" size="icon" onClick={() => openEdit(tx)}>
                      <Pencil />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => setDeleting(tx)}>
                      <Trash2 className="text-red-500" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

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
