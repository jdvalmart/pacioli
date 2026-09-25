import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'
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
import { api } from '@/lib/api'
import { normalizeAmount } from '@/lib/money'
import type { SavingsItem, SavingsKind } from '@/lib/types'

export const KIND_META: Record<SavingsKind, { label: string; icon: string }> = {
  bolsillo: { label: 'Bolsillo', icon: '👝' },
  bolsillo_programado: { label: 'Bolsillo programado', icon: '📆' },
  cdt: { label: 'CDT', icon: '🏦' },
  acciones: { label: 'Acciones', icon: '📈' },
}

export function SavingsFormDialog({
  open,
  onOpenChange,
  item,
  onCreated,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  item: SavingsItem | null
  onCreated?: (id: number) => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {open && (
          <SavingsFormBody item={item} onOpenChange={onOpenChange} onCreated={onCreated} />
        )}
      </DialogContent>
    </Dialog>
  )
}

function SavingsFormBody({
  item,
  onOpenChange,
  onCreated,
}: {
  item: SavingsItem | null
  onOpenChange: (open: boolean) => void
  onCreated?: (id: number) => void
}) {
  const queryClient = useQueryClient()
  const accounts = useQuery({ queryKey: ['accounts'], queryFn: api.listAccounts })

  const [name, setName] = useState(item?.name ?? '')
  const [kind, setKind] = useState<SavingsKind>(item?.kind ?? 'bolsillo')
  const [target, setTarget] = useState(item?.target ?? '')
  const [rate, setRate] = useState(item?.rate_bp != null ? String(item.rate_bp / 100) : '')
  const [termDays, setTermDays] = useState(item?.term_days ? String(item.term_days) : '180')
  const [currentValue, setCurrentValue] = useState(item?.current_value ?? '')
  const [dividends, setDividends] = useState(
    item?.dividends && item.dividends !== '0.00' ? String(Math.round(Number(item.dividends))) : '',
  )
  const [scheduledDay, setScheduledDay] = useState(
    item?.scheduled_day ? String(item.scheduled_day) : '15',
  )
  const [scheduledAmount, setScheduledAmount] = useState(item?.scheduled_amount ?? '')
  const [sourceAccountId, setSourceAccountId] = useState(
    item?.source_account_id ? String(item.source_account_id) : '',
  )
  const [initialAmount, setInitialAmount] = useState('')
  const [initialAccountId, setInitialAccountId] = useState('')

  const mutation = useMutation({
    mutationFn: async () => {
      const common = {
        name,
        kind,
        target: target ? normalizeAmount(target) : null,
        rate_bp: rate ? Math.round(Number(rate) * 100) : null,
        term_days:
          kind === 'bolsillo_programado' || kind === 'cdt' ? Number(termDays) : null,
        current_value: kind === 'acciones' && currentValue ? normalizeAmount(currentValue) : null,
        dividends: kind === 'acciones' && dividends ? normalizeAmount(dividends) : null,
        scheduled_day: kind === 'bolsillo_programado' ? Number(scheduledDay) : null,
        scheduled_amount:
          kind === 'bolsillo_programado' && scheduledAmount ? normalizeAmount(scheduledAmount) : null,
        source_account_id:
          kind === 'bolsillo_programado' && sourceAccountId ? Number(sourceAccountId) : null,
      }
      if (item) {
        await api.updateSavings(item.id, common)
        return item.id
      }
      const created = await api.createSavings({
        ...common,
        initial_amount: initialAmount ? normalizeAmount(initialAmount) : null,
        initial_account_id: initialAccountId ? Number(initialAccountId) : null,
      })
      return created.id
    },
    onSuccess: (id) => {
      toast.success(item ? 'Actualizado' : 'Creado')
      onOpenChange(false)
      if (!item && id != null) onCreated?.(id)
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
    if (!item && initialAmount && !initialAccountId) {
      toast.error('Selecciona de qué cuenta sale el monto inicial')
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
          El saldo se calcula con los movimientos de ahorro y retiro, que siempre salen de una
          cuenta.
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

        {kind === 'bolsillo' && (
          <div className="space-y-1.5">
            <Label htmlFor="sv-rate">Tasa EA (%)</Label>
            <Input
              id="sv-rate"
              placeholder="10.5"
              value={rate}
              onChange={(e) => setRate(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Interés que paga el bolsillo. Podés mover el dinero cuando quieras.
            </p>
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
            <p className="text-xs text-muted-foreground">
              No se puede retirar hasta que venza el plazo.
            </p>
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
            <p className="col-span-2 text-xs text-muted-foreground">
              No se puede retirar hasta que venza el plazo.
            </p>
          </div>
        )}

        {kind === 'acciones' && (
          <>
            <div className="space-y-1.5">
              <Label htmlFor="sv-value">Valor actual (opcional)</Label>
              <Input
                id="sv-value"
                placeholder="1.300.000"
                value={currentValue}
                onChange={(e) => setCurrentValue(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Actualízalo cuando quieras para ver la ganancia por precio.
              </p>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="sv-dividends">Dividendos recibidos (opcional)</Label>
              <Input
                id="sv-dividends"
                placeholder="0"
                value={dividends}
                onChange={(e) => setDividends(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Total de dividendos que te ha pagado. Se suman a la ganancia.
              </p>
            </div>
          </>
        )}

        {!item && (
          <div className="space-y-3 rounded-xl border border-dashed border-primary/40 bg-primary/5 p-3">
            <p className="text-xs font-bold text-muted-foreground">
              Monto inicial (opcional) — el dinero sale de una cuenta
            </p>
            <div className="space-y-1.5">
              <Label>Desde la cuenta</Label>
              <Select value={initialAccountId} onValueChange={(v) => setInitialAccountId(v ?? '')}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona la cuenta" />
                </SelectTrigger>
                <SelectContent>
                  {(accounts.data ?? []).map((account) => (
                    <SelectItem key={account.id} value={String(account.id)}>
                      {account.icon} {account.name} ({account.balance})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="sv-init">Monto</Label>
              <Input
                id="sv-init"
                placeholder="0"
                value={initialAmount}
                onChange={(e) => setInitialAmount(e.target.value)}
              />
            </div>
          </div>
        )}

        <Button type="submit" className="w-full" disabled={mutation.isPending}>
          {mutation.isPending ? 'Guardando…' : 'Guardar'}
        </Button>
      </form>
    </>
  )
}
