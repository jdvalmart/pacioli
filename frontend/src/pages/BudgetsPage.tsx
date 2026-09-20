import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Save, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { useMonth } from '@/hooks/useMonth'
import { api } from '@/lib/api'
import { fmtCop, normalizeAmount } from '@/lib/money'

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

  const [drafts, setDrafts] = useState<Record<string, string>>({})

  const expenseCategories = categories.data?.filter((c) => c.type === 'expense') ?? []
  const budgetByCategory = new Map(
    (budgets.data ?? []).map((b) => [b.category_id, b.amount]),
  )
  const actualByCategory = new Map(
    (budgetVsActual.data ?? []).map((row) => [row.category_id, row.actual]),
  )

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
        <h1 className="text-xl font-semibold">Presupuestos</h1>
        <p className="text-sm text-muted-foreground">
          Define cuánto puedes gastar por categoría cada mes
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {budgets.isLoading || categories.isLoading ? (
          <>
            <Skeleton className="h-28 w-full" />
            <Skeleton className="h-28 w-full" />
            <Skeleton className="h-28 w-full" />
            <Skeleton className="h-28 w-full" />
          </>
        ) : (
          expenseCategories.map((category) => {
            const current = budgetByCategory.get(category.id) ?? ''
            const actual = actualByCategory.get(category.id) ?? '0'
            const draft = drafts[String(category.id)] ?? current
            const hasBudget = current !== '' && Number(current) > 0
            const percent = hasBudget ? (Number(actual) / Number(current)) * 100 : 0

            return (
              <Card key={category.id}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">
                    {category.icon} {category.name}
                  </CardTitle>
                  <CardDescription>
                    {hasBudget
                      ? `Gastado ${fmtCop(actual)} de ${fmtCop(current)}`
                      : `Gastado ${fmtCop(actual)} — sin presupuesto`}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {hasBudget && (
                    <Progress
                      value={Math.min(percent, 100)}
                      className={percent > 100 ? '[&>div]:bg-red-500' : ''}
                    />
                  )}
                  <div className="flex gap-2">
                    <Input
                      placeholder="Ej. 1.000.000"
                      value={draft}
                      onChange={(e) =>
                        setDrafts((prev) => ({ ...prev, [String(category.id)]: e.target.value }))
                      }
                    />
                    <Button onClick={() => handleSave(category.id)} disabled={saveMutation.isPending}>
                      <Save />
                    </Button>
                    {hasBudget && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => deleteMutation.mutate(category.id)}
                      >
                        <Trash2 className="text-red-500" />
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })
        )}
      </div>
    </div>
  )
}
