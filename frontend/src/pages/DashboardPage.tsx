import { useQuery } from '@tanstack/react-query'
import { ArrowDownLeft, ArrowUpRight, Landmark, PiggyBank, Wallet } from 'lucide-react'
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
  const accounts = useQuery({ queryKey: ['accounts'], queryFn: api.listAccounts })
  const savings = useQuery({ queryKey: ['savings'], queryFn: api.listSavings })

  const accountsTotal = (accounts.data ?? []).reduce(
    (sum, account) => sum + Number(account.balance),
    0,
  )
  // Pocket money already sits inside the accounts; only programmed
  // savings, CDTs and stocks have left them, so they add to net worth.
  const investedTotal = (savings.data ?? [])
    .filter((item) => item.kind !== 'bolsillo')
    .reduce(
      (sum, item) =>
        sum + (item.current_value != null ? Number(item.current_value) : Number(item.balance)),
      0,
    )
  const netWorth = accountsTotal + investedTotal

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
      <h1 className="text-xl font-extrabold">Resumen</h1>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        <StatCard
          title="Ingresos"
          value={fmtCop(summary.data?.total_income ?? '0')}
          icon={ArrowDownLeft}
          tone="income"
        />
        <StatCard
          title="Gastos"
          value={fmtCop(summary.data?.total_expense ?? '0')}
          icon={ArrowUpRight}
          tone="expense"
        />
        <StatCard
          title="Balance del mes"
          value={fmtCop(summary.data?.balance ?? '0')}
          detail={`Acumulado: ${fmtCop(summary.data?.accumulated_balance ?? '0')}`}
          icon={Wallet}
          tone="primary"
        />
        <StatCard
          title="En cuentas"
          value={fmtCop(accountsTotal)}
          detail="Efectivo disponible"
          icon={Landmark}
          tone="neutral"
        />
        <StatCard
          title="Patrimonio"
          value={fmtCop(netWorth)}
          detail="Cuentas + ahorros e inversiones"
          icon={PiggyBank}
          tone="income"
        />
      </div>

      <AccountsSection readOnly />

      <CreditCardsSection readOnly />

      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-extrabold">Presupuestos</h2>
          <p className="text-sm font-semibold text-muted-foreground">
            Avance del gasto por categoría
          </p>
        </div>

        {budgetCards.length > 0 && (
          <div className="grid grid-cols-3 gap-3">
            {(() => {
              const totalBudget = budgetCards.reduce((sum, row) => sum + Number(row.budget), 0)
              const totalActual = budgetCards.reduce((sum, row) => sum + Number(row.actual), 0)
              const totalRestante = totalBudget - totalActual
              return (
                <>
                  <div className="rounded-xl border border-border bg-card p-3 text-center shadow-[0_3px_0_0_rgba(0,0,0,0.05)]">
                    <p className="text-[11px] font-extrabold uppercase tracking-wide text-muted-foreground">
                      Presupuestado
                    </p>
                    <p className="text-lg font-black">{fmtCop(totalBudget)}</p>
                  </div>
                  <div className="rounded-xl border border-border bg-card p-3 text-center shadow-[0_3px_0_0_rgba(0,0,0,0.05)]">
                    <p className="text-[11px] font-extrabold uppercase tracking-wide text-muted-foreground">
                      Gastado
                    </p>
                    <p className="text-lg font-black text-rose-600">{fmtCop(totalActual)}</p>
                  </div>
                  <div className="rounded-xl border border-border bg-card p-3 text-center shadow-[0_3px_0_0_rgba(0,0,0,0.05)]">
                    <p className="text-[11px] font-extrabold uppercase tracking-wide text-muted-foreground">
                      Restante
                    </p>
                    <p
                      className={`text-lg font-black ${
                        totalRestante < 0 ? 'text-rose-600' : 'text-emerald-600'
                      }`}
                    >
                      {fmtCop(totalRestante)}
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
              Sin presupuestos este mes. Configúralos en la pestaña Presupuestos.
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
                        {Math.round(row.percent)}% usado
                      </p>
                    </div>
                  </div>

                  <div className="mt-3 space-y-1.5">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-bold text-muted-foreground">
                        Gastado {fmtCop(row.actual)}
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
                        ? `Te pasaste ${fmtCopDecimals(row.remaining.replace('-', ''))}`
                        : `Restante ${fmtCopDecimals(row.remaining)}`}
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
          <CardTitle>Gasto por categoría</CardTitle>
          <CardDescription>Desglose mensual del gasto</CardDescription>
        </CardHeader>
        <CardContent>
          {spending.isLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : chartData.length === 0 ? (
            <p className="py-20 text-center text-sm text-muted-foreground">
              Aún no hay gastos este mes.
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
