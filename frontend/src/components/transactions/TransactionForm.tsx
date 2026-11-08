import { Plus } from 'lucide-react'
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
import { SavingsFormDialog } from '@/components/SavingsFormDialog'
import { fmtMoney, normalizeAmount } from '@/lib/money'
import type { Transaction } from '@/lib/types'

import { FORM_KINDS, KIND_META } from '@/components/transactions/kinds'
import { useTransactionForm } from '@/components/transactions/useTransactionForm'

const FORM_OPTIONS = FORM_KINDS.map((value) => ({ value, ...KIND_META[value] }))

interface TransactionFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  transaction: Transaction | null
}

export function TransactionForm({ open, onOpenChange, transaction }: TransactionFormProps) {
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
  const {
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
    mutation,
    handleKindChange,
    handleSubmit,
  } = useTransactionForm(transaction, () => onOpenChange(false))

  return (
    <>
      <DialogHeader>
        <DialogTitle>{transaction ? 'Editar movimiento' : 'Nuevo movimiento'}</DialogTitle>
        <DialogDescription>
          {transaction ? 'Actualiza los datos y guarda.' : 'Registra un movimiento de este mes.'}
        </DialogDescription>
      </DialogHeader>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-3 gap-2">
          {FORM_OPTIONS.map(({ value, label, icon: Icon, activeClass }) => (
            <button
              key={value}
              type="button"
              onClick={() => handleKindChange(value)}
              className={`flex flex-col items-center gap-1 rounded-xl border px-2 py-2.5 text-xs font-medium transition-all ${
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
                  <SelectValue placeholder="Cuenta origen" />
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
                  <SelectValue placeholder="Cuenta destino" />
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
                <p className="text-xs font-medium text-muted-foreground">
                  🔒 Bloqueado hasta {selectedSavings?.matures_on} — no puedes mover el dinero hasta el vencimiento.
                </p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label>{kind === 'ahorro' ? 'Cuenta origen' : 'Cuenta destino'}</Label>
              {!hasAccounts ? (
                <div className="rounded-xl border border-dashed border-primary/50 bg-primary/10 p-3 text-sm font-semibold text-muted-foreground">
                  Todavía no tienes cuentas. Crea una en Ajustes.
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
                    ? 'Apartado en el bolsillo: sale del saldo disponible, sigue siendo tuyo.'
                    : 'El dinero sale de tu cuenta hacia el ahorro (no se cuenta como gasto).'
                  : savingsIsBolsillo
                    ? 'Retirado del bolsillo: vuelve al saldo disponible.'
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
                  <div className="rounded-lg border border-dashed border-border bg-muted/50 p-3 text-sm text-muted-foreground">
                    💳 Todavía no tienes tarjetas. Crea una en Ajustes (sección Tarjetas de
                    crédito) para registrar compras con tarjeta.
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
                        ? `Cuota: ${fmtMoney(
                            (Number(normalizeAmount(amount || '0')) *
                              (1 + Number(interest || '0') / 100)) /
                              (Number(installments) || 1),
                          )} por mes`
                        : 'Sin interés con 1 sola cuota.'}
                    </p>
                  </>
                )}
              </div>
            ) : (
              <div className="space-y-1.5">
                <Label>{accountLabel}</Label>
                {!hasAccounts ? (
                  <div className="rounded-xl border border-dashed border-primary/50 bg-primary/10 p-3 text-sm font-semibold text-muted-foreground">
                    Todavía no tienes cuentas. Crea una en Ajustes (billetera,
                    banco, ahorro…) para registrar movimientos.
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
            placeholder="Ej. Mercado de la semana"
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
          <Label htmlFor="tx-recurring">Recurrente (arriendo, servicios, ahorro…)</Label>
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
