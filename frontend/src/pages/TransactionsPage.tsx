import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Pencil, Plus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
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
import type { Transaction, TransactionInput } from '@/lib/types'

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

  const [date, setDate] = useState(
    transaction?.date ?? `${month.year}-${String(month.month).padStart(2, '0')}-15`,
  )
  const [amount, setAmount] = useState(transaction?.amount ?? '')
  const [categoryId, setCategoryId] = useState(transaction ? String(transaction.category_id) : '')
  const [subcategoryId, setSubcategoryId] = useState(
    transaction?.subcategory_id ? String(transaction.subcategory_id) : 'none',
  )
  const [description, setDescription] = useState(transaction?.description ?? '')
  const [isRecurring, setIsRecurring] = useState(transaction?.is_recurring ?? false)
  const [recurringDay, setRecurringDay] = useState(String(transaction?.recurring_day ?? 1))

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
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    if (!categoryId) {
      toast.error('Selecciona una categoría')
      return
    }
    mutation.mutate({
      date,
      amount: normalizeAmount(amount),
      category_id: Number(categoryId),
      subcategory_id: subcategoryId === 'none' ? null : Number(subcategoryId),
      description,
      is_recurring: isRecurring,
      recurring_day: isRecurring ? Number(recurringDay) : null,
    })
  }

  const selectedCategory = categories.data?.find((c) => String(c.id) === categoryId)
  const filteredSubcategories = subcategories.data ?? []
  // Guard against a stale selection pointing at a subcategory that no
  // longer belongs to the selected category (e.g. after switching).
  const subValue = filteredSubcategories.some((s) => String(s.id) === subcategoryId)
    ? subcategoryId
    : 'none'

  return (
    <>
      <DialogHeader>
        <DialogTitle>{transaction ? 'Editar transacción' : 'Nueva transacción'}</DialogTitle>
        <DialogDescription>
          {transaction ? 'Modifica los datos y guarda.' : 'Registra un movimiento del mes.'}
        </DialogDescription>
      </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
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

          <div className="space-y-1.5">
            <Label>Categoría</Label>
            <Select
              value={categoryId}
              onValueChange={(v) => {
                setCategoryId(v ?? '')
                setSubcategoryId('none')
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Selecciona una categoría" />
              </SelectTrigger>
              <SelectContent>
                {(categories.data ?? []).map((cat) => (
                  <SelectItem key={cat.id} value={String(cat.id)}>
                    {cat.icon} {cat.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {selectedCategory && (
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
            <Label htmlFor="tx-recurring">Es recurrente (arriendo, servicios…)</Label>
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

        <Button type="submit" className="w-full" disabled={mutation.isPending}>
          {mutation.isPending ? 'Guardando…' : 'Guardar'}
        </Button>
      </form>
    </>
  )
}

export function TransactionsPage() {
  const { month } = useMonth()
  const queryClient = useQueryClient()
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Transaction | null>(null)
  const [deleting, setDeleting] = useState<Transaction | null>(null)

  const transactions = useQuery({
    queryKey: ['transactions', month],
    queryFn: () => api.listTransactions(month.month, month.year),
  })

  // Materialize recurring templates whenever the month changes.
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

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Transacciones</h1>
          <p className="text-sm text-muted-foreground">Todos los movimientos del mes</p>
        </div>
        <Button onClick={openCreate}>
          <Plus /> Nueva transacción
        </Button>
      </div>

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Fecha</TableHead>
              <TableHead>Categoría</TableHead>
              <TableHead>Descripción</TableHead>
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
                  <span
                    className="inline-block size-2.5 rounded-full align-middle"
                    style={{ backgroundColor: tx.color || '#888' }}
                  />
                  <span className="ml-2">
                    {tx.icon} {tx.category_name}
                  </span>
                  {tx.subcategory_name && (
                    <span className="ml-1 text-xs text-muted-foreground">
                      · {tx.subcategory_name}
                    </span>
                  )}
                </TableCell>
                <TableCell className="max-w-64 truncate">{tx.description || '—'}</TableCell>
                <TableCell
                  className={`text-right font-medium ${
                    tx.category_type === 'income' ? 'text-emerald-600' : 'text-red-600'
                  }`}
                >
                  {tx.category_type === 'income' ? '+' : '−'}
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

      <TransactionForm open={formOpen} onOpenChange={setFormOpen} transaction={editing} />

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
