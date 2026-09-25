import { useQuery } from '@tanstack/react-query'
import { ArrowDownLeft, ArrowUpRight, Download, TrendingUp, Wallet } from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { StatCard } from '@/components/StatCard'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { monthLabel, useMonth } from '@/hooks/useMonth'
import { api } from '@/lib/api'
import { fmtCop } from '@/lib/money'

const MONTH_SHORT = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

// Same tones as the Dashboard summary cards (emerald-500 / rose-500).
const INCOME_COLOR = '#10B981'
const EXPENSE_COLOR = '#F43F5E'
const BALANCE_COLOR = '#F59E0B'

// Compact axis labels so they fit the half-width panels.
function fmtAxis(value: number): string {
  const abs = Math.abs(value)
  if (abs >= 1_000_000) return `$${(value / 1_000_000).toFixed(1).replace('.', ',')}M`
  if (abs >= 1_000) return `$${Math.round(value / 1_000)}k`
  return `$${value}`
}

function Panel({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: React.ReactNode
}) {
  return (
    <div className="flex h-[28rem] flex-col rounded-2xl border border-border bg-card p-6 shadow-[0_4px_0_0_rgba(0,0,0,0.05)]">
      <h2 className="text-lg font-extrabold">{title}</h2>
      <p className="text-sm font-semibold text-muted-foreground">{subtitle}</p>
      <div className="mt-4 min-h-0 flex-1">{children}</div>
    </div>
  )
}

export function ReportsPage() {
  const { month } = useMonth()
  const yearly = useQuery({
    queryKey: ['yearly', month.year],
    queryFn: () => api.yearlySummaries(month.year),
  })
  const spending = useQuery({
    queryKey: ['categorySpending', month, 'expense'],
    queryFn: () => api.categorySpending(month.month, month.year, 'expense'),
  })
  const budgetVsActual = useQuery({
    queryKey: ['budgetVsActual', month],
    queryFn: () => api.budgetVsActual(month.month, month.year),
  })

  const monthly = yearly.data ?? []
  const chartData = monthly.map((s) => ({
    name: MONTH_SHORT[s.month - 1],
    Ingresos: Number(s.total_income),
    Gastos: Number(s.total_expense),
  }))
  const balanceData = monthly.map((s) => ({
    name: MONTH_SHORT[s.month - 1],
    Balance: Number(s.total_income) - Number(s.total_expense),
  }))
  const currentMonthIndex = month.month - 1

  const totalIncome = monthly.reduce((acc, s) => acc + Number(s.total_income), 0)
  const totalExpense = monthly.reduce((acc, s) => acc + Number(s.total_expense), 0)
  const totalBalance = totalIncome - totalExpense
  const activeMonths = monthly.filter(
    (s) => Number(s.total_income) !== 0 || Number(s.total_expense) !== 0,
  ).length
  const avgExpense = activeMonths > 0 ? totalExpense / activeMonths : 0

  const spendingRows = [...(spending.data ?? [])].sort((a, b) => Number(b.total) - Number(a.total))
  const maxSpending = Math.max(1, ...spendingRows.map((r) => Number(r.total)))
  const spendingTotal = spendingRows.reduce((acc, r) => acc + Number(r.total), 0)

  const budgetRows = (budgetVsActual.data ?? [])
    .filter((row) => Number(row.budget) > 0)
    .sort((a, b) => Number(b.percent) - Number(a.percent))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-extrabold">Reportes</h1>
          <p className="text-sm font-semibold text-muted-foreground">
            Análisis del año {month.year} · mes de {monthLabel(month)}
          </p>
        </div>
        <a href={api.exportCsvUrl(month.month, month.year)} download>
          <Button variant="outline" size="icon-sm" aria-label="Exportar CSV del mes">
            <Download />
          </Button>
        </a>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Ingresos del año"
          value={fmtCop(totalIncome)}
          icon={ArrowDownLeft}
          tone="income"
        />
        <StatCard
          title="Gastos del año"
          value={fmtCop(totalExpense)}
          icon={ArrowUpRight}
          tone="expense"
        />
        <StatCard
          title="Balance del año"
          value={fmtCop(totalBalance)}
          icon={Wallet}
          tone={totalBalance >= 0 ? 'income' : 'expense'}
        />
        <StatCard
          title="Promedio de gasto"
          value={fmtCop(avgExpense)}
          detail={activeMonths > 0 ? `por mes (${activeMonths} con movimientos)` : 'sin datos'}
          icon={TrendingUp}
          tone="primary"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title={`Ingresos vs gastos ${month.year}`} subtitle="El mes en curso aparece marcado">
          {yearly.isLoading ? (
            <Skeleton className="h-full w-full" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="name" />
                <YAxis tickFormatter={fmtAxis} width={56} />
                <Tooltip formatter={(value) => fmtCop(Number(value))} />
                <Legend />
                <ReferenceLine
                  x={MONTH_SHORT[currentMonthIndex]}
                  stroke="#94a3b8"
                  strokeDasharray="4 4"
                />
                <Bar
                  dataKey="Ingresos"
                  fill={INCOME_COLOR}
                  radius={[4, 4, 0, 0]}
                  isAnimationActive={false}
                />
                <Bar
                  dataKey="Gastos"
                  fill={EXPENSE_COLOR}
                  radius={[4, 4, 0, 0]}
                  isAnimationActive={false}
                />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Panel>

        <Panel title={`Balance mensual ${month.year}`} subtitle="Ingresos menos gastos de cada mes">
          {yearly.isLoading ? (
            <Skeleton className="h-full w-full" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={balanceData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="name" />
                <YAxis tickFormatter={fmtAxis} width={56} />
                <Tooltip formatter={(value) => fmtCop(Number(value))} />
                <ReferenceLine y={0} stroke="#94a3b8" />
                <Line
                  type="monotone"
                  dataKey="Balance"
                  stroke={BALANCE_COLOR}
                  strokeWidth={3}
                  dot={{ r: 4 }}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Panel>

        <Panel
          title="Gasto por categoría"
          subtitle={`${monthLabel(month)} · total ${fmtCop(spendingTotal)}`}
        >
          {spending.isLoading ? (
            <Skeleton className="h-full w-full" />
          ) : spendingRows.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              No hay gastos este mes.
            </div>
          ) : (
            <div className="h-full space-y-3 overflow-y-auto pr-1">
              {spendingRows.map((row) => {
                const total = Number(row.total)
                const percent = spendingTotal > 0 ? (total / spendingTotal) * 100 : 0
                return (
                  <div key={row.name} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-bold">
                        {row.icon} {row.name}
                      </span>
                      <span className="font-black">
                        {fmtCop(total)}
                        <span className="ml-2 text-xs font-bold text-muted-foreground">
                          {Math.round(percent)}%
                        </span>
                      </span>
                    </div>
                    <div className="h-2.5 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.max(2, (total / maxSpending) * 100)}%`,
                          backgroundColor: row.color || '#888',
                        }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </Panel>

        <Panel title="Presupuesto vs real" subtitle={`Ejecución de ${monthLabel(month)}`}>
          {budgetRows.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              No hay presupuestos este mes.
            </div>
          ) : (
            <div className="h-full overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Categoría</TableHead>
                    <TableHead className="text-right">Gastado</TableHead>
                    <TableHead className="w-28">Progreso</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {budgetRows.map((row) => (
                    <TableRow key={row.category_id}>
                      <TableCell className="font-medium">
                        {row.icon} {row.name}
                      </TableCell>
                      <TableCell className="text-right">
                        <span className="font-bold">{fmtCop(row.actual)}</span>
                        <span className="text-xs font-semibold text-muted-foreground">
                          {' '}
                          / {fmtCop(row.budget)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Progress
                            value={Math.min(row.percent, 100)}
                            className={`flex-1 ${row.percent > 100 ? '[&>div]:bg-red-500' : ''}`}
                          />
                          <span className="w-9 text-right text-xs font-bold text-muted-foreground">
                            {Math.round(row.percent)}%
                          </span>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </Panel>
      </div>
    </div>
  )
}
