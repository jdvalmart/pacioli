import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Save, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { monthLabel, useMonth } from '@/hooks/useMonth'
import { api } from '@/lib/api'
import { fmtCop, fmtCopDecimals, normalizeAmount } from '@/lib/money'

export function BudgetsPage() {
  const { month } = useMonth()
  const queryClient = useQueryClient()
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

  const [drafts, setDrafts] = useState<Record<string, string>>({})

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

  const saveMutation = useMutation({
    mutationFn: ({ categoryId, amount }: { categoryId: number; amount: string }) =>
      api.upsertBudget({ category_id: categoryId, month: month.month, year: month.year, amount }),
    onSuccess: () => {
      toast.success('Presupuesto guardado')
      void queryClient.invalidateQueries({ queryKey: ['budgets', month] })
      void queryClient.invalidateQueries({ queryKey: ['budgetVsActual', month] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (categoryId: number) => api.deleteBudget(categoryId, month.month, month.year),
    onSuccess: () => {
      toast.success('Presupuesto eliminado')
      void queryClient.invalidateQueries({ queryKey: ['budgets', month] })
      void queryClient.invalidateQueries({ queryKey: ['budgetVsActual', month] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const handleSave = (categoryId: number) => {
    const draft = drafts[String(categoryId)]
    if (!draft || draft.trim() === '') {
      toast.error('Ingresa un monto')
      return
    }
    saveMutation.mutate({ categoryId, amount: normalizeAmount(draft) })
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-extrabold">Presupuestos</h1>
        <p className="text-sm font-semibold text-muted-foreground">
          Establece cuánto puedes gastar por categoría en {monthLabel(month)}
        </p>
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
          expenseCategories.map((category) => {
            const current = budgetByCategory.get(category.id) ?? ''
            const actual = actualByCategory.get(category.id) ?? '0'
            const draft = drafts[String(category.id)] ?? current
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
                        : `Gastado ${fmtCop(actual)}`}
                    </p>
                  </div>
                  {hasBudget && (
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      onClick={() => deleteMutation.mutate(category.id)}
                    >
                      <Trash2 className="size-3.5 text-destructive" />
                    </Button>
                  )}
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

                <div className="mt-3 flex gap-2">
                  <Input
                    placeholder="Ej. 800.000"
                    value={draft}
                    onChange={(e) =>
                      setDrafts((prev) => ({ ...prev, [String(category.id)]: e.target.value }))
                    }
                  />
                  <Button
                    size="icon"
                    aria-label={`Guardar presupuesto de ${category.name}`}
                    onClick={() => handleSave(category.id)}
                    disabled={saveMutation.isPending}
                  >
                    <Save />
                  </Button>
                </div>
              </Card>
            )
          })
        )}
      </div>
    </div>
  )
}
