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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
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
import { useMonth } from '@/hooks/useMonth'
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Reportes</h1>
          <p className="text-sm text-muted-foreground">Análisis del año {month.year}</p>
        </div>
        <a href={api.exportCsvUrl(month.month, month.year)} download>
          <Button variant="outline">
            <Download /> Exportar CSV del mes
          </Button>
        </a>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Ingresos vs gastos {month.year}</CardTitle>
          <CardDescription>Resumen mensual de todo el año</CardDescription>
        </CardHeader>
        <CardContent>
          {yearly.isLoading ? (
            <Skeleton className="h-72 w-full" />
          ) : (
            <div className="h-72">
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
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Presupuesto vs real</CardTitle>
          <CardDescription>Detalle de ejecución presupuestal del mes</CardDescription>
        </CardHeader>
        <CardContent>
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
              {budgetVsActual.data?.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
                    No hay presupuestos ni gastos este mes.
                  </TableCell>
                </TableRow>
              )}
              {budgetVsActual.data?.map((row) => (
                <TableRow key={row.category_id}>
                  <TableCell>
                    {row.icon} {row.name}
                  </TableCell>
                  <TableCell className="text-right">{fmtCop(row.budget)}</TableCell>
                  <TableCell className="text-right">{fmtCop(row.actual)}</TableCell>
                  <TableCell
                    className={`text-right ${
                      row.budget !== '0.00' && Number(row.remaining) < 0
                        ? 'text-red-500'
                        : 'text-muted-foreground'
                    }`}
                  >
                    {row.budget !== '0.00' ? fmtCop(row.remaining) : '—'}
                  </TableCell>
                  <TableCell>
                    {row.budget !== '0.00' ? (
                      <Progress
                        value={Math.min(row.percent, 100)}
                        className={row.percent > 100 ? '[&>div]:bg-red-500' : ''}
                      />
                    ) : (
                      <span className="text-xs text-muted-foreground">Sin presupuesto</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
