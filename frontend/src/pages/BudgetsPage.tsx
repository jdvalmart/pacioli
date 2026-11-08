import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { ArrowUpRight, PieChart, PiggyBank, SlidersHorizontal, Wallet } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { StatCard } from '@/components/StatCard'
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
import { Skeleton } from '@/components/ui/skeleton'
import { monthLabel, useMonth } from '@/hooks/useMonth'
import { CategoryIcon } from '@/components/CategoryIcon'
import { PageHeader, SectionHeading } from '@/components/PageHeader'
import { api } from '@/lib/api'
import { useBudgetPlan, useBudgetVsActual, useBudgets, useCategories, useInvalidate, useSummary } from '@/lib/queries'
import { fmtMoney, normalizeAmount } from '@/lib/money'
import { budgetTotals, totalSourceLabel } from '@/lib/budget'
import { cn } from '@/lib/utils'
import type { Category } from '@/lib/types'

const num = (value: string | undefined): number => Number(normalizeAmount(value || '0'))

const fmtInput = (value: string | number): string => {
  const n = Math.round(Number(value))
  if (!Number.isFinite(n) || n === 0) return ''
  return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

const parseMoneyInput = (raw: string): string => {
  const digits = raw.replace(/\D/g, '').replace(/^0+/, '')
  if (!digits) return ''
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

function MoneyInput({
  id,
  value,
  onChange,
  placeholder = '0',
  className,
}: {
  id?: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
}) {
  return (
    <div className={cn('relative', className)}>
      <span className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-sm font-medium text-muted-foreground">
        $
      </span>
      <Input
        id={id}
        inputMode="numeric"
        autoComplete="off"
        placeholder={placeholder}
        className="pl-7 text-right font-medium tabular-nums"
        value={value}
        onChange={(e) => onChange(parseMoneyInput(e.target.value))}
      />
    </div>
  )
}

function CategoryField({
  category,
  value,
  onChange,
  total,
}: {
  category: Category
  value: string
  onChange: (value: string) => void
  total: number
}) {
  const amount = num(value)
  const percent = total > 0 && amount > 0 ? Math.round((amount / total) * 100) : null
  return (
    <div className="flex items-center gap-3">
      <CategoryIcon icon={category.icon} color={category.color} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{category.name}</p>
        {percent != null && (
          <p className="text-xs text-muted-foreground">{percent}% del total</p>
        )}
      </div>
      <MoneyInput
        id={`budget-${category.id}`}
        className="w-36"
        value={value}
        onChange={onChange}
      />
    </div>
  )
}

function BudgetSetupDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { month } = useMonth()
  const invalidate = useInvalidate()
  const categories = useCategories()
  const budgets = useBudgets(month)

  const summary = useSummary(month, { enabled: open })
  const plan = useBudgetPlan(month, { enabled: open })

  const [total, setTotal] = useState('')
  const [amounts, setAmounts] = useState<Record<string, string>>({})

  const allExpense = categories.data?.filter((c) => c.type === 'expense') ?? []
  // The savings category is the month's savings goal; it goes first, on its own.
  const savingsCategory = allExpense.find((c) => c.role === 'savings')
  const savedAmount = (id: number) => Number((budgets.data ?? []).find((b) => b.category_id === id)?.amount ?? 0)
  const spendCategories = allExpense
    .filter((c) => c.role !== 'savings')
    .sort((a, b) => savedAmount(b.id) - savedAmount(a.id) || a.name.localeCompare(b.name, 'es'))
  const orderedCategories = savingsCategory ? [savingsCategory, ...spendCategories] : spendCategories

  // Initialize the form: total = the month's plan (saved, inherited or recent
  // income average; else this month's income), amounts = budgets in effect.
  const [initialized, setInitialized] = useState(false)
  if (open && !initialized && budgets.data && categories.data && summary.data && plan.data) {
    const map: Record<string, string> = {}
    for (const b of budgets.data) {
      map[String(b.category_id)] = fmtInput(b.amount)
    }
    setAmounts(map)
    const savedTotal = plan.data.total
    setTotal(savedTotal != null ? fmtInput(savedTotal) : fmtInput(Number(summary.data.total_income)))
    setInitialized(true)
  }
  if (!open && initialized) {
    setInitialized(false)
  }

  const setAmount = (id: number | undefined, value: string) => {
    if (id == null) return
    setAmounts((prev) => ({ ...prev, [String(id)]: value }))
  }

  const totalNum = num(total)
  const assigned = orderedCategories.reduce((sum, c) => sum + num(amounts[String(c.id)]), 0)
  const pending = totalNum - assigned
  const usedPercent = totalNum > 0 ? Math.min(100, (assigned / totalNum) * 100) : 0

  const mutation = useMutation({
    mutationFn: async () => {
      await api.replaceBudgets({
        month: month.month,
        year: month.year,
        budgets: allExpense
          .filter((cat) => num(amounts[String(cat.id)]) > 0)
          .map((cat) => ({
            category_id: cat.id,
            amount: normalizeAmount(amounts[String(cat.id)]),
          })),
      })
      await api.setBudgetPlan({
        month: month.month,
        year: month.year,
        total: normalizeAmount(total || '0'),
      })
    },
    onSuccess: () => {
      toast.success('Presupuesto guardado')
      onOpenChange(false)
      void invalidate('budget')
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        {open && (
          <>
            <DialogHeader>
              <DialogTitle>Definir presupuesto</DialogTitle>
              <DialogDescription>
                Planifica tu gasto en {monthLabel(month)}: reparte tu presupuesto total entre
                categorías.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-5">
              <div className="space-y-1.5">
                <Label htmlFor="budget-total">Mi presupuesto total</Label>
                <MoneyInput id="budget-total" value={total} onChange={setTotal} placeholder="3.000.000" />
                <p className="text-xs text-muted-foreground">
                  {plan.data?.total != null
                    ? `${totalSourceLabel(plan.data.source ?? 'saved')}.`
                    : `Sin datos previos: usamos tus ingresos del mes (${fmtMoney(Number(summary.data?.total_income ?? 0))}).`}
                </p>
              </div>

              <div className="rounded-xl border border-border bg-muted/40 p-4">
                <div className="grid grid-cols-2 gap-2 text-center">
                  <div>
                    <p className="text-[10px] font-semibold tracking-wide text-muted-foreground uppercase">
                      Asignado
                    </p>
                    <p className="text-sm font-semibold">{fmtMoney(assigned)}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-semibold tracking-wide text-muted-foreground uppercase">
                      Sin asignar
                    </p>
                    <p
                      className={cn(
                        'text-sm font-semibold',
                        pending < 0
                          ? 'text-negative'
                          : pending > 0
                            ? 'text-foreground'
                            : 'text-positive',
                      )}
                    >
                      {fmtMoney(pending)}
                    </p>
                  </div>
                </div>
                <Progress
                  value={usedPercent}
                  className="mt-3"
                  indicatorClassName={pending < 0 ? 'bg-negative' : undefined}
                />
                {pending < 0 && (
                  <p className="mt-2 text-xs font-medium text-negative">
                    Te pasaste {fmtMoney(Math.abs(pending))}
                  </p>
                )}
              </div>

              {savingsCategory && (
                <div className="space-y-2">
                  <p className="text-xs font-medium text-muted-foreground">Meta de ahorro</p>
                  <CategoryField
                    category={savingsCategory}
                    value={amounts[String(savingsCategory.id)] ?? ''}
                    onChange={(v) => setAmount(savingsCategory.id, v)}
                    total={totalNum}
                  />
                  <p className="text-xs text-muted-foreground">
                    Cuánto quieres apartar este mes. No es gasto: superarla es bueno.
                  </p>
                </div>
              )}

              <div className="space-y-3">
                <p className="text-xs font-medium text-muted-foreground">Categorías de gasto</p>
                {spendCategories.map((cat) => (
                  <CategoryField
                    key={cat.id}
                    category={cat}
                    value={amounts[String(cat.id)] ?? ''}
                    onChange={(v) => setAmount(cat.id, v)}
                    total={totalNum}
                  />
                ))}
              </div>

              <Button
                type="button"
                className="w-full"
                disabled={mutation.isPending}
                onClick={() => mutation.mutate()}
              >
                {mutation.isPending ? 'Guardando…' : 'Guardar presupuesto'}
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

export function BudgetsPage() {
  const { month } = useMonth()
  const categories = useCategories()
  const budgets = useBudgets(month)
  const budgetVsActual = useBudgetVsActual(month)
  const summary = useSummary(month)
  const plan = useBudgetPlan(month)

  const [setupOpen, setSetupOpen] = useState(false)

  const totals = budgetTotals(
    budgetVsActual.data ?? [],
    plan.data,
    Number(summary.data?.total_income ?? 0),
  )
  const inherited = (budgets.data ?? []).some((b) => b.inherited)
  const reservedTotal = (budgetVsActual.data ?? []).reduce((sum, row) => sum + Number(row.reserved), 0)
  const budgeted = new Set(totals.categories.map((c) => c.row.category_id))
  const spentByCategory = new Map(
    (budgetVsActual.data ?? []).map((row) => [row.category_id, Number(row.actual)]),
  )
  const reservedByCategory = new Map(
    (budgetVsActual.data ?? []).map((row) => [row.category_id, Number(row.reserved)]),
  )
  const withoutBudget = (categories.data ?? []).filter(
    (c) => c.type === 'expense' && c.role !== 'savings' && !budgeted.has(c.id),
  )
  const goal = totals.savings

  return (
    <div className="space-y-6">
      <PageHeader
        title="Presupuestos"
        description={`Cuánto puedes gastar por categoría en ${monthLabel(month).toLowerCase()}`}
        action={
          <Button onClick={() => setSetupOpen(true)}>
            <SlidersHorizontal /> Definir presupuesto
          </Button>
        }
      />

      {inherited && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-muted/50 px-4 py-2.5 text-sm text-muted-foreground">
          <span>
            Este mes usa el presupuesto del último mes que definiste. Ajústalo si este mes es distinto.
          </span>
          <Button variant="outline" size="sm" onClick={() => setSetupOpen(true)}>
            Ajustar este mes
          </Button>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <StatCard
          title="Presupuesto total"
          value={fmtMoney(totals.total)}
          detail={totalSourceLabel(totals.totalSource)}
          icon={Wallet}
          tone="primary"
        />
        <StatCard
          title="Gastado"
          value={fmtMoney(totals.spent)}
          detail={
            totals.spentWithoutBudget > 0
              ? `${fmtMoney(totals.spentWithoutBudget)} sin presupuesto`
              : 'Todo dentro de categorías con presupuesto'
          }
          icon={ArrowUpRight}
          tone="expense"
        />
        <StatCard
          title="Disponible"
          value={fmtMoney(totals.available)}
          valueClassName={totals.available < 0 ? 'text-negative' : undefined}
          detail={totals.available < 0 ? 'Gastaste más que tu presupuesto' : 'Lo que queda para gastar'}
          icon={PieChart}
          tone={totals.available < 0 ? 'expense' : 'neutral'}
        />
        <StatCard
          title="Meta de ahorro"
          value={goal ? fmtMoney(goal.saved) : fmtMoney(0)}
          valueClassName={goal && goal.goal > 0 && goal.saved >= goal.goal ? 'text-positive' : undefined}
          detail={
            !goal || goal.goal <= 0
              ? 'Define una meta en “Definir presupuesto”'
              : goal.saved >= goal.goal
                ? `Meta de ${fmtMoney(goal.goal)} cumplida`
                : `de ${fmtMoney(goal.goal)} · faltan ${fmtMoney(goal.goal - goal.saved)}`
          }
          icon={PiggyBank}
          tone="income"
        />
      </div>

      <section className="space-y-3">
        <SectionHeading
          title="Por categoría"
          count={totals.categories.length}
          aside={
            <>
              Asignado {fmtMoney(totals.assigned)}
              {totals.unassigned !== 0 && (
                <span className={cn('ml-2', totals.unassigned < 0 && 'text-negative')}>
                  ·{' '}
                  {totals.unassigned > 0
                    ? `sin asignar ${fmtMoney(totals.unassigned)}`
                    : `excede el total en ${fmtMoney(Math.abs(totals.unassigned))}`}
                </span>
              )}
            </>
          }
        />
        {budgets.isLoading || budgetVsActual.isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : totals.categories.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border px-4 py-10 text-center text-sm text-muted-foreground">
            Aún no asignas presupuesto a ninguna categoría.
          </div>
        ) : (
          <Card className="gap-0 py-0">
            <ul className="divide-y divide-border">
              {totals.categories.map(({ row, budget, spent, percent, over }) => {
                const reserved = reservedByCategory.get(row.category_id) ?? 0
                const remaining = budget - spent
                return (
                  <li
                    key={row.category_id}
                    className="grid grid-cols-[auto_1fr_auto] items-center gap-x-3 gap-y-2 px-4 py-3.5 sm:grid-cols-[auto_minmax(8rem,13rem)_1fr_13rem_10rem]"
                  >
                    <CategoryIcon icon={row.icon} color={row.color} />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{row.name}</p>
                      {reserved !== 0 && (
                        <p className="text-xs text-muted-foreground">Reservado {fmtMoney(reserved)}</p>
                      )}
                    </div>
                    <div className="col-span-3 flex items-center gap-3 sm:col-span-1">
                      <Progress
                        className="flex-1"
                        value={Math.min(percent, 100)}
                        indicatorClassName={over ? 'bg-negative' : undefined}
                      />
                      <span
                        className={cn(
                          'w-11 text-right text-xs font-medium',
                          over ? 'text-negative' : 'text-muted-foreground',
                        )}
                      >
                        {Math.round(percent)}%
                      </span>
                    </div>
                    <p className="row-start-1 col-start-3 text-right text-sm whitespace-nowrap sm:row-auto sm:col-auto">
                      <span className={cn('font-medium', over && 'text-negative')}>{fmtMoney(spent)}</span>
                      <span className="text-muted-foreground"> de {fmtMoney(budget)}</span>
                    </p>
                    <p
                      className={cn(
                        'hidden text-right text-sm sm:block',
                        over ? 'font-medium text-negative' : 'text-muted-foreground',
                      )}
                    >
                      {over ? `Excedido ${fmtMoney(Math.abs(remaining))}` : `Restan ${fmtMoney(remaining)}`}
                    </p>
                  </li>
                )
              })}
            </ul>
          </Card>
        )}
        {reservedTotal > 0 && (
          <p className="text-xs text-muted-foreground">
            Reservado en bolsillos para categorías: {fmtMoney(reservedTotal)}
          </p>
        )}
      </section>

      {withoutBudget.length > 0 && (
        <section className="space-y-3">
          <SectionHeading
            title="Sin presupuesto"
            count={withoutBudget.length}
            aside={
              totals.spentWithoutBudget > 0 ? `Gastado ${fmtMoney(totals.spentWithoutBudget)}` : undefined
            }
          />
          <div className="flex flex-wrap gap-2">
            {withoutBudget.map((category) => {
              const spent = spentByCategory.get(category.id) ?? 0
              return (
                <span
                  key={category.id}
                  className="flex items-center gap-2 rounded-lg border border-border bg-card py-1.5 pr-3 pl-1.5 text-sm"
                >
                  <CategoryIcon icon={category.icon} color={category.color} size="sm" />
                  {category.name}
                  {spent > 0 && <span className="text-muted-foreground">{fmtMoney(spent)}</span>}
                </span>
              )
            })}
          </div>
        </section>
      )}

      <BudgetSetupDialog open={setupOpen} onOpenChange={setSetupOpen} />
    </div>
  )
}
