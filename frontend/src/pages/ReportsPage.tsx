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
import { currentMonth, monthLabel, useMonth } from '@/hooks/useMonth'
import { CategoryIcon } from '@/components/CategoryIcon'
import { PageHeader } from '@/components/PageHeader'
import { Card } from '@/components/ui/card'
import { CHART, axisProps, tooltipProps } from '@/lib/chartTheme'
import { api } from '@/lib/api'
import { useBudgetVsActual, useCategorySpending, useYearlySummaries } from '@/lib/queries'
import { fmtMoney } from '@/lib/money'

const MONTH_SHORT = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']


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
    <Card className="h-[26rem] gap-4 p-5">
      <div>
        <h2 className="text-base font-semibold">{title}</h2>
        <p className="text-sm text-muted-foreground">{subtitle}</p>
      </div>
      <div className="min-h-0 flex-1">{children}</div>
    </Card>
  )
}

export function ReportsPage() {
  const { month } = useMonth()
  const yearly = useYearlySummaries(month.year)
  const spending = useCategorySpending(month, 'expense')
  const budgetVsActual = useBudgetVsActual(month)

  const monthly = yearly.data ?? []
  // Months that have not happened yet have no data: plot nothing, not $0.
  const thisMonth = currentMonth()
  const isFuture = (m: number) =>
    month.year > thisMonth.year || (month.year === thisMonth.year && m > thisMonth.month)
  const chartData = monthly.map((s) => ({
    name: MONTH_SHORT[s.month - 1],
    Ingresos: isFuture(s.month) ? null : Number(s.total_income),
    Gastos: isFuture(s.month) ? null : Number(s.total_expense),
  }))
  // A month with no movements at all has no balance to show (not $0).
  const hasActivity = (s: (typeof monthly)[number]) =>
    Number(s.total_income) !== 0 || Number(s.total_expense) !== 0
  const balanceData = monthly.map((s) => ({
    name: MONTH_SHORT[s.month - 1],
    Balance:
      isFuture(s.month) || !hasActivity(s) ? null : Number(s.total_income) - Number(s.total_expense),
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

  // The savings goal is not spending: it is not part of budget vs actual.
  const budgetRows = (budgetVsActual.data ?? [])
    .filter((row) => Number(row.budget) > 0 && row.role !== 'savings')
    .sort((a, b) => Number(b.percent) - Number(a.percent))

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reportes"
        description={`Año ${month.year} · detalle de ${monthLabel(month).toLowerCase()}`}
        action={
          <Button variant="outline" size="sm" render={<a href={api.exportCsvUrl(month.month, month.year)} download />}>
            <Download /> Exportar CSV
          </Button>
        }
      />

      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <StatCard
          title="Ingresos anuales"
          value={fmtMoney(totalIncome)}
          icon={ArrowDownLeft}
          tone="income"
        />
        <StatCard
          title="Gastos anuales"
          value={fmtMoney(totalExpense)}
          icon={ArrowUpRight}
          tone="expense"
        />
        <StatCard
          title="Balance anual"
          value={fmtMoney(totalBalance)}
          icon={Wallet}
          valueClassName={totalBalance < 0 ? 'text-negative' : undefined}
          tone={totalBalance >= 0 ? 'income' : 'expense'}
        />
        <StatCard
          title="Gasto promedio"
          value={fmtMoney(Math.round(avgExpense))}
          detail={activeMonths > 0 ? `por mes (${activeMonths} con movimientos)` : 'sin datos'}
          icon={TrendingUp}
          tone="primary"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={`Ingresos vs gastos ${month.year}`} subtitle="La línea punteada marca el mes elegido">
          {yearly.isLoading ? (
            <Skeleton className="h-full w-full" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} barGap={2} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke={CHART.grid} />
                <XAxis dataKey="name" {...axisProps} />
                <YAxis tickFormatter={fmtAxis} width={56} {...axisProps} />
                <Tooltip formatter={(value) => fmtMoney(Number(value))} {...tooltipProps} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
                <ReferenceLine
                  x={MONTH_SHORT[currentMonthIndex]}
                  stroke={CHART.reference}
                  strokeDasharray="4 4"
                />
                <Bar
                  dataKey="Ingresos"
                  fill={CHART.income}
                  radius={[3, 3, 0, 0]}
                  maxBarSize={18}
                  isAnimationActive={false}
                />
                <Bar
                  dataKey="Gastos"
                  fill={CHART.expense}
                  radius={[3, 3, 0, 0]}
                  maxBarSize={18}
                  isAnimationActive={false}
                />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Panel>

        <Panel title={`Balance mensual ${month.year}`} subtitle="Ingresos menos gastos por mes">
          {yearly.isLoading ? (
            <Skeleton className="h-full w-full" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={balanceData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke={CHART.grid} />
                <XAxis dataKey="name" {...axisProps} />
                <YAxis tickFormatter={fmtAxis} width={56} {...axisProps} />
                <Tooltip formatter={(value) => fmtMoney(Number(value))} {...tooltipProps} />
                <ReferenceLine y={0} stroke={CHART.reference} strokeOpacity={0.5} />
                <Line
                  type="linear"
                  dataKey="Balance"
                  stroke={CHART.balance}
                  strokeWidth={2}
                  dot={{ r: 3, strokeWidth: 0, fill: CHART.balance }}
                  activeDot={{ r: 5 }}
                  connectNulls={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Panel>

        <Panel
          title="Gasto por categoría"
          subtitle={`${monthLabel(month)} · total ${fmtMoney(spendingTotal)}`}
        >
          {spending.isLoading ? (
            <Skeleton className="h-full w-full" />
          ) : spendingRows.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              Sin gastos este mes.
            </div>
          ) : (
            <div className="h-full space-y-3 overflow-y-auto pr-1">
              {spendingRows.map((row) => {
                const total = Number(row.total)
                const percent = spendingTotal > 0 ? (total / spendingTotal) * 100 : 0
                return (
                  <div key={row.name} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="flex min-w-0 items-center gap-2 font-medium">
                        <CategoryIcon icon={row.icon} color={row.color} size="sm" />
                        <span className="truncate">{row.name}</span>
                      </span>
                      <span className="font-semibold">
                        {fmtMoney(total)}
                        <span className="ml-2 text-xs font-medium text-muted-foreground">
                          {Math.round(percent)}%
                        </span>
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-muted">
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

        <Panel title="Presupuesto vs real" subtitle={`Desempeño de ${monthLabel(month)}`}>
          {budgetRows.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              Sin presupuestos este mes.
            </div>
          ) : (
            <div className="h-full overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Categoría</TableHead>
                    <TableHead className="text-right">Gastado</TableHead>
                    <TableHead className="w-28">Avance</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {budgetRows.map((row) => (
                    <TableRow key={row.category_id}>
                      <TableCell className="font-medium">
                        <span className="flex items-center gap-2">
                          <CategoryIcon icon={row.icon} color={row.color} size="sm" />
                          {row.name}
                        </span>
                      </TableCell>
                      <TableCell className="text-right align-top">
                        <div className="font-medium tabular-nums">{fmtMoney(row.actual)}</div>
                        <div className="text-[11px] font-semibold text-muted-foreground tabular-nums">
                          de {fmtMoney(row.budget)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                            <Progress
                              value={Math.min(row.percent, 100)}
                              className="flex-1"
                              indicatorClassName={row.percent > 100 ? 'bg-negative' : undefined}
                            />
                          <span className="w-9 text-right text-xs font-medium text-muted-foreground">
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
