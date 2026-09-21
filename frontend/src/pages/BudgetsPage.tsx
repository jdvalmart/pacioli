import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { SlidersHorizontal } from 'lucide-react'
import { toast } from 'sonner'
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
import { Skeleton } from '@/components/ui/skeleton'
import { monthLabel, useMonth } from '@/hooks/useMonth'
import { api } from '@/lib/api'
import { fmtCop, fmtCopDecimals, normalizeAmount } from '@/lib/money'

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

  const [total, setTotal] = useState('')
  const [amounts, setAmounts] = useState<Record<string, string>>({})

  const expenseCategories = categories.data?.filter((c) => c.type === 'expense') ?? []

  // Initialize the form from the current budgets when it opens.
  const [initialized, setInitialized] = useState(false)
  if (open && !initialized && budgets.data) {
    const map: Record<string, string> = {}
    for (const b of budgets.data) {
      map[String(b.category_id)] = b.amount
    }
    setAmounts(map)
    setTotal(String(budgets.data.reduce((sum, b) => sum + Number(b.amount), 0)))
    setInitialized(true)
  }
  if (!open && initialized) {
    setInitialized(false)
  }

  const assigned = expenseCategories.reduce(
    (sum, cat) => sum + Number(normalizeAmount(amounts[String(cat.id)] || '0')),
    0,
  )
  const totalNum = Number(normalizeAmount(total || '0'))
  const pending = totalNum - assigned

  const hasPreviousBudgets = (previousBudgets.data ?? []).length > 0

  const copyPrevious = () => {
    const map: Record<string, string> = {}
    for (const b of previousBudgets.data ?? []) {
      map[String(b.category_id)] = b.amount
    }
    setAmounts(map)
    setTotal(String((previousBudgets.data ?? []).reduce((sum, b) => sum + Number(b.amount), 0)))
    toast.success('Presupuesto del mes anterior copiado')
  }

  const mutation = useMutation({
    mutationFn: () =>
      api.replaceBudgets({
        month: month.month,
        year: month.year,
        budgets: expenseCategories
          .filter((cat) => Number(normalizeAmount(amounts[String(cat.id)] || '0')) > 0)
          .map((cat) => ({
            category_id: cat.id,
            amount: normalizeAmount(amounts[String(cat.id)]),
          })),
      }),
    onSuccess: () => {
      toast.success('Presupuesto establecido')
      onOpenChange(false)
      void queryClient.invalidateQueries({ queryKey: ['budgets', month] })
      void queryClient.invalidateQueries({ queryKey: ['budgetVsActual', month] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto">
        {open && (
          <>
            <DialogHeader>
              <DialogTitle>Establecer presupuesto</DialogTitle>
              <DialogDescription>
                Define tu presupuesto total y repártelo por categorías para{' '}
                {monthLabel(month)}.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="budget-total">Mi presupuesto total</Label>
                <Input
                  id="budget-total"
                  placeholder="3.000.000"
                  className="text-lg font-black"
                  value={total}
                  onChange={(e) => setTotal(e.target.value)}
                />
              </div>

              <div className="flex items-center justify-between rounded-xl border-2 border-dashed border-primary/40 bg-primary/5 px-3 py-2 text-sm font-bold">
                <span>Asignado: {fmtCopDecimals(assigned)}</span>
                <span className={pending < 0 ? 'text-rose-600' : 'text-muted-foreground'}>
                  {pending >= 0
                    ? `Por asignar: ${fmtCopDecimals(pending)}`
                    : `Te pasaste por ${fmtCopDecimals(Math.abs(pending))}`}
                </span>
              </div>

              {hasPreviousBudgets && (
                <Button type="button" variant="outline" className="w-full" onClick={copyPrevious}>
                  📋 Copiar presupuesto del mes anterior
                </Button>
              )}

              <div className="space-y-3">
                {expenseCategories.map((cat) => (
                  <div key={cat.id} className="space-y-1.5">
                    <Label htmlFor={`budget-${cat.id}`} className="flex items-center gap-1.5">
                      <span>{cat.icon}</span> {cat.name}
                    </Label>
                    <Input
                      id={`budget-${cat.id}`}
                      placeholder="0"
                      value={amounts[String(cat.id)] ?? ''}
                      onChange={(e) =>
                        setAmounts((prev) => ({ ...prev, [String(cat.id)]: e.target.value }))
                      }
                    />
                  </div>
                ))}
              </div>

              <Button
                type="button"
                className="w-full"
                disabled={mutation.isPending || assigned <= 0}
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

  const [setupOpen, setSetupOpen] = useState(false)

  const expenseCategories = categories.data?.filter((c) => c.type === 'expense') ?? []
  const budgetByCategory = new Map((budgets.data ?? []).map((b) => [b.category_id, b.amount]))
  const actualByCategory = new Map(
    (budgetVsActual.data ?? []).map((row) => [row.category_id, row.actual]),
  )

  const totalBudget = (budgets.data ?? []).reduce((sum, b) => sum + Number(b.amount), 0)
  const totalActual = (budgetVsActual.data ?? []).reduce((sum, row) => sum + Number(row.actual), 0)
  const totalRemaining = totalBudget - totalActual
  const income = Number(summary.data?.total_income ?? 0)
  const unassigned = income - totalBudget

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

      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-xl border-2 border-border bg-card p-3 text-center shadow-[0_3px_0_0_rgba(0,0,0,0.05)]">
          <p className="text-[11px] font-extrabold uppercase tracking-wide text-muted-foreground">
            Presupuestado
          </p>
          <p className="text-lg font-black">{fmtCop(totalBudget)}</p>
        </div>
        <div className="rounded-xl border-2 border-border bg-card p-3 text-center shadow-[0_3px_0_0_rgba(0,0,0,0.05)]">
          <p className="text-[11px] font-extrabold uppercase tracking-wide text-muted-foreground">
            Gastado
          </p>
          <p className="text-lg font-black text-rose-600">{fmtCop(totalActual)}</p>
        </div>
        <div className="rounded-xl border-2 border-border bg-card p-3 text-center shadow-[0_3px_0_0_rgba(0,0,0,0.05)]">
          <p className="text-[11px] font-extrabold uppercase tracking-wide text-muted-foreground">
            Restante
          </p>
          <p
            className={`text-lg font-black ${
              totalRemaining < 0 ? 'text-rose-600' : 'text-emerald-600'
            }`}
          >
            {fmtCop(totalRemaining)}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border-2 border-dashed border-primary/40 bg-primary/5 px-4 py-3">
        <span className="text-sm font-bold">
          Ingresos del mes: <span className="text-emerald-600">{fmtCop(income)}</span>
        </span>
        <span
          className={`text-sm font-bold ${unassigned < 0 ? 'text-rose-600' : 'text-muted-foreground'}`}
        >
          {unassigned >= 0
            ? `Sin asignar: ${fmtCopDecimals(unassigned)}`
            : `Sobrepasaste tus ingresos por ${fmtCopDecimals(Math.abs(unassigned))}`}
        </span>
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
                      className={over ? '[&>div]:bg-red-500' : '[&>div]:bg-primary'}
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
