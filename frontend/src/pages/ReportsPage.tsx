import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
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

export function ReportsPage() {
  const { month } = useMonth()
  const yearly = useQuery({
    queryKey: ['yearly', month.year],
    queryFn: () => api.yearlySummaries(month.year),
  })
  const budgetVsActual = useQuery({
    queryKey: ['budgetVsActual', month],
    queryFn: () => api.budgetVsActual(month.month, month.year),
  })

  const chartData = (yearly.data ?? []).map((s) => ({
    name: MONTH_SHORT[s.month - 1],
    Ingresos: Number(s.total_income),
    Gastos: Number(s.total_expense),
  }))

  const totalIncome = (yearly.data ?? []).reduce((acc, s) => acc + Number(s.total_income), 0)
  const totalExpense = (yearly.data ?? []).reduce((acc, s) => acc + Number(s.total_expense), 0)
  const totalBalance = totalIncome - totalExpense

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-extrabold">Reportes</h1>
          <p className="text-sm font-semibold text-muted-foreground">
            Análisis del año {month.year}
          </p>
        </div>
        <a href={api.exportCsvUrl(month.month, month.year)} download>
          <Button variant="outline" size="icon-sm">
            <Download />
          </Button>
        </a>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border-2 border-border bg-card p-4 shadow-[0_4px_0_0_rgba(0,0,0,0.05)]">
          <p className="text-xs font-bold text-muted-foreground">Ingresos totales</p>
          <p className="mt-1 text-lg font-extrabold text-emerald-600">{fmtCop(totalIncome)}</p>
        </div>
        <div className="rounded-2xl border-2 border-border bg-card p-4 shadow-[0_4px_0_0_rgba(0,0,0,0.05)]">
          <p className="text-xs font-bold text-muted-foreground">Gastos totales</p>
          <p className="mt-1 text-lg font-extrabold text-red-600">{fmtCop(totalExpense)}</p>
        </div>
        <div className="rounded-2xl border-2 border-border bg-card p-4 shadow-[0_4px_0_0_rgba(0,0,0,0.05)]">
          <p className="text-xs font-bold text-muted-foreground">Balance del año</p>
          <p className={`mt-1 text-lg font-extrabold ${totalBalance >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
            {fmtCop(totalBalance)}
          </p>
        </div>
      </div>

      <div className="rounded-2xl border-2 border-border bg-card p-6 shadow-[0_4px_0_0_rgba(0,0,0,0.05)]">
        <h2 className="text-lg font-extrabold">Ingresos vs gastos {month.year}</h2>
        <p className="text-sm font-semibold text-muted-foreground">Resumen mensual de todo el año</p>
        {yearly.isLoading ? (
          <Skeleton className="mt-4 h-72 w-full" />
        ) : chartData.length === 0 ? (
          <div className="flex h-72 items-center justify-center text-sm text-muted-foreground">
            No hay datos para este año.
          </div>
        ) : (
          <div className="mt-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="name" />
                <YAxis tickFormatter={(v: number) => fmtCop(v)} width={90} />
                <Tooltip formatter={(value) => fmtCop(Number(value))} />
                <Legend />
                <Bar dataKey="Ingresos" fill="#10B981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Gastos" fill="#EF4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="rounded-2xl border-2 border-border bg-card p-6 shadow-[0_4px_0_0_rgba(0,0,0,0.05)]">
        <h2 className="text-lg font-extrabold">Presupuesto vs real</h2>
        <p className="text-sm font-semibold text-muted-foreground">
          Ejecución presupuestal de {monthLabel(month)}
        </p>
        <div className="mt-4">
          {budgetVsActual.data?.length === 0 ? (
            <div className="py-12 text-center text-sm text-muted-foreground">
              No hay presupuestos ni gastos este mes.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Categoría</TableHead>
                  <TableHead className="text-right">Presupuesto</TableHead>
                  <TableHead className="text-right">Gastado</TableHead>
                  <TableHead className="text-right">Restante</TableHead>
                  <TableHead className="w-40">Progreso</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {budgetVsActual.data
                  ?.sort((a, b) => Number(b.percent) - Number(a.percent))
                  .map((row) => (
                    <TableRow key={row.category_id}>
                      <TableCell className="font-medium">
                        {row.icon} {row.name}
                      </TableCell>
                      <TableCell className="text-right">{fmtCop(row.budget)}</TableCell>
                      <TableCell className="text-right">{fmtCop(row.actual)}</TableCell>
                      <TableCell
                        className={`text-right ${
                          row.budget !== '0.00' && Number(row.remaining) < 0
                            ? 'font-bold text-red-500'
                            : 'text-muted-foreground'
                        }`}
                      >
                        {row.budget !== '0.00' ? fmtCop(row.remaining) : '—'}
                      </TableCell>
                      <TableCell>
                        {row.budget !== '0.00' ? (
                          <div className="flex items-center gap-2">
                            <Progress
                              value={Math.min(row.percent, 100)}
                              className={`flex-1 ${row.percent > 100 ? '[&>div]:bg-red-500' : ''}`}
                            />
                            <span className="w-10 text-right text-xs font-bold text-muted-foreground">
                              {row.percent}%
                            </span>
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground">Sin presupuesto</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          )}
        </div>
      </div>
    </div>
  )
}
