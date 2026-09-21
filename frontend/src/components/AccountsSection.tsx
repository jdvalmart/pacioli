import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Pencil, Plus, Trash2 } from 'lucide-react'
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { fmtCopDecimals, normalizeAmount } from '@/lib/money'
import type { Account, AccountType } from '@/lib/types'

const ACCOUNT_TYPES: { value: AccountType; label: string; icon: string }[] = [
  { value: 'efectivo', label: 'Billetera física', icon: '💵' },
  { value: 'digital', label: 'Billetera digital', icon: '📱' },
  { value: 'ahorros', label: 'Cuenta de ahorros', icon: '🐷' },
  { value: 'banco', label: 'Cuenta bancaria', icon: '🏦' },
]

function typeLabel(type: AccountType): string {
  return ACCOUNT_TYPES.find((t) => t.value === type)?.label ?? type
}

function AccountForm({
  open,
  onOpenChange,
  account,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  account: Account | null
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {open && <AccountFormBody account={account} onOpenChange={onOpenChange} />}
      </DialogContent>
    </Dialog>
  )
}

function AccountFormBody({
  account,
  onOpenChange,
}: {
  account: Account | null
  onOpenChange: (open: boolean) => void
}) {
  const queryClient = useQueryClient()
  const [name, setName] = useState(account?.name ?? '')
  const [type, setType] = useState<AccountType>(account?.type ?? 'efectivo')
  const [startingAmount, setStartingAmount] = useState('')

  const mutation = useMutation({
    mutationFn: async () => {
      if (account) {
        await api.updateAccount(account.id, { name })
      } else {
        await api.createAccount({
          name,
          type,
          starting_amount: normalizeAmount(startingAmount || '0'),
        })
      }
    },
    onSuccess: () => {
      toast.success(account ? 'Cuenta actualizada' : 'Cuenta creada')
      onOpenChange(false)
      void queryClient.invalidateQueries({ queryKey: ['accounts'] })
      void queryClient.invalidateQueries({ queryKey: ['transactions'] })
      void queryClient.invalidateQueries({ queryKey: ['summary'] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    mutation.mutate()
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle>{account ? 'Editar cuenta' : 'Nueva cuenta'}</DialogTitle>
        <DialogDescription>
          El saldo se calcula solo con los movimientos que le asignes.
        </DialogDescription>
      </DialogHeader>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="acc-name">Nombre</Label>
          <Input
            id="acc-name"
            required
            placeholder="Ej. Billetera, Nequi, Ahorros"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        {!account && (
          <>
            <div className="space-y-1.5">
              <Label>Tipo</Label>
              <Select
                value={type}
                onValueChange={(v) => setType((v ?? 'efectivo') as AccountType)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ACCOUNT_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.icon} {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="acc-start">Dinero inicial (opcional)</Label>
              <Input
                id="acc-start"
                placeholder="0"
                value={startingAmount}
                onChange={(e) => setStartingAmount(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Se registra como ingreso de este mes en &quot;Otros ingresos&quot;.
              </p>
            </div>
          </>
        )}
        <Button type="submit" className="w-full" disabled={mutation.isPending}>
          {mutation.isPending ? 'Guardando…' : 'Guardar'}
        </Button>
      </form>
    </>
  )
}

export function AccountsSection() {
  const queryClient = useQueryClient()
  const accounts = useQuery({ queryKey: ['accounts'], queryFn: api.listAccounts })
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Account | null>(null)
  const [deleting, setDeleting] = useState<Account | null>(null)

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteAccount(id),
    onSuccess: () => {
      toast.success('Cuenta eliminada — sus movimientos quedaron sin cuenta')
      setDeleting(null)
      void queryClient.invalidateQueries({ queryKey: ['accounts'] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const total = (accounts.data ?? []).reduce((sum, a) => sum + Number(a.balance), 0)

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-extrabold">Cuentas</h2>
          <p className="text-sm font-semibold text-muted-foreground">
            Dónde está tu dinero
            {(accounts.data ?? []).length > 0 && ` · total ${fmtCopDecimals(total)}`}
          </p>
        </div>
        <Button
          size="icon"
          aria-label="Nueva cuenta"
          onClick={() => {
            setEditing(null)
            setFormOpen(true)
          }}
        >
          <Plus />
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {accounts.isLoading ? (
          <>
            <Skeleton className="h-28 w-full" />
            <Skeleton className="h-28 w-full" />
            <Skeleton className="h-28 w-full" />
          </>
        ) : accounts.data?.length === 0 ? (
          <Card className="col-span-full p-6 text-center text-sm font-semibold text-muted-foreground">
            Aún no tienes cuentas. Crea una billetera física, una digital o una de ahorros
            para saber cuánto tienes y dónde.
          </Card>
        ) : (
          [...(accounts.data ?? [])]
            .sort((a, b) => Number(b.balance) - Number(a.balance))
            .map((account) => (
            <Card key={account.id} className="p-4">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className="flex size-11 items-center justify-center rounded-xl text-xl text-white shadow-[0_3px_0_0_rgba(0,0,0,0.25)]"
                    style={{ backgroundColor: account.color }}
                  >
                    {account.icon}
                  </div>
                  <div>
                    <CardTitle className="text-sm leading-tight">{account.name}</CardTitle>
                    <p className="text-xs font-bold text-muted-foreground">
                      {typeLabel(account.type)}
                    </p>
                  </div>
                </div>
                <div className="flex gap-0.5">
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    onClick={() => {
                      setEditing(account)
                      setFormOpen(true)
                    }}
                  >
                    <Pencil className="size-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon-xs" onClick={() => setDeleting(account)}>
                    <Trash2 className="size-3.5 text-destructive" />
                  </Button>
                </div>
              </div>
              <p className="mt-3 text-xl font-black">{fmtCopDecimals(account.balance)}</p>
            </Card>
          ))
        )}
      </div>

      <AccountForm open={formOpen} onOpenChange={setFormOpen} account={editing} />

      <AlertDialog open={!!deleting} onOpenChange={(open) => !open && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar cuenta?</AlertDialogTitle>
            <AlertDialogDescription>
              Se eliminará &quot;{deleting?.name}&quot;. Sus movimientos no se borran, solo
              quedan sin cuenta asignada.
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
    </section>
  )
}
