import { useQuery } from '@tanstack/react-query'
import { ArrowDownLeft, ArrowUpRight, Wallet } from 'lucide-react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { api } from '@/lib/api'
import { fmtCop, fmtCopDecimals } from '@/lib/money'
import { useMonth } from '@/hooks/useMonth'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'

function SummaryCard({
  title,
  value,
  icon: Icon,
  tone,
}: {
  title: string
  value: string
  icon: typeof Wallet
  tone: 'income' | 'expense' | 'neutral'
}) {
  const iconClass =
    tone === 'income'
      ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400'
      : tone === 'expense'
        ? 'bg-red-100 text-red-600 dark:bg-red-950 dark:text-red-400'
        : 'bg-blue-100 text-blue-600 dark:bg-blue-950 dark:text-blue-400'
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <div className={`rounded-lg p-2 ${iconClass}`}>
          <Icon className="size-4" />
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-bold">{value}</p>
      </CardContent>
    </Card>
  )
}

export function DashboardPage() {
  const { month } = useMonth()
  const summary = useQuery({
    queryKey: ['summary', month],
    queryFn: () => api.summary(month.month, month.year),
  })
  const spending = useQuery({
    queryKey: ['categorySpending', month],
    queryFn: () => api.categorySpending(month.month, month.year),
  })
  const budgetVsActual = useQuery({
    queryKey: ['budgetVsActual', month],
    queryFn: () => api.budgetVsActual(month.month, month.year),
  })

  const chartData = (spending.data ?? []).map((row) => ({
    name: row.name,
    value: Number(row.total),
    color: row.color,
  }))

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <SummaryCard
          title="Ingresos"
          value={fmtCop(summary.data?.total_income ?? '0')}
          icon={ArrowDownLeft}
          tone="income"
        />
        <SummaryCard
          title="Gastos"
          value={fmtCop(summary.data?.total_expense ?? '0')}
          icon={ArrowUpRight}
          tone="expense"
        />
        <SummaryCard
          title="Balance"
          value={fmtCop(summary.data?.balance ?? '0')}
          icon={Wallet}
          tone="neutral"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Gasto por categoría</CardTitle>
            <CardDescription>Distribución del gasto del mes</CardDescription>
          </CardHeader>
          <CardContent>
            {spending.isLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : chartData.length === 0 ? (
              <p className="py-20 text-center text-sm text-muted-foreground">
                No hay gastos este mes todavía.
              </p>
            ) : (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={chartData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={55}
                      outerRadius={90}
                      paddingAngle={2}
                    >
                      {chartData.map((entry) => (
                        <Cell key={entry.name} fill={entry.color || '#8884d8'} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => fmtCop(Number(value))} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Presupuesto vs real</CardTitle>
            <CardDescription>Progreso de cada presupuesto del mes</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {budgetVsActual.isLoading ? (
              <>
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </>
            ) : budgetVsActual.data?.length === 0 ? (
              <p className="py-16 text-center text-sm text-muted-foreground">
                Sin presupuestos este mes. Defínelos en la pestaña Presupuestos.
              </p>
            ) : (
              budgetVsActual.data?.map((row) => (
                <div key={row.category_id} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">
                      {row.icon} {row.name}
                    </span>
                    <span className="text-muted-foreground">
                      {fmtCop(row.actual)} / {fmtCop(row.budget)}
                    </span>
                  </div>
                  <Progress
                    value={Math.min(row.percent, 100)}
                    className={row.percent > 100 ? '[&>div]:bg-red-500' : ''}
                  />
                  {row.percent > 100 && (
                    <p className="text-xs text-red-500">
                      Sobrepasado por {fmtCopDecimals(row.remaining.replace('-', ''))}
                    </p>
                  )}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
