import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { CreditCard as CreditCardIcon, Pencil, Plus, Trash2, Wallet } from 'lucide-react'
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
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
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
import { Skeleton } from '@/components/ui/skeleton'
import { useMonth } from '@/hooks/useMonth'
import { api } from '@/lib/api'
import { SectionCard } from '@/components/SectionCard'
import { fmtCopDecimals, normalizeAmount } from '@/lib/money'
import type { Account, CreditCard } from '@/lib/types'

const MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function fmtDay(iso: string): string {
  const [, month, day] = iso.split('-').map(Number)
  return `${day} ${MONTHS_SHORT[month - 1]}`
}

function addOneDay(iso: string): string {
  const d = new Date(`${iso}T00:00:00`)
  d.setDate(d.getDate() + 1)
  return d.toISOString().slice(0, 10)
}

function CardForm({
  open,
  onOpenChange,
  card,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  card: CreditCard | null
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {open && <CardFormBody card={card} onOpenChange={onOpenChange} />}
      </DialogContent>
    </Dialog>
  )
}

function CardFormBody({
  card,
  onOpenChange,
}: {
  card: CreditCard | null
  onOpenChange: (open: boolean) => void
}) {
  const queryClient = useQueryClient()
  const [name, setName] = useState(card?.name ?? '')
  const [limit, setLimit] = useState(card?.limit ?? '')
  const [cutoffDay, setCutoffDay] = useState(String(card?.cutoff_day ?? 15))
  const [paymentDay, setPaymentDay] = useState(String(card?.payment_day ?? 30))

  const mutation = useMutation({
    mutationFn: async () => {
      const payload = {
        name,
        limit: normalizeAmount(limit),
        cutoff_day: Number(cutoffDay),
        payment_day: Number(paymentDay),
      }
      if (card) {
        await api.updateCreditCard(card.id, payload)
      } else {
        await api.createCreditCard(payload)
      }
    },
    onSuccess: () => {
      toast.success(card ? 'Tarjeta actualizada' : 'Tarjeta creada')
      onOpenChange(false)
      void queryClient.invalidateQueries({ queryKey: ['creditCards'] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    mutation.mutate()
  }

  const days = Array.from({ length: 31 }, (_, i) => String(i + 1))

  return (
    <>
      <DialogHeader>
        <DialogTitle>{card ? 'Editar tarjeta' : 'Nueva tarjeta de crédito'}</DialogTitle>
        <DialogDescription>
          El cupo disponible se calcula solo: límite menos lo gastado en el mes.
        </DialogDescription>
      </DialogHeader>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="cc-name">Banco</Label>
          <Input
            id="cc-name"
            required
            placeholder="Ej. Bancolombia, Nu, Lulo"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="cc-limit">Límite de la tarjeta</Label>
          <Input
            id="cc-limit"
            required
            placeholder="5.000.000"
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label>Fecha de corte</Label>
            <Select value={cutoffDay} onValueChange={(v) => setCutoffDay(v ?? '15')}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {days.map((d) => (
                  <SelectItem key={d} value={d}>
                    Día {d}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Hasta qué día puedes usar la tarjeta en el ciclo.
            </p>
          </div>
          <div className="space-y-1.5">
            <Label>Fecha de pago</Label>
            <Select value={paymentDay} onValueChange={(v) => setPaymentDay(v ?? '30')}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {days.map((d) => (
                  <SelectItem key={d} value={d}>
                    Día {d}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Fecha límite para pagar el ciclo.
            </p>
          </div>
        </div>
        <Button type="submit" className="w-full" disabled={mutation.isPending}>
          {mutation.isPending ? 'Guardando…' : 'Guardar'}
        </Button>
      </form>
    </>
  )
}

function PayCardForm({
  open,
  onOpenChange,
  card,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  card: CreditCard | null
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {open && card && <PayCardBody card={card} onOpenChange={onOpenChange} />}
      </DialogContent>
    </Dialog>
  )
}

function PayCardBody({
  card,
  onOpenChange,
}: {
  card: CreditCard
  onOpenChange: (open: boolean) => void
}) {
  const queryClient = useQueryClient()
  const accounts = useQuery({ queryKey: ['accounts'], queryFn: api.listAccounts })
  const [accountId, setAccountId] = useState('')
  const [amount, setAmount] = useState(card.outstanding)

  const outstanding = Number(card.outstanding)
  const selectedAccount: Account | undefined = (accounts.data ?? []).find(
    (a) => String(a.id) === accountId,
  )
  const balance = selectedAccount ? Number(selectedAccount.balance) : 0
  const amountNum = Number(normalizeAmount(amount || '0'))

  const mutation = useMutation({
    mutationFn: () =>
      api.createTransaction({
        date: new Date().toISOString().slice(0, 10),
        amount: normalizeAmount(amount),
        kind: 'pago_tc',
        category_id: null,
        account_id: Number(accountId),
        to_account_id: null,
        card_id: card.id,
        description: `Pago ${card.name}`,
        is_recurring: false,
        recurring_day: null,
        subcategory_id: null,
      }),
    onSuccess: () => {
      toast.success('Pago registrado')
      onOpenChange(false)
      void queryClient.invalidateQueries({ queryKey: ['creditCards'] })
      void queryClient.invalidateQueries({ queryKey: ['accounts'] })
      void queryClient.invalidateQueries({ queryKey: ['transactions'] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    if (!accountId) {
      toast.error('Selecciona la cuenta de donde sale el pago')
      return
    }
    mutation.mutate()
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle>Pagar {card.name}</DialogTitle>
        <DialogDescription>
          El pago sale de una cuenta tuya y libera cupo de la tarjeta.
        </DialogDescription>
      </DialogHeader>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="rounded-xl bg-orange-500/10 p-3 text-center">
          <p className="text-xs font-extrabold uppercase tracking-wide text-muted-foreground">
            Deuda total
          </p>
          <p className="text-2xl font-black text-orange-600">{fmtCopDecimals(card.outstanding)}</p>
          <p className="text-xs font-bold text-muted-foreground">
            Cuota del mes: {fmtCopDecimals(card.pending)}
          </p>
        </div>

        <div className="space-y-1.5">
          <Label>Pagar desde</Label>
          <Select value={accountId} onValueChange={(v) => setAccountId(v ?? '')}>
            <SelectTrigger>
              <SelectValue placeholder="Selecciona la cuenta" />
            </SelectTrigger>
            <SelectContent>
              {(accounts.data ?? []).map((account) => (
                <SelectItem key={account.id} value={String(account.id)}>
                  {account.icon} {account.name} ({fmtCopDecimals(account.balance)})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {selectedAccount && balance < amountNum && (
            <p className="text-xs font-bold text-red-500">
              Saldo insuficiente: la cuenta tiene {fmtCopDecimals(balance)} y quieres pagar{' '}
              {fmtCopDecimals(amountNum)}.
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="pay-amount">Monto a pagar</Label>
          <Input
            id="pay-amount"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0"
          />
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => setAmount(String(Math.round(Number(card.pending))))}
            >
              Cuota del mes
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => setAmount(card.outstanding)}
            >
              Deuda total
            </Button>
          </div>
        </div>

        <Button
          type="submit"
          className="w-full"
          disabled={
            mutation.isPending ||
            !accountId ||
            amountNum <= 0 ||
            amountNum > outstanding ||
            (!!selectedAccount && balance < amountNum)
          }
        >
          {mutation.isPending ? 'Pagando…' : `Pagar ${fmtCopDecimals(amountNum || 0)}`}
        </Button>
      </form>
    </>
  )
}

export function CreditCardsSection({ readOnly = false }: { readOnly?: boolean } = {}) {
  const { month } = useMonth()
  const queryClient = useQueryClient()
  const cards = useQuery({
    queryKey: ['creditCards', month],
    queryFn: () => api.listCreditCards(month.month, month.year),
  })
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<CreditCard | null>(null)
  const [deleting, setDeleting] = useState<CreditCard | null>(null)
  const [paying, setPaying] = useState<CreditCard | null>(null)

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteCreditCard(id),
    onSuccess: () => {
      toast.success('Tarjeta eliminada — sus gastos quedaron sin tarjeta')
      setDeleting(null)
      void queryClient.invalidateQueries({ queryKey: ['creditCards'] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return (
    <>
      <SectionCard
        icon={CreditCardIcon}
        title="Tarjetas de crédito"
        subtitle="Cupo disponible según tus gastos TC del mes"
        action={
          !readOnly ? (
            <Button
              size="icon"
              aria-label="Nueva tarjeta"
              onClick={() => {
                setEditing(null)
                setFormOpen(true)
              }}
            >
              <Plus />
            </Button>
          ) : undefined
        }
      >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.isLoading ? (
          <>
            <Skeleton className="h-40 w-full" />
            <Skeleton className="h-40 w-full" />
          </>
        ) : cards.data?.length === 0 ? (
          <Card className="col-span-full p-6 text-center text-sm font-semibold text-muted-foreground">
            Aún no tienes tarjetas. Añade una para registrar tus gastos con tarjeta de crédito.
          </Card>
        ) : (
          [...(cards.data ?? [])]
            .sort((a, b) => Number(b.available) - Number(a.available))
            .map((card) => {
            const limit = Number(card.limit)
            const outstanding = Number(card.outstanding)
            const percent = limit > 0 ? (outstanding / limit) * 100 : 0
            const over = outstanding > limit
            return (
              <Card key={card.id} className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex size-11 items-center justify-center rounded-xl bg-orange-500 text-xl text-white shadow-[0_3px_0_0_#c2410c]">
                      <CreditCardIcon className="size-5" />
                    </div>
                    <div>
                      <CardTitle className="text-sm leading-tight">{card.name}</CardTitle>
                      <p className="text-xs font-bold text-muted-foreground">
                        Corte: día {card.cutoff_day} · Pago: día {card.payment_day}
                      </p>
                    </div>
                  </div>
                  {!readOnly && (
                    <div className="flex gap-0.5">
                      <Button
                        variant="ghost"
                        size="icon-xs"
                        onClick={() => {
                          setEditing(card)
                          setFormOpen(true)
                        }}
                      >
                        <Pencil className="size-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon-xs" onClick={() => setDeleting(card)}>
                        <Trash2 className="size-3.5 text-destructive" />
                      </Button>
                    </div>
                  )}
                </div>

                <div className="mt-4 space-y-1.5">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-bold text-muted-foreground">Cupo disponible</span>
                    <span className={`font-black ${over ? 'text-red-600' : ''}`}>
                      {fmtCopDecimals(card.available)}
                    </span>
                  </div>
                  <Progress
                    value={Math.min(percent, 100)}
                    indicatorClassName={over ? 'bg-red-500' : 'bg-orange-500'}
                  />
                  <p className="text-xs font-bold text-muted-foreground">
                    de {fmtCopDecimals(card.limit)}
                  </p>
                  <div className="flex items-center justify-between text-xs font-bold text-muted-foreground">
                    <span>
                      Ciclo {fmtDay(addOneDay(card.cycle_start))} → {fmtDay(card.cycle_end)}
                    </span>
                    <span>Pago {fmtDay(card.payment_date)}</span>
                  </div>
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-xs font-bold">
                      <span className="text-muted-foreground">Por facturar </span>
                      {fmtCopDecimals(card.pending)}
                    </span>
                    <Button
                      size="sm"
                      disabled={outstanding <= 0}
                      onClick={() => setPaying(card)}
                    >
                      <Wallet /> Pagar
                    </Button>
                  </div>
                  {outstanding > 0 && (
                    <p className="text-xs font-bold text-orange-600">
                      Deuda total: {fmtCopDecimals(card.outstanding)}
                    </p>
                  )}
                </div>
              </Card>
            )
          })
        )}
      </div>
      </SectionCard>

      <CardForm open={formOpen} onOpenChange={setFormOpen} card={editing} />

      <PayCardForm open={!!paying} onOpenChange={(open) => !open && setPaying(null)} card={paying} />

      <AlertDialog open={!!deleting} onOpenChange={(open) => !open && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar tarjeta?</AlertDialogTitle>
            <AlertDialogDescription>
              Se eliminará &quot;{deleting?.name}&quot;. Sus gastos TC no se borran, solo
              quedan sin tarjeta asignada.
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
    </>
  )
}
