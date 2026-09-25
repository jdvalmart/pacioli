import { useQuery } from '@tanstack/react-query'
import { ArrowDownLeft, ArrowUpRight, Wallet } from 'lucide-react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { api } from '@/lib/api'
import { fmtCop, fmtCopDecimals } from '@/lib/money'
import { useMonth } from '@/hooks/useMonth'
import { AccountsSection } from '@/components/AccountsSection'
import { CreditCardsSection } from '@/components/CreditCardsSection'
import { SavingsSection } from '@/components/SavingsSection'
import { StatCard } from '@/components/StatCard'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'

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

  // Only categories with a defined budget appear on the dashboard;
  // categories with spending but no budget live in the Budgets page.
  // Highest budgets come first.
  const budgetCards = (budgetVsActual.data ?? [])
    .filter((row) => Number(row.budget) > 0)
    .sort((a, b) => Number(b.budget) - Number(a.budget))

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-extrabold">Overview</h1>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          title="Income"
          value={fmtCop(summary.data?.total_income ?? '0')}
          icon={ArrowDownLeft}
          tone="income"
        />
        <StatCard
          title="Expenses"
          value={fmtCop(summary.data?.total_expense ?? '0')}
          icon={ArrowUpRight}
          tone="expense"
        />
        <StatCard
          title="Accumulated balance"
          value={fmtCop(summary.data?.accumulated_balance ?? '0')}
          detail={`This month: ${fmtCop(summary.data?.balance ?? '0')}${
            Number(summary.data?.carryover ?? 0) !== 0
              ? ` · Carried over: ${fmtCop(summary.data?.carryover ?? '0')}`
              : ''
          }`}
          icon={Wallet}
          tone="primary"
        />
      </div>

      <AccountsSection readOnly />

      <CreditCardsSection readOnly />

      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-extrabold">Budgets</h2>
          <p className="text-sm font-semibold text-muted-foreground">
            Spending progress by category
          </p>
        </div>

        {budgetCards.length > 0 && (
          <div className="grid grid-cols-3 gap-3">
            {(() => {
              const totalBudget = budgetCards.reduce((sum, row) => sum + Number(row.budget), 0)
              const totalActual = budgetCards.reduce((sum, row) => sum + Number(row.actual), 0)
              const totalRemaining = totalBudget - totalActual
              return (
                <>
                  <div className="rounded-xl border border-border bg-card p-3 text-center shadow-[0_3px_0_0_rgba(0,0,0,0.05)]">
                    <p className="text-[11px] font-extrabold uppercase tracking-wide text-muted-foreground">
                      Budgeted
                    </p>
                    <p className="text-lg font-black">{fmtCop(totalBudget)}</p>
                  </div>
                  <div className="rounded-xl border border-border bg-card p-3 text-center shadow-[0_3px_0_0_rgba(0,0,0,0.05)]">
                    <p className="text-[11px] font-extrabold uppercase tracking-wide text-muted-foreground">
                      Spent
                    </p>
                    <p className="text-lg font-black text-rose-600">{fmtCop(totalActual)}</p>
                  </div>
                  <div className="rounded-xl border border-border bg-card p-3 text-center shadow-[0_3px_0_0_rgba(0,0,0,0.05)]">
                    <p className="text-[11px] font-extrabold uppercase tracking-wide text-muted-foreground">
                      Remaining
                    </p>
                    <p
                      className={`text-lg font-black ${
                        totalRemaining < 0 ? 'text-rose-600' : 'text-emerald-600'
                      }`}
                    >
                      {fmtCop(totalRemaining)}
                    </p>
                  </div>
                </>
              )
            })()}
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {budgetVsActual.isLoading ? (
            <>
              <Skeleton className="h-36 w-full" />
              <Skeleton className="h-36 w-full" />
              <Skeleton className="h-36 w-full" />
            </>
          ) : budgetCards.length === 0 ? (
            <Card className="col-span-full p-6 text-center text-sm font-semibold text-muted-foreground">
              No budgets this month. Set them up in the Budgets tab.
            </Card>
          ) : (
            budgetCards.map((row) => {
              const over = row.percent > 100
              return (
                <Card key={row.category_id} className="p-4">
                  <div className="flex items-center gap-3">
                    <div
                      className="flex size-11 items-center justify-center rounded-xl text-xl text-white shadow-[0_3px_0_0_rgba(0,0,0,0.25)]"
                      style={{ backgroundColor: row.color || '#888' }}
                    >
                      {row.icon}
                    </div>
                    <div>
                      <CardTitle className="text-sm leading-tight">{row.name}</CardTitle>
                      <p className="text-xs font-bold text-muted-foreground">
                        {Math.round(row.percent)}% used
                      </p>
                    </div>
                  </div>

                  <div className="mt-3 space-y-1.5">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-bold text-muted-foreground">
                        Spent {fmtCop(row.actual)}
                      </span>
                      <span className="font-black">{fmtCop(row.budget)}</span>
                    </div>
                    <Progress
                      value={Math.min(row.percent, 100)}
                      indicatorClassName={over ? 'bg-red-500' : undefined}
                    />
                    <p
                      className={`text-xs font-bold ${
                        over ? 'text-red-500' : 'text-muted-foreground'
                      }`}
                    >
                      {over
                        ? `Over by ${fmtCopDecimals(row.remaining.replace('-', ''))}`
                        : `Remaining ${fmtCopDecimals(row.remaining)}`}
                    </p>
                  </div>
                </Card>
              )
            })
          )}
        </div>
      </section>

      <SavingsSection readOnly />

      <Card>
        <CardHeader>
          <CardTitle>Spending by category</CardTitle>
          <CardDescription>Monthly spending breakdown</CardDescription>
        </CardHeader>
        <CardContent>
          {spending.isLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : chartData.length === 0 ? (
            <p className="py-20 text-center text-sm text-muted-foreground">
              No expenses yet this month.
            </p>
          ) : (
            <div className="grid gap-6 lg:grid-cols-2">
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

              <div className="flex items-center">
                <ul className="w-full space-y-2.5">
                  {chartData.map((entry) => (
                    <li
                      key={entry.name}
                      className="flex items-center justify-between gap-3 rounded-xl border border-border bg-background px-3 py-2"
                    >
                      <span className="flex min-w-0 items-center gap-2.5 font-bold">
                        <span
                          className="size-3.5 shrink-0 rounded-full"
                          style={{ backgroundColor: entry.color || '#8884d8' }}
                        />
                        <span className="truncate">{entry.name}</span>
                      </span>
                      <span className="shrink-0 font-black">{fmtCop(entry.value)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
