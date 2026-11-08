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
      <div
        className="flex size-9 shrink-0 items-center justify-center rounded-lg text-base text-white"
        style={{ backgroundColor: category.color || '#888' }}
      >
        {category.icon}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{category.name}</p>
        {percent != null && (
          <p className="text-[11px] font-semibold text-muted-foreground">{percent}% del total</p>
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

  // Previous month (for the copy action).
  const prevDate = new Date(month.year, month.month - 2, 1)
  const prevMonth = { month: prevDate.getMonth() + 1, year: prevDate.getFullYear() }
  const previousBudgets = useBudgets(prevMonth, { enabled: open })
  const summary = useSummary(month, { enabled: open })
  const plan = useBudgetPlan(month, { enabled: open })

  const [total, setTotal] = useState('')
  const [amounts, setAmounts] = useState<Record<string, string>>({})

  const allExpense = categories.data?.filter((c) => c.type === 'expense') ?? []
  const findCat = (name: string) => allExpense.find((c) => c.name === name)

  // Diezmo and Ahorro are budget categories like any other, shown in
  // the user's preferred order rather than set apart.
  const orderedNames = ['Vivienda', 'Alimentación', 'Servicios', 'Transporte', 'Diezmo', 'Ahorro']
  const orderedCategories = [
    ...orderedNames.map((name) => findCat(name)).filter((c): c is Category => Boolean(c)),
    ...allExpense.filter((c) => !orderedNames.includes(c.name)),
  ]

  // Initialize the form: total = saved plan (or the month's income),
  // amounts from saved budgets.
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

  const hasPreviousBudgets = (previousBudgets.data ?? []).length > 0

  const copyPrevious = () => {
    const map: Record<string, string> = {}
    for (const b of previousBudgets.data ?? []) {
      map[String(b.category_id)] = fmtInput(b.amount)
    }
    setAmounts(map)
    toast.success('Presupuesto del mes copiado')
  }

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
      <DialogContent className="max-h-[88vh] overflow-y-auto sm:max-w-lg">
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
                <p className="text-xs font-semibold text-muted-foreground">
                  Por defecto usamos el ingreso del mes: {fmtMoney(Number(summary.data?.total_income ?? 0))}
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

              {hasPreviousBudgets && (
                <Button type="button" variant="outline" className="w-full" onClick={copyPrevious}>
                  📋 Copiar presupuesto del mes pasado
                </Button>
              )}

              <div className="space-y-3">
                <p className="text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">
                  Categorías
                </p>
                {orderedCategories.map((cat) => (
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

  const expenseCategories = categories.data?.filter((c) => c.type === 'expense') ?? []
  const budgetByCategory = new Map((budgets.data ?? []).map((b) => [b.category_id, b.amount]))
  const actualByCategory = new Map(
    (budgetVsActual.data ?? []).map((row) => [row.category_id, row.actual]),
  )
  const reservedByCategory = new Map(
    (budgetVsActual.data ?? []).map((row) => [row.category_id, row.reserved]),
  )

  const totalBudget = (budgets.data ?? []).reduce((sum, b) => sum + Number(b.amount), 0)
  const totalReserved = (budgetVsActual.data ?? []).reduce(
    (sum, row) => sum + Number(row.reserved),
    0,
  )
  // Compare only against budgeted categories, so this matches the
  // dashboard. Spending in categories without a budget is shown apart.
  const budgetedRows = (budgetVsActual.data ?? []).filter((row) => Number(row.budget) > 0)
  const totalActual = budgetedRows.reduce((sum, row) => sum + Number(row.actual), 0)
  const unbudgeted = (budgetVsActual.data ?? [])
    .filter((row) => Number(row.budget) === 0)
    .reduce((sum, row) => sum + Number(row.actual), 0)
  const totalRemaining = totalBudget - totalActual
  const income = Number(summary.data?.total_income ?? 0)
  const planTotal = plan.data?.total != null ? Number(plan.data.total) : income
  const unassigned = planTotal - totalBudget

  const rows = [...expenseCategories]
    .map((category) => {
      const budget = Number(budgetByCategory.get(category.id) ?? 0)
      const actual = Number(actualByCategory.get(category.id) ?? 0)
      const reserved = Number(reservedByCategory.get(category.id) ?? 0)
      return { category, budget, actual, reserved, percent: budget > 0 ? (actual / budget) * 100 : 0 }
    })
    .sort((a, b) => b.budget - a.budget || b.actual - a.actual)
  const withBudget = rows.filter((row) => row.budget > 0)
  const withoutBudget = rows.filter((row) => row.budget === 0)

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

      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <StatCard
          title="Presupuesto total"
          value={fmtMoney(planTotal)}
          detail={plan.data?.total == null ? 'Igual a tus ingresos del mes' : undefined}
          icon={Wallet}
          tone="primary"
        />
        <StatCard
          title="Asignado"
          value={fmtMoney(totalBudget)}
          detail={
            unassigned > 0
              ? `Sin asignar ${fmtMoney(unassigned)}`
              : unassigned < 0
                ? `Excede el total en ${fmtMoney(Math.abs(unassigned))}`
                : 'Todo asignado'
          }
          icon={PieChart}
          tone="neutral"
        />
        <StatCard
          title="Gastado"
          value={fmtMoney(totalActual)}
          detail={unbudgeted > 0 ? `+ ${fmtMoney(unbudgeted)} sin presupuesto` : 'En categorías con presupuesto'}
          icon={ArrowUpRight}
          tone="expense"
        />
        <StatCard
          title="Restante"
          value={fmtMoney(totalRemaining)}
          valueClassName={totalRemaining < 0 ? 'text-negative' : undefined}
          detail={totalReserved > 0 ? `Reservado en bolsillos ${fmtMoney(totalReserved)}` : undefined}
          icon={PiggyBank}
          tone={totalRemaining < 0 ? 'expense' : 'income'}
        />
      </div>

      <section className="space-y-3">
        <SectionHeading title="Por categoría" count={withBudget.length} />
        {budgets.isLoading || categories.isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : withBudget.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border px-4 py-10 text-center text-sm text-muted-foreground">
            Aún no asignas presupuesto a ninguna categoría este mes.
          </div>
        ) : (
          <Card className="gap-0 py-0">
            <ul className="divide-y divide-border">
              {withBudget.map(({ category, budget, actual, reserved, percent }) => {
                const over = percent > 100
                const remaining = budget - actual
                return (
                  <li
                    key={category.id}
                    className="grid grid-cols-[auto_1fr_auto] items-center gap-x-3 gap-y-2 px-4 py-3.5 sm:grid-cols-[auto_minmax(8rem,13rem)_1fr_13rem_10rem]"
                  >
                    <CategoryIcon icon={category.icon} color={category.color} />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{category.name}</p>
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
                      <span className={cn('font-medium', over && 'text-negative')}>{fmtMoney(actual)}</span>
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
      </section>

      {withoutBudget.length > 0 && (
        <section className="space-y-3">
          <SectionHeading
            title="Sin presupuesto"
            count={withoutBudget.length}
            aside={unbudgeted > 0 ? `Gastado ${fmtMoney(unbudgeted)}` : undefined}
          />
          <div className="flex flex-wrap gap-2">
            {withoutBudget.map(({ category, actual }) => (
              <span
                key={category.id}
                className="flex items-center gap-2 rounded-lg border border-border bg-card py-1.5 pr-3 pl-1.5 text-sm"
              >
                <CategoryIcon icon={category.icon} color={category.color} size="sm" />
                {category.name}
                {actual > 0 && <span className="text-muted-foreground">{fmtMoney(actual)}</span>}
              </span>
            ))}
          </div>
        </section>
      )}

      <BudgetSetupDialog open={setupOpen} onOpenChange={setSetupOpen} />
    </div>
  )
}
