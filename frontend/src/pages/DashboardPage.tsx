import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ArrowDownLeft, ArrowUpRight, Plus, Wallet } from 'lucide-react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { api } from '@/lib/api'
import { fmtCop, fmtCopDecimals } from '@/lib/money'
import { useMonth } from '@/hooks/useMonth'
import { AccountsSection } from '@/components/AccountsSection'
import { CreditCardsSection } from '@/components/CreditCardsSection'
import { SavingsSection } from '@/components/SavingsSection'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'

function SummaryCard({
  title,
  value,
  detail,
  icon: Icon,
  tone,
}: {
  title: string
  value: string
  detail?: string
  icon: typeof Wallet
  tone: 'income' | 'expense' | 'neutral'
}) {
  const circleClass =
    tone === 'income'
      ? 'bg-emerald-500 shadow-[0_4px_0_0_#059669]'
      : tone === 'expense'
        ? 'bg-rose-500 shadow-[0_4px_0_0_#e11d48]'
        : 'bg-primary shadow-[0_4px_0_0_color-mix(in_oklch,var(--primary),black_18%)]'
  return (
    <Card className="flex-row items-center gap-4 p-5">
      <div
        className={`flex size-14 shrink-0 items-center justify-center rounded-2xl text-white ${circleClass}`}
      >
        <Icon className="size-7" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-extrabold uppercase tracking-wider text-muted-foreground">
          {title}
        </p>
        <p className="truncate text-2xl font-black">{value}</p>
        {detail && <p className="text-xs font-bold text-muted-foreground">{detail}</p>}
      </div>
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
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-extrabold">Resumen</h1>
        <Link to="/transactions?new=1">
          <Button>
            <Plus /> Nueva transacción
          </Button>
        </Link>
      </div>

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
          title="Balance acumulado"
          value={fmtCop(summary.data?.accumulated_balance ?? '0')}
          detail={`Este mes: ${fmtCop(summary.data?.balance ?? '0')}${
            Number(summary.data?.carryover ?? 0) !== 0
              ? ` · Arrastrado: ${fmtCop(summary.data?.carryover ?? '0')}`
              : ''
          }`}
          icon={Wallet}
          tone="neutral"
        />
      </div>

      <AccountsSection />

      <CreditCardsSection />

      <Card>
        <CardHeader>
          <CardTitle>Presupuesto vs real</CardTitle>
          <CardDescription>Progreso de cada presupuesto del mes</CardDescription>
        </CardHeader>
        <CardContent>
          {budgetVsActual.isLoading ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : budgetVsActual.data?.length === 0 ? (
            <p className="py-16 text-center text-sm text-muted-foreground">
              Sin presupuestos este mes. Defínelos en la pestaña Presupuestos.
            </p>
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {budgetVsActual.data?.map((row) => (
                <div key={row.category_id} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-bold">
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
                    <p className="text-xs font-bold text-red-500">
                      Sobrepasado por {fmtCopDecimals(row.remaining.replace('-', ''))}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <SavingsSection />

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
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={70}
                    outerRadius={110}
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
    </div>
  )
}
