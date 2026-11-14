import { useMutation } from '@tanstack/react-query'
import { Landmark, Pencil, Plus, Trash2, Wallet } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { SectionCard } from '@/components/SectionCard'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { api } from '@/lib/api'
import { todayISO } from '@/lib/dates'
import { fmtMoney, normalizeAmount } from '@/lib/money'
import { useAccounts, useCategories, useInvalidate, useLoans } from '@/lib/queries'
import type { Loan } from '@/lib/types'

const fmtMonth = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('es-CO', { month: 'long', year: 'numeric' })

/** Paid share since the last confirmed bank balance (interest included in the balance). */
function progressOf(loan: Loan): number {
  const start = Number(loan.balance)
  if (start <= 0) return 100
  return Math.max(0, Math.min(100, (1 - Number(loan.current_balance) / start) * 100))
}

function LoanForm({
  loan,
  open,
  onOpenChange,
}: {
  loan: Loan | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const invalidate = useInvalidate()
  const categories = useCategories()
  const expense = (categories.data ?? []).filter((c) => c.type === 'expense' && c.role !== 'savings')
  const defaultCategory = expense.find((c) => /cr[eé]dito/i.test(c.name))

  const [name, setName] = useState(loan?.name ?? '')
  const [balance, setBalance] = useState(loan ? String(Number(loan.current_balance)) : '')
  const [asOf, setAsOf] = useState(todayISO())
  const [installment, setInstallment] = useState(loan ? String(Number(loan.installment)) : '')
  const [rate, setRate] = useState(loan?.rate_bp != null ? String(loan.rate_bp / 100) : '')
  const [paymentDay, setPaymentDay] = useState(loan?.payment_day ? String(loan.payment_day) : '')
  const [categoryId, setCategoryId] = useState(
    loan?.category_id ? String(loan.category_id) : defaultCategory ? String(defaultCategory.id) : '',
  )

  const mutation = useMutation({
    mutationFn: async (): Promise<void> => {
      const payload = {
        name: name.trim(),
        balance: normalizeAmount(balance),
        as_of: asOf,
        installment: normalizeAmount(installment),
        rate_bp: rate.trim() ? Math.round(Number(rate.replace(',', '.')) * 100) : null,
        payment_day: paymentDay ? Number(paymentDay) : null,
        category_id: categoryId ? Number(categoryId) : null,
      }
      if (loan) await api.updateLoan(loan.id, payload)
      else await api.createLoan(payload)
    },
    onSuccess: () => {
      toast.success(loan ? 'Crédito actualizado' : 'Crédito registrado')
      onOpenChange(false)
      void invalidate('loan')
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{loan ? 'Editar crédito' : 'Nuevo crédito'}</DialogTitle>
          <DialogDescription>
            Usa el saldo que te muestra el banco. Si lo cambias más adelante, la proyección se
            recalcula desde esa fecha.
          </DialogDescription>
        </DialogHeader>
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault()
            mutation.mutate()
          }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="loan-name">Nombre</Label>
            <Input
              id="loan-name"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ej. Libre inversión Davivienda"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="loan-balance">Saldo pendiente</Label>
              <Input
                id="loan-balance"
                required
                value={balance}
                onChange={(e) => setBalance(e.target.value)}
                placeholder="8.900.000"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="loan-asof">Saldo al</Label>
              <Input
                id="loan-asof"
                type="date"
                required
                value={asOf}
                onChange={(e) => setAsOf(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="loan-installment">Cuota mensual</Label>
              <Input
                id="loan-installment"
                required
                value={installment}
                onChange={(e) => setInstallment(e.target.value)}
                placeholder="300.000"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="loan-rate">Tasa (% EA, opcional)</Label>
              <Input
                id="loan-rate"
                inputMode="decimal"
                value={rate}
                onChange={(e) => setRate(e.target.value)}
                placeholder="Ej. 24"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="loan-day">Día de pago</Label>
              <Input
                id="loan-day"
                type="number"
                min={1}
                max={31}
                value={paymentDay}
                onChange={(e) => setPaymentDay(e.target.value)}
                placeholder="Ej. 5"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Categoría del pago</Label>
              <Select value={categoryId} onValueChange={(v) => setCategoryId(v ?? '')}>
                <SelectTrigger>
                  <SelectValue placeholder="Categoría" />
                </SelectTrigger>
                <SelectContent>
                  {expense.map((c) => (
                    <SelectItem key={c.id} value={String(c.id)}>
                      {c.icon} {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          {!rate.trim() && (
            <p className="text-xs text-muted-foreground">
              Sin tasa, el saldo se estima como saldo − pagos (sin intereses). Agrégala cuando la
              tengas para una proyección exacta.
            </p>
          )}
          <Button type="submit" className="w-full" disabled={mutation.isPending}>
            {mutation.isPending ? 'Guardando…' : 'Guardar'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function PayDialog({ loan, onClose }: { loan: Loan; onClose: () => void }) {
  const invalidate = useInvalidate()
  const accounts = useAccounts()
  const [accountId, setAccountId] = useState('')
  const [amount, setAmount] = useState(String(Number(loan.installment)))
  const [date, setDate] = useState(todayISO())
  const [recurring, setRecurring] = useState(false)
  const extra = Number(normalizeAmount(amount)) > Number(loan.installment)

  const mutation = useMutation({
    mutationFn: () =>
      api.createTransaction({
        date,
        amount: normalizeAmount(amount),
        kind: 'gasto',
        category_id: loan.category_id,
        account_id: Number(accountId),
        to_account_id: null,
        loan_id: loan.id,
        description: extra ? `Cuota + abono ${loan.name}` : `Cuota ${loan.name}`,
        is_recurring: recurring,
        recurring_day: recurring ? (loan.payment_day ?? Number(date.slice(8, 10))) : null,
      }),
    onSuccess: () => {
      toast.success('Pago registrado')
      onClose()
      void invalidate('movement')
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Pagar {loan.name}</DialogTitle>
          <DialogDescription>
            Saldo hoy {fmtMoney(loan.current_balance)}. Lo que pagues de más de la cuota es un abono
            a capital: pide al banco reducir el plazo.
          </DialogDescription>
        </DialogHeader>
        {loan.category_id == null && (
          <p className="rounded-lg border border-dashed border-border bg-muted/40 px-3 py-2 text-sm text-muted-foreground">
            Este crédito no tiene categoría: edítalo y elige una para registrar el pago.
          </p>
        )}
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault()
            if (!accountId) {
              toast.error('Selecciona la cuenta desde la que pagas')
              return
            }
            mutation.mutate()
          }}
        >
          <div className="space-y-1.5">
            <Label>Pagar desde</Label>
            <Select value={accountId} onValueChange={(v) => setAccountId(v ?? '')}>
              <SelectTrigger>
                <SelectValue placeholder="Selecciona la cuenta" />
              </SelectTrigger>
              <SelectContent>
                {(accounts.data ?? []).map((a) => (
                  <SelectItem key={a.id} value={String(a.id)}>
                    {a.name} ({fmtMoney(a.balance)})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="pay-loan-amount">Monto</Label>
              <Input
                id="pay-loan-amount"
                required
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="pay-loan-date">Fecha</Label>
              <Input
                id="pay-loan-date"
                type="date"
                required
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
          </div>
          {extra && (
            <p className="text-xs text-muted-foreground">
              Abono extra de {fmtMoney(Number(normalizeAmount(amount)) - Number(loan.installment))}{' '}
              sobre la cuota.
            </p>
          )}
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={recurring}
              onChange={(e) => setRecurring(e.target.checked)}
            />
            Repetir cada mes (cuota recurrente)
          </label>
          <Button
            type="submit"
            className="w-full"
            disabled={mutation.isPending || loan.category_id == null}
          >
            {mutation.isPending ? 'Registrando…' : `Pagar ${fmtMoney(normalizeAmount(amount) || '0')}`}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function LoansSection() {
  const invalidate = useInvalidate()
  const loans = useLoans()
  const [editing, setEditing] = useState<Loan | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [paying, setPaying] = useState<Loan | null>(null)
  const total = (loans.data ?? []).reduce((sum, l) => sum + Number(l.current_balance), 0)

  const remove = useMutation({
    mutationFn: (id: number) => api.deleteLoan(id),
    onSuccess: () => {
      toast.success('Crédito eliminado')
      void invalidate('loan')
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return (
    <SectionCard
      icon={Landmark}
      title="Créditos"
      subtitle={(loans.data ?? []).length > 0 ? `Debes ${fmtMoney(total)}` : 'Préstamos fuera de tarjetas'}
      action={
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            setEditing(null)
            setFormOpen(true)
          }}
        >
          <Plus /> Nuevo crédito
        </Button>
      }
    >
      {(loans.data ?? []).length === 0 ? (
        <p className="py-6 text-center text-sm text-muted-foreground">
          Sin créditos registrados.
        </p>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {(loans.data ?? []).map((loan) => {
            const left = loan.remaining_installments
            return (
              <Card key={loan.id} className="gap-3 p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate font-medium">{loan.name}</p>
                    <p className="text-xs text-muted-foreground">
                      Cuota {fmtMoney(loan.installment)}
                      {loan.payment_day ? ` · día ${loan.payment_day}` : ''}
                      {loan.rate_bp != null ? ` · ${loan.rate_bp / 100}% EA` : ' · sin tasa'}
                    </p>
                  </div>
                  <div className="flex gap-0.5">
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      aria-label={`Editar crédito ${loan.name}`}
                      onClick={() => {
                        setEditing(loan)
                        setFormOpen(true)
                      }}
                    >
                      <Pencil className="size-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      aria-label={`Eliminar crédito ${loan.name}`}
                      onClick={() => remove.mutate(loan.id)}
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                </div>
                <div>
                  <p className="text-2xl font-semibold tracking-tight">
                    {fmtMoney(loan.current_balance)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    saldo hoy{loan.rate_bp == null ? ' (estimado, sin intereses)' : ''}
                  </p>
                </div>
                <Progress value={progressOf(loan)} />
                <div className="flex flex-wrap justify-between gap-2 text-xs text-muted-foreground">
                  <span>Pagado {fmtMoney(loan.paid)}</span>
                  <span>
                    {left == null
                      ? 'La cuota no alcanza a cubrir los intereses'
                      : left === 0
                        ? 'Pagado'
                        : `${left} cuotas · termina ${loan.payoff ? fmtMonth(loan.payoff) : ''}`}
                  </span>
                </div>
                <Button size="sm" onClick={() => setPaying(loan)} className="self-start">
                  <Wallet /> Pagar
                </Button>
              </Card>
            )
          })}
        </div>
      )}
      {formOpen && (
        <LoanForm
          key={editing?.id ?? 'new'}
          loan={editing}
          open={formOpen}
          onOpenChange={setFormOpen}
        />
      )}
      {paying && <PayDialog loan={paying} onClose={() => setPaying(null)} />}
    </SectionCard>
  )
}
