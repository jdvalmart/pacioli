import { ArrowDownLeft, ArrowUpRight, ChevronRight, CreditCard, PiggyBank, Scale, Wallet } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

import { ACCOUNT_ICON } from '@/components/accountIcons'
import { SAVINGS_KIND_META } from '@/components/savingsKinds'
import { StatCard } from '@/components/StatCard'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { monthLabel, useMonth } from '@/hooks/useMonth'
import { budgetTotals } from '@/lib/budget'
import { fmtMoney } from '@/lib/money'
import {
  useAccounts,
  useBudgetVsActual,
  useCategorySpending,
  useCreditCards,
  useSavings,
  useSummary,
} from '@/lib/queries'
import { cn } from '@/lib/utils'

const fmtDay = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('es-CO', { day: 'numeric', month: 'short' })

function SeeAll({ to, label }: { to: string; label: string }) {
  return (
    <CardAction>
      <Link
        to={to}
        className="flex items-center gap-0.5 text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        {label}
        <ChevronRight className="size-4" />
      </Link>
    </CardAction>
  )
}

function EmptyLine({ children }: { children: React.ReactNode }) {
  return <p className="py-6 text-center text-sm text-muted-foreground">{children}</p>
}

export function DashboardPage() {
  const { month } = useMonth()
  const summary = useSummary(month)
  const spending = useCategorySpending(month)
  const budgetVsActual = useBudgetVsActual(month)
  const accounts = useAccounts()
  const savings = useSavings()
  const cards = useCreditCards(month)

  const accountList = accounts.data ?? []
  const accountsTotal = accountList.reduce((sum, account) => sum + Number(account.balance), 0)
  // Money moved to savings (pockets, CDTs, stocks) has left the accounts,
  // so it adds to net worth.
  const savingsList = savings.data ?? []
  const investedTotal = savingsList.reduce(
    (sum, item) => sum + Number(item.current_value ?? item.balance),
    0,
  )
  const netWorth = accountsTotal + investedTotal

  const chartData = (spending.data ?? []).map((row) => ({
    name: row.name,
    value: Number(row.total),
    color: row.color,
  }))
  const spendingTotal = chartData.reduce((sum, row) => sum + row.value, 0)

  // Same figures as the Budgets page (savings are a goal, not spending).
  const budget = budgetTotals(budgetVsActual.data ?? [], undefined, 0)
  const budgetRows = budget.categories.map((c) => c.row)
  const budgeted = budget.categories.reduce((sum, c) => sum + c.budget, 0)
  const budgetSpent = budget.categories.reduce((sum, c) => sum + c.spent, 0)
  const goal = budget.savings

  const balance = Number(summary.data?.balance ?? 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Resumen</h1>
        <p className="text-sm text-muted-foreground">{monthLabel(month)}</p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <StatCard
          title="Ingresos"
          value={fmtMoney(summary.data?.total_income ?? '0')}
          icon={ArrowDownLeft}
          tone="income"
        />
        <StatCard
          title="Gastos"
          value={fmtMoney(summary.data?.total_expense ?? '0')}
          icon={ArrowUpRight}
          tone="expense"
        />
        <StatCard
          title="Balance del mes"
          value={fmtMoney(balance)}
          valueClassName={balance < 0 ? 'text-negative' : undefined}
          detail={`Acumulado ${fmtMoney(summary.data?.accumulated_balance ?? '0')}`}
          icon={Scale}
          tone="primary"
        />
        <StatCard
          title="Patrimonio"
          value={fmtMoney(netWorth)}
          detail={`Cuentas ${fmtMoney(accountsTotal)} · Ahorros ${fmtMoney(investedTotal)}`}
          icon={PiggyBank}
          tone="neutral"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Main column: where the month's money goes */}
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Presupuestos</CardTitle>
              <CardDescription>
                {budgetRows.length > 0
                  ? `${fmtMoney(budgetSpent)} gastado de ${fmtMoney(budgeted)} presupuestado`
                  : 'Avance del gasto por categoría'}
              </CardDescription>
              <SeeAll to="/budgets" label="Ajustar" />
            </CardHeader>
            <CardContent>
              {budgetVsActual.isLoading ? (
                <Skeleton className="h-40 w-full" />
              ) : budgetRows.length === 0 ? (
                <EmptyLine>Sin presupuestos este mes. Defínelos en Presupuestos.</EmptyLine>
              ) : (
                <ul className="divide-y divide-border">
                  {budgetRows.map((row) => {
                    const over = row.percent > 100
                    return (
                      <li key={row.category_id} className="py-3 first:pt-0 last:pb-0">
                        <div className="flex items-baseline justify-between gap-3 text-sm">
                          <span className="flex min-w-0 items-center gap-2 font-medium">
                            <span
                              className="size-2 shrink-0 rounded-full"
                              style={{ backgroundColor: row.color || '#888' }}
                              aria-hidden
                            />
                            <span className="truncate">{row.name}</span>
                          </span>
                          <span className="shrink-0 text-muted-foreground">
                            <span className={cn('font-medium text-foreground', over && 'text-negative')}>
                              {fmtMoney(row.actual)}
                            </span>{' '}
                            de {fmtMoney(row.budget)}
                          </span>
                        </div>
                        <div className="mt-2 flex items-center gap-3">
                          <Progress
                            className="flex-1"
                            value={Math.min(row.percent, 100)}
                            indicatorClassName={over ? 'bg-negative' : undefined}
                          />
                          <span
                            className={cn(
                              'w-12 shrink-0 text-right text-xs font-medium',
                              over ? 'text-negative' : 'text-muted-foreground',
                            )}
                          >
                            {Math.round(row.percent)}%
                          </span>
                        </div>
                      </li>
                    )
                  })}
                </ul>
              )}
              {goal && goal.goal > 0 && (
                <div className="mt-4 flex items-center gap-3 rounded-lg bg-muted/50 px-3 py-2.5 text-sm">
                  <PiggyBank className="size-4 shrink-0 text-muted-foreground" />
                  <span className="min-w-0 flex-1">
                    Meta de ahorro:{' '}
                    <span className={cn('font-medium', goal.saved >= goal.goal && 'text-positive')}>
                      {fmtMoney(goal.saved)}
                    </span>{' '}
                    <span className="text-muted-foreground">de {fmtMoney(goal.goal)}</span>
                  </span>
                  <span className={cn('text-xs font-medium', goal.saved >= goal.goal ? 'text-positive' : 'text-muted-foreground')}>
                    {goal.saved >= goal.goal ? 'Cumplida' : `${Math.round(goal.percent)}%`}
                  </span>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Gasto por categoría</CardTitle>
              <CardDescription>
                {spendingTotal > 0 ? `Total ${fmtMoney(spendingTotal)}` : 'Desglose mensual del gasto'}
              </CardDescription>
              <SeeAll to="/reports" label="Reportes" />
            </CardHeader>
            <CardContent>
              {spending.isLoading ? (
                <Skeleton className="h-56 w-full" />
              ) : chartData.length === 0 ? (
                <EmptyLine>Aún no hay gastos este mes.</EmptyLine>
              ) : (
                <div className="grid items-center gap-6 sm:grid-cols-[14rem_1fr]">
                  <div className="mx-auto h-56 w-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={chartData}
                          dataKey="value"
                          nameKey="name"
                          innerRadius={62}
                          outerRadius={100}
                          paddingAngle={1.5}
                          stroke="var(--card)"
                          strokeWidth={2}
                        >
                          {chartData.map((entry) => (
                            <Cell key={entry.name} fill={entry.color || '#888'} />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(value) => fmtMoney(Number(value))}
                          contentStyle={{
                            background: 'var(--popover)',
                            border: '1px solid var(--border)',
                            borderRadius: 8,
                            color: 'var(--popover-foreground)',
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <ul className="space-y-2 text-sm">
                    {chartData.map((entry) => (
                      <li key={entry.name} className="flex items-center justify-between gap-3">
                        <span className="flex min-w-0 items-center gap-2">
                          <span
                            className="size-2.5 shrink-0 rounded-sm"
                            style={{ backgroundColor: entry.color || '#888' }}
                            aria-hidden
                          />
                          <span className="truncate">{entry.name}</span>
                        </span>
                        <span className="flex shrink-0 items-baseline gap-2">
                          <span className="font-medium">{fmtMoney(entry.value)}</span>
                          <span className="w-10 text-right text-xs text-muted-foreground">
                            {Math.round((entry.value / spendingTotal) * 100)}%
                          </span>
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Side column: where the money is */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Cuentas</CardTitle>
              <CardDescription>Total {fmtMoney(accountsTotal)}</CardDescription>
              <SeeAll to="/settings" label="Gestionar" />
            </CardHeader>
            <CardContent>
              {accountList.length === 0 ? (
                <EmptyLine>Todavía no tienes cuentas. Créalas en Ajustes.</EmptyLine>
              ) : (
                <ul className="space-y-3">
                  {accountList.map((account) => {
                    const Icon = ACCOUNT_ICON[account.type]
                    return (
                      <li key={account.id} className="flex items-center gap-3">
                        <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                          <Icon className="size-4" />
                        </span>
                        <span className="min-w-0 flex-1 truncate text-sm font-medium">
                          {account.name}
                        </span>
                        <span className="text-sm font-semibold">{fmtMoney(account.balance)}</span>
                      </li>
                    )
                  })}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Tarjetas de crédito</CardTitle>
              <CardDescription>Deuda y cupo disponible</CardDescription>
              <SeeAll to="/settings" label="Pagar" />
            </CardHeader>
            <CardContent>
              {(cards.data ?? []).length === 0 ? (
                <EmptyLine>Sin tarjetas registradas.</EmptyLine>
              ) : (
                <ul className="space-y-4">
                  {(cards.data ?? []).map((card) => {
                    const used =
                      Number(card.limit) > 0
                        ? (Number(card.outstanding) / Number(card.limit)) * 100
                        : 0
                    const due = Number(card.debt) > 0
                    return (
                      <li key={card.id} className="space-y-2">
                        <div className="flex items-center gap-3">
                          <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                            <CreditCard className="size-4" />
                          </span>
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-medium">{card.name}</p>
                            <p className="text-xs text-muted-foreground">
                              Pago {fmtDay(card.payment_date)}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-semibold">{fmtMoney(card.outstanding)}</p>
                            <p className="text-xs text-muted-foreground">deuda total</p>
                          </div>
                        </div>
                        <Progress value={Math.min(used, 100)} />
                        <div className="flex justify-between gap-2 text-xs text-muted-foreground">
                          <span>Disponible {fmtMoney(card.available)}</span>
                          {due ? (
                            <span className="font-medium text-negative">
                              Por pagar ya {fmtMoney(card.debt)}
                            </span>
                          ) : (
                            <span>Cuota {fmtMoney(card.pending)}</span>
                          )}
                        </div>
                      </li>
                    )
                  })}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Ahorro e inversión</CardTitle>
              <CardDescription>Total {fmtMoney(investedTotal)}</CardDescription>
              <SeeAll to="/settings" label="Gestionar" />
            </CardHeader>
            <CardContent>
              {savingsList.length === 0 ? (
                <EmptyLine>Sin bolsillos ni inversiones.</EmptyLine>
              ) : (
                <ul className="space-y-3">
                  {savingsList.map((item) => {
                    const value = Number(item.current_value ?? item.balance)
                    const target = item.target ? Number(item.target) : 0
                    return (
                      <li key={item.id} className="space-y-1.5">
                        <div className="flex items-center gap-3">
                          <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted text-base">
                            {SAVINGS_KIND_META[item.kind].icon}
                          </span>
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-medium">{item.name}</p>
                            <p className="text-xs text-muted-foreground">
                              {SAVINGS_KIND_META[item.kind].label}
                              {target > 0 && ` · meta ${fmtMoney(target)}`}
                            </p>
                          </div>
                          <span className="text-sm font-semibold">{fmtMoney(value)}</span>
                        </div>
                        {target > 0 && <Progress value={Math.min((value / target) * 100, 100)} />}
                      </li>
                    )
                  })}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card className="p-4">
            <Link to="/transactions" className="flex items-center justify-between text-sm font-medium">
              <span className="flex items-center gap-2">
                <Wallet className="size-4 text-muted-foreground" />
                Ver movimientos del mes
              </span>
              <ChevronRight className="size-4 text-muted-foreground" />
            </Link>
          </Card>
        </div>
      </div>
    </div>
  )
}
