import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Pencil, PiggyBank, Plus, Trash2, TrendingUp } from 'lucide-react'
import { toast } from 'sonner'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { SectionCard } from '@/components/SectionCard'
import { KIND_META, SavingsFormDialog } from '@/components/SavingsFormDialog'
import { fmtCopDecimals } from '@/lib/money'
import type { SavingsItem } from '@/lib/types'

export function SavingsSection({ readOnly = false }: { readOnly?: boolean } = {}) {
  const queryClient = useQueryClient()
  const items = useQuery({ queryKey: ['savings'], queryFn: api.listSavings })
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<SavingsItem | null>(null)
  const [deleting, setDeleting] = useState<SavingsItem | null>(null)

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteSavings(id),
    onSuccess: () => {
      toast.success('Eliminado')
      setDeleting(null)
      void queryClient.invalidateQueries({ queryKey: ['savings'] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const total = (items.data ?? []).reduce((sum, s) => sum + Number(s.balance), 0)

  return (
    <>
      <SectionCard
        icon={PiggyBank}
        title="Ahorro e inversión"
        subtitle={`Bolsillos, ahorros programados, CDTs y acciones${
          (items.data ?? []).length > 0 ? ` · total ${fmtCopDecimals(total)}` : ''
        }`}
        action={
          !readOnly ? (
            <Button
              size="icon"
              aria-label="Nuevo ahorro o inversión"
              onClick={() => {
                setEditing(null)
                setFormOpen(true)
              }}
            >
              <Plus />
            </Button>
          ) : undefined
        }
      >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.isLoading ? (
          <>
            <Skeleton className="h-36 w-full" />
            <Skeleton className="h-36 w-full" />
          </>
        ) : items.data?.length === 0 ? (
          <Card className="col-span-full p-6 text-center text-sm font-semibold text-muted-foreground">
            Aún no tienes ahorros ni inversiones. Crea un bolsillo, un CDT o registra tus
            acciones para ver crecer tu dinero.
          </Card>
        ) : (
          [...(items.data ?? [])]
            .sort((a, b) => {
              const valueA = a.current_value != null ? Number(a.current_value) : Number(a.balance)
              const valueB = b.current_value != null ? Number(b.current_value) : Number(b.balance)
              return valueB - valueA
            })
            .map((item) => {
            const balance = Number(item.balance)
            const invested = Number(item.invested)
            const current = item.current_value != null ? Number(item.current_value) : invested
            const dividends = Number(item.dividends ?? 0)
            const priceGain = current - invested
            const totalGain = priceGain + dividends
            const totalGainPct = invested > 0 ? (totalGain / invested) * 100 : 0
            const target = item.target ? Number(item.target) : 0
            const targetPct = target > 0 ? (balance / target) * 100 : 0

            return (
              <Card key={item.id} className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex size-11 items-center justify-center rounded-xl bg-amber-400 text-xl text-amber-950 shadow-[0_3px_0_0_#b45309]">
                      {KIND_META[item.kind]?.icon ?? '💰'}
                    </div>
                    <div>
                      <CardTitle className="text-sm leading-tight">{item.name}</CardTitle>
                      <p className="text-xs font-bold text-muted-foreground">
                        {KIND_META[item.kind]?.label ?? item.kind}
                      </p>
                    </div>
                  </div>
                  {!readOnly && (
                    <div className="flex gap-0.5">
                      <Button
                        variant="ghost"
                        size="icon-xs"
                        onClick={() => {
                          setEditing(item)
                          setFormOpen(true)
                        }}
                      >
                        <Pencil className="size-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon-xs" onClick={() => setDeleting(item)}>
                        <Trash2 className="size-3.5 text-destructive" />
                      </Button>
                    </div>
                  )}
                </div>

                <div className="mt-3 space-y-1.5">
                  <p className="text-xl font-black">
                    {item.kind === 'acciones' && item.current_value != null
                      ? fmtCopDecimals(current)
                      : fmtCopDecimals(item.balance)}
                  </p>

                  {item.kind === 'acciones' && (
                    <div className="space-y-0.5 text-xs font-bold text-muted-foreground">
                      <p>Invertido: {fmtCopDecimals(invested)}</p>
                      <p className={priceGain >= 0 ? 'text-emerald-600' : 'text-red-600'}>
                        <TrendingUp className="mr-1 inline size-3.5" />
                        Precio: {priceGain >= 0 ? '+' : ''}
                        {fmtCopDecimals(priceGain)}
                      </p>
                      {dividends > 0 && <p>Dividendos: +{fmtCopDecimals(dividends)}</p>}
                      <p className={totalGain >= 0 ? 'text-emerald-600' : 'text-red-600'}>
                        Ganancia total: {totalGain >= 0 ? '+' : ''}
                        {fmtCopDecimals(totalGain)} ({totalGainPct >= 0 ? '+' : ''}
                        {totalGainPct.toFixed(1)}%)
                      </p>
                    </div>
                  )}

                  {item.rate_bp != null && item.kind !== 'acciones' && (
                    <p className="text-xs font-bold text-muted-foreground">
                      Tasa {item.rate_bp / 100}% EA
                      {item.term_days
                        ? ` · rendimiento ≈ ${fmtCopDecimals(
                            (invested * (item.rate_bp / 100) * (item.term_days / 360)) / 100,
                          )}`
                        : ''}
                    </p>
                  )}

                  {item.kind === 'bolsillo_programado' && item.scheduled_amount != null && (
                    <p className="text-xs font-bold text-muted-foreground">
                      📆 Día {item.scheduled_day}: {fmtCopDecimals(item.scheduled_amount)}/mes
                    </p>
                  )}

                  {item.matures_on && (
                    <p className="text-xs font-bold text-muted-foreground">
                      {item.matures_on > new Date().toISOString().slice(0, 10)
                        ? `🔒 Bloqueado hasta el ${item.matures_on}`
                        : `Vencido el ${item.matures_on}`}
                    </p>
                  )}

                  {target > 0 && (
                    <>
                      <Progress
                        value={Math.min(targetPct, 100)}
                        indicatorClassName="bg-amber-400"
                      />
                      <p className="text-xs font-bold text-muted-foreground">
                        {Math.round(targetPct)}% de la meta {fmtCopDecimals(target)}
                      </p>
                    </>
                  )}
                </div>
              </Card>
            )
          })
        )}
      </div>
      </SectionCard>

      <SavingsFormDialog open={formOpen} onOpenChange={setFormOpen} item={editing} />

      <AlertDialog open={!!deleting} onOpenChange={(open) => !open && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar {deleting?.name}?</AlertDialogTitle>
            <AlertDialogDescription>
              Se eliminará junto con su ahorro programado (si tiene). Los movimientos no se
              borran, solo quedan sin bolsillo asignado.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleting && deleteMutation.mutate(deleting.id)}
              className="bg-red-600 hover:bg-red-700"
            >
              Eliminar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
