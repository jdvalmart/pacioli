import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { ArrowUpRight, PieChart, PiggyBank, SlidersHorizontal, Wallet } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
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
import { api } from '@/lib/api'
import { fmtCop, fmtCopDecimals, normalizeAmount } from '@/lib/money'
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
      <span className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-sm font-bold text-muted-foreground">
        $
      </span>
      <Input
        id={id}
        inputMode="numeric"
        autoComplete="off"
        placeholder={placeholder}
        className="pl-7 text-right font-bold tabular-nums"
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
        className="flex size-9 shrink-0 items-center justify-center rounded-lg text-base text-white shadow-[0_2px_0_0_rgba(0,0,0,0.2)]"
        style={{ backgroundColor: category.color || '#888' }}
      >
        {category.icon}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-bold">{category.name}</p>
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
  const queryClient = useQueryClient()
  const categories = useQuery({ queryKey: ['categories'], queryFn: () => api.listCategories() })
  const budgets = useQuery({
    queryKey: ['budgets', month],
    queryFn: () => api.listBudgets(month.month, month.year),
  })

  // Previous month (for the copy action).
  const prevDate = new Date(month.year, month.month - 2, 1)
  const prevMonth = { month: prevDate.getMonth() + 1, year: prevDate.getFullYear() }
  const previousBudgets = useQuery({
    queryKey: ['budgets', prevMonth],
    queryFn: () => api.listBudgets(prevMonth.month, prevMonth.year),
    enabled: open,
  })
  const summary = useQuery({
    queryKey: ['summary', month],
    queryFn: () => api.summary(month.month, month.year),
    enabled: open,
  })
  const plan = useQuery({
    queryKey: ['budgetPlan', month],
    queryFn: () => api.getBudgetPlan(month.month, month.year),
    enabled: open,
  })

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
    toast.success('Presupuesto del mes anterior copiado')
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
      toast.success('Presupuesto establecido')
      onOpenChange(false)
      void queryClient.invalidateQueries({ queryKey: ['budgets', month] })
      void queryClient.invalidateQueries({ queryKey: ['budgetVsActual', month] })
      void queryClient.invalidateQueries({ queryKey: ['budgetPlan', month] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[88vh] overflow-y-auto sm:max-w-lg">
        {open && (
          <>
            <DialogHeader>
              <DialogTitle>Establecer presupuesto</DialogTitle>
              <DialogDescription>
                Planifica tus gastos de {monthLabel(month)}: reparte tu presupuesto total entre
                las categorías.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-5">
              <div className="space-y-1.5">
                <Label htmlFor="budget-total">Mi presupuesto total</Label>
                <MoneyInput id="budget-total" value={total} onChange={setTotal} placeholder="3.000.000" />
                <p className="text-xs font-semibold text-muted-foreground">
                  Por defecto usamos tu ingreso del mes: {fmtCop(Number(summary.data?.total_income ?? 0))}
                </p>
              </div>

              <div className="rounded-2xl border border-border bg-muted/40 p-4">
                <div className="grid grid-cols-2 gap-2 text-center">
                  <div>
                    <p className="text-[10px] font-extrabold tracking-wide text-muted-foreground uppercase">
                      Asignado
                    </p>
                    <p className="text-sm font-black">{fmtCop(assigned)}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-extrabold tracking-wide text-muted-foreground uppercase">
                      Sin asignar
                    </p>
                    <p
                      className={cn(
                        'text-sm font-black',
                        pending < 0
                          ? 'text-rose-600'
                          : pending > 0
                            ? 'text-amber-600'
                            : 'text-emerald-600',
                      )}
                    >
                      {fmtCop(pending)}
                    </p>
                  </div>
                </div>
                <Progress
                  value={usedPercent}
                  className="mt-3"
                  indicatorClassName={pending < 0 ? 'bg-rose-500' : undefined}
                />
                {pending < 0 && (
                  <p className="mt-2 text-xs font-bold text-rose-600">
                    Te pasaste por {fmtCopDecimals(Math.abs(pending))}
                  </p>
                )}
              </div>

              {hasPreviousBudgets && (
                <Button type="button" variant="outline" className="w-full" onClick={copyPrevious}>
                  📋 Copiar presupuesto del mes anterior
                </Button>
              )}

              <div className="space-y-3">
                <p className="text-[11px] font-extrabold tracking-wide text-muted-foreground uppercase">
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
  const categories = useQuery({ queryKey: ['categories'], queryFn: () => api.listCategories() })
  const budgets = useQuery({
    queryKey: ['budgets', month],
    queryFn: () => api.listBudgets(month.month, month.year),
  })
  const budgetVsActual = useQuery({
    queryKey: ['budgetVsActual', month],
    queryFn: () => api.budgetVsActual(month.month, month.year),
  })
  const summary = useQuery({
    queryKey: ['summary', month],
    queryFn: () => api.summary(month.month, month.year),
  })
  const plan = useQuery({
    queryKey: ['budgetPlan', month],
    queryFn: () => api.getBudgetPlan(month.month, month.year),
  })

  const [setupOpen, setSetupOpen] = useState(false)

  const expenseCategories = categories.data?.filter((c) => c.type === 'expense') ?? []
  const budgetByCategory = new Map((budgets.data ?? []).map((b) => [b.category_id, b.amount]))
  const actualByCategory = new Map(
    (budgetVsActual.data ?? []).map((row) => [row.category_id, row.actual]),
  )

  const totalBudget = (budgets.data ?? []).reduce((sum, b) => sum + Number(b.amount), 0)
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-extrabold">Presupuestos</h1>
          <p className="text-sm font-semibold text-muted-foreground">
            Establece cuánto puedes gastar por categoría en {monthLabel(month)}
          </p>
        </div>
        <Button onClick={() => setSetupOpen(true)}>
          <SlidersHorizontal /> Establecer presupuesto
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Presupuesto total" value={fmtCop(planTotal)} icon={Wallet} tone="primary" />
        <StatCard title="Asignado" value={fmtCop(totalBudget)} icon={PieChart} tone="neutral" />
        <StatCard title="Gastado" value={fmtCop(totalActual)} icon={ArrowUpRight} tone="expense" />
        <StatCard
          title="Restante"
          value={fmtCop(totalRemaining)}
          icon={PiggyBank}
          tone={totalRemaining < 0 ? 'expense' : 'income'}
        />
      </div>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-1 rounded-xl border border-dashed border-primary/40 bg-primary/5 px-4 py-3">
        <span
          className={`text-sm font-bold ${
            unassigned < 0
              ? 'text-rose-600'
              : unassigned > 0
                ? 'text-amber-600'
                : 'text-emerald-600'
          }`}
        >
          {unassigned > 0
            ? `Sin asignar: ${fmtCop(unassigned)} (falta repartirlo entre categorías)`
            : unassigned < 0
              ? `Te pasaste del presupuesto total por ${fmtCop(Math.abs(unassigned))}`
              : 'Todo el presupuesto está asignado ✓'}
        </span>
        {unbudgeted > 0 && (
          <span className="text-sm font-bold text-muted-foreground">
            Gastado sin presupuesto: <span className="text-rose-600">{fmtCop(unbudgeted)}</span>
          </span>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {budgets.isLoading || categories.isLoading ? (
          <>
            <Skeleton className="h-44 w-full" />
            <Skeleton className="h-44 w-full" />
            <Skeleton className="h-44 w-full" />
          </>
        ) : (
          [...expenseCategories]
            .sort((a, b) => {
              const budgetA = Number(budgetByCategory.get(a.id) ?? 0)
              const budgetB = Number(budgetByCategory.get(b.id) ?? 0)
              if (budgetA !== budgetB) return budgetB - budgetA
              return Number(actualByCategory.get(b.id) ?? 0) - Number(actualByCategory.get(a.id) ?? 0)
            })
            .map((category) => {
            const current = budgetByCategory.get(category.id) ?? ''
            const actual = actualByCategory.get(category.id) ?? '0'
            const hasBudget = current !== '' && Number(current) > 0
            const percent = hasBudget ? (Number(actual) / Number(current)) * 100 : 0
            const over = percent > 100
            const remaining = Number(current) - Number(actual)

            return (
              <Card key={category.id} className="p-4">
                <div className="flex items-center gap-3">
                  <div
                    className="flex size-11 items-center justify-center rounded-xl text-xl text-white shadow-[0_3px_0_0_rgba(0,0,0,0.25)]"
                    style={{ backgroundColor: category.color || '#888' }}
                  >
                    {category.icon}
                  </div>
                  <div className="min-w-0 flex-1">
                    <CardTitle className="text-sm leading-tight">{category.name}</CardTitle>
                    <p className="text-xs font-bold text-muted-foreground">
                      {hasBudget
                        ? `Gastado ${fmtCop(actual)} de ${fmtCop(current)}`
                        : 'Sin presupuesto asignado'}
                    </p>
                  </div>
                </div>

                {hasBudget && (
                  <div className="mt-3 space-y-1">
                    <Progress
                      value={Math.min(percent, 100)}
                      indicatorClassName={over ? 'bg-red-500' : undefined}
                    />
                    <p
                      className={`text-xs font-bold ${
                        over ? 'text-red-500' : 'text-muted-foreground'
                      }`}
                    >
                      {over
                        ? `Sobrepasado por ${fmtCopDecimals(Math.abs(remaining))}`
                        : `Restante ${fmtCopDecimals(remaining)}`}
                    </p>
                  </div>
                )}
              </Card>
            )
          })
        )}
      </div>

      <BudgetSetupDialog open={setupOpen} onOpenChange={setSetupOpen} />
    </div>
  )
}
