import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Pencil, PiggyBank, Plus, Trash2, TrendingUp } from 'lucide-react'
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
import { api } from '@/lib/api'
import { fmtCopDecimals, normalizeAmount } from '@/lib/money'
import type { SavingsItem, SavingsKind } from '@/lib/types'

const KIND_META: Record<SavingsKind, { label: string; icon: string }> = {
  bolsillo: { label: 'Bolsillo', icon: '👝' },
  bolsillo_programado: { label: 'Bolsillo programado', icon: '📆' },
  cdt: { label: 'CDT', icon: '🏦' },
  acciones: { label: 'Acciones', icon: '📈' },
}

function SavingsForm({
  open,
  onOpenChange,
  item,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  item: SavingsItem | null
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {open && <SavingsFormBody item={item} onOpenChange={onOpenChange} />}
      </DialogContent>
    </Dialog>
  )
}

function SavingsFormBody({
  item,
  onOpenChange,
}: {
  item: SavingsItem | null
  onOpenChange: (open: boolean) => void
}) {
  const queryClient = useQueryClient()
  const accounts = useQuery({ queryKey: ['accounts'], queryFn: api.listAccounts })

  const [name, setName] = useState(item?.name ?? '')
  const [kind, setKind] = useState<SavingsKind>(item?.kind ?? 'bolsillo')
  const [target, setTarget] = useState(item?.target ?? '')
  const [rate, setRate] = useState(
    item?.rate_bp != null ? String(item.rate_bp / 100) : '',
  )
  const [termDays, setTermDays] = useState(item?.term_days ? String(item.term_days) : '180')
  const [currentValue, setCurrentValue] = useState(item?.current_value ?? '')
  const [scheduledDay, setScheduledDay] = useState(
    item?.scheduled_day ? String(item.scheduled_day) : '15',
  )
  const [scheduledAmount, setScheduledAmount] = useState(item?.scheduled_amount ?? '')
  const [sourceAccountId, setSourceAccountId] = useState(
    item?.source_account_id ? String(item.source_account_id) : '',
  )
  const [initialAmount, setInitialAmount] = useState('')

  const mutation = useMutation({
    mutationFn: async () => {
      const common = {
        name,
        kind,
        target: target ? normalizeAmount(target) : null,
        rate_bp: rate ? Math.round(Number(rate) * 100) : null,
        term_days: kind === 'cdt' ? Number(termDays) : null,
        current_value: kind === 'acciones' && currentValue ? normalizeAmount(currentValue) : null,
        scheduled_day: kind === 'bolsillo_programado' ? Number(scheduledDay) : null,
        scheduled_amount:
          kind === 'bolsillo_programado' && scheduledAmount ? normalizeAmount(scheduledAmount) : null,
        source_account_id:
          kind === 'bolsillo_programado' && sourceAccountId ? Number(sourceAccountId) : null,
      }
      if (item) {
        await api.updateSavings(item.id, common)
      } else {
        await api.createSavings({
          ...common,
          initial_amount: initialAmount ? normalizeAmount(initialAmount) : null,
        })
      }
    },
    onSuccess: () => {
      toast.success(item ? 'Actualizado' : 'Creado')
      onOpenChange(false)
      void queryClient.invalidateQueries({ queryKey: ['savings'] })
      void queryClient.invalidateQueries({ queryKey: ['accounts'] })
      void queryClient.invalidateQueries({ queryKey: ['transactions'] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    if (kind === 'bolsillo_programado' && !sourceAccountId) {
      toast.error('Selecciona la cuenta de origen del ahorro programado')
      return
    }
    mutation.mutate()
  }

  const days = Array.from({ length: 31 }, (_, i) => String(i + 1))

  return (
    <>
      <DialogHeader>
        <DialogTitle>{item ? 'Editar' : 'Nuevo ahorro o inversión'}</DialogTitle>
        <DialogDescription>
          El saldo se calcula solo con los movimientos de ahorro y retiro.
        </DialogDescription>
      </DialogHeader>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-4 gap-2">
          {(Object.keys(KIND_META) as SavingsKind[]).map((k) => (
            <button
              key={k}
              type="button"
              onClick={() => setKind(k)}
              className={`flex flex-col items-center gap-1 rounded-xl border px-1 py-2 text-[11px] font-bold transition-all ${
                kind === k
                  ? 'border-amber-600 bg-primary text-primary-foreground shadow-[0_3px_0_0_color-mix(in_oklch,var(--primary),black_18%)]'
                  : 'border-border bg-background text-muted-foreground hover:bg-muted'
              }`}
            >
              <span className="text-base">{KIND_META[k].icon}</span>
              {KIND_META[k].label}
            </button>
          ))}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="sv-name">Nombre</Label>
          <Input
            id="sv-name"
            required
            placeholder={kind === 'acciones' ? 'Ej. Ecopetrol' : 'Ej. Viaje, Emergencias'}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        {(kind === 'bolsillo' || kind === 'bolsillo_programado') && (
          <div className="space-y-1.5">
            <Label htmlFor="sv-target">Meta (opcional)</Label>
            <Input
              id="sv-target"
              placeholder="1.000.000"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            />
          </div>
        )}

        {kind === 'bolsillo_programado' && (
          <>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Día del mes</Label>
                <Select value={scheduledDay} onValueChange={(v) => setScheduledDay(v ?? '15')}>
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
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="sv-sched-amount">Monto mensual</Label>
                <Input
                  id="sv-sched-amount"
                  placeholder="200.000"
                  value={scheduledAmount}
                  onChange={(e) => setScheduledAmount(e.target.value)}
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>Cuenta de origen</Label>
              <Select value={sourceAccountId} onValueChange={(v) => setSourceAccountId(v ?? '')}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona la cuenta" />
                </SelectTrigger>
                <SelectContent>
                  {(accounts.data ?? []).map((account) => (
                    <SelectItem key={account.id} value={String(account.id)}>
                      {account.icon} {account.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Se transferirá automáticamente cada mes en este día.
              </p>
            </div>
          </>
        )}

        {kind === 'cdt' && (
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="sv-rate">Tasa EA (%)</Label>
              <Input
                id="sv-rate"
                placeholder="10.5"
                value={rate}
                onChange={(e) => setRate(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="sv-term">Plazo (días)</Label>
              <Input
                id="sv-term"
                type="number"
                min={1}
                value={termDays}
                onChange={(e) => setTermDays(e.target.value)}
              />
            </div>
          </div>
        )}

        {kind === 'acciones' && (
          <div className="space-y-1.5">
            <Label htmlFor="sv-value">Valor actual (opcional)</Label>
            <Input
              id="sv-value"
              placeholder="1.300.000"
              value={currentValue}
              onChange={(e) => setCurrentValue(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Actualízalo cuando quieras para ver la ganancia.
            </p>
          </div>
        )}

        {!item && (
          <div className="space-y-1.5 rounded-xl border border-dashed border-primary/40 bg-primary/5 p-3">
            <Label htmlFor="sv-init">Saldo inicial (opcional)</Label>
            <Input
              id="sv-init"
              placeholder="0"
              value={initialAmount}
              onChange={(e) => setInitialAmount(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Dinero que ya tenías (por ejemplo un CDT existente). No cuenta en ningún mes,
              solo en el saldo.
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

export function SavingsSection({ readOnly = false }: { readOnly?: boolean } = {}) {
  const queryClient = useQueryClient()
  const items = useQuery({ queryKey: ['savings'], queryFn: api.listSavings })
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<SavingsItem | null>(null)
  const [deleting, setDeleting] = useState<SavingsItem | null>(null)

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteSavings(id),
    onSuccess: () => {
      toast.success('Eliminado')
      setDeleting(null)
      void queryClient.invalidateQueries({ queryKey: ['savings'] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const total = (items.data ?? []).reduce((sum, s) => sum + Number(s.balance), 0)

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-[0_3px_0_0_color-mix(in_oklch,var(--primary),black_18%)]">
            <PiggyBank className="size-5" />
          </div>
          <div>
            <h2 className="text-lg font-extrabold">Ahorro e inversión</h2>
            <p className="text-sm font-semibold text-muted-foreground">
              Bolsillos, ahorros programados, CDTs y acciones
              {(items.data ?? []).length > 0 && ` · total ${fmtCopDecimals(total)}`}
            </p>
          </div>
        </div>
        {!readOnly && (
          <Button
            size="icon"
            aria-label="Nuevo ahorro o inversión"
            onClick={() => {
              setEditing(null)
              setFormOpen(true)
            }}
          >
            <Plus />
          </Button>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.isLoading ? (
          <>
            <Skeleton className="h-36 w-full" />
            <Skeleton className="h-36 w-full" />
          </>
        ) : items.data?.length === 0 ? (
          <Card className="col-span-full p-6 text-center text-sm font-semibold text-muted-foreground">
            Aún no tienes ahorros ni inversiones. Crea un bolsillo, un CDT o registra tus
            acciones para ver crecer tu dinero.
          </Card>
        ) : (
          [...(items.data ?? [])]
            .sort((a, b) => {
              const valueA = a.current_value != null ? Number(a.current_value) : Number(a.balance)
              const valueB = b.current_value != null ? Number(b.current_value) : Number(b.balance)
              return valueB - valueA
            })
            .map((item) => {
            const balance = Number(item.balance)
            const invested = Number(item.invested)
            const current = item.current_value != null ? Number(item.current_value) : invested
            const gain = current - invested
            const gainPct = invested > 0 ? (gain / invested) * 100 : 0
            const target = item.target ? Number(item.target) : 0
            const targetPct = target > 0 ? (balance / target) * 100 : 0

            return (
              <Card key={item.id} className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex size-11 items-center justify-center rounded-xl bg-amber-400 text-xl text-amber-950 shadow-[0_3px_0_0_#b45309]">
                      {KIND_META[item.kind]?.icon ?? '💰'}
                    </div>
                    <div>
                      <CardTitle className="text-sm leading-tight">{item.name}</CardTitle>
                      <p className="text-xs font-bold text-muted-foreground">
                        {KIND_META[item.kind]?.label ?? item.kind}
                      </p>
                    </div>
                  </div>
                  {!readOnly && (
                    <div className="flex gap-0.5">
                      <Button
                        variant="ghost"
                        size="icon-xs"
                        onClick={() => {
                          setEditing(item)
                          setFormOpen(true)
                        }}
                      >
                        <Pencil className="size-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon-xs" onClick={() => setDeleting(item)}>
                        <Trash2 className="size-3.5 text-destructive" />
                      </Button>
                    </div>
                  )}
                </div>

                <div className="mt-3 space-y-1.5">
                  <p className="text-xl font-black">{fmtCopDecimals(item.balance)}</p>

                  {item.kind === 'acciones' && (
                    <p
                      className={`text-xs font-bold ${
                        gain >= 0 ? 'text-emerald-600' : 'text-red-600'
                      }`}
                    >
                      <TrendingUp className="mr-1 inline size-3.5" />
                      {gain >= 0 ? '+' : ''}
                      {fmtCopDecimals(gain)} ({gainPct >= 0 ? '+' : ''}
                      {gainPct.toFixed(1)}%)
                    </p>
                  )}

                  {item.kind === 'cdt' && item.rate_bp != null && (
                    <p className="text-xs font-bold text-muted-foreground">
                      Tasa {item.rate_bp / 100}% EA ·{' '}
                      {item.term_days
                        ? `rendimiento ≈ ${fmtCopDecimals(
                            (invested * (item.rate_bp / 100) * (item.term_days / 360)) / 100,
                          )}`
                        : ''}
                    </p>
                  )}

                  {item.kind === 'bolsillo_programado' && item.scheduled_amount != null && (
                    <p className="text-xs font-bold text-muted-foreground">
                      📆 Día {item.scheduled_day}: {fmtCopDecimals(item.scheduled_amount)}/mes
                    </p>
                  )}

                  {target > 0 && (
                    <>
                      <Progress
                        value={Math.min(targetPct, 100)}
                        className="[&>div]:bg-amber-400"
                      />
                      <p className="text-xs font-bold text-muted-foreground">
                        {Math.round(targetPct)}% de la meta {fmtCopDecimals(target)}
                      </p>
                    </>
                  )}
                </div>
              </Card>
            )
          })
        )}
      </div>

      <SavingsForm open={formOpen} onOpenChange={setFormOpen} item={editing} />

      <AlertDialog open={!!deleting} onOpenChange={(open) => !open && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar {deleting?.name}?</AlertDialogTitle>
            <AlertDialogDescription>
              Se eliminará junto con su ahorro programado (si tiene). Los movimientos no se
              borran, solo quedan sin bolsillo asignado.
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
    </section>
  )
}
