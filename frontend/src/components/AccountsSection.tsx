import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Pencil, Plus, Trash2, Wallet } from 'lucide-react'
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
import { SectionCard } from '@/components/SectionCard'
import { fmtCopDecimals, normalizeAmount } from '@/lib/money'
import type { Account, AccountType } from '@/lib/types'

const ACCOUNT_TYPES: { value: AccountType; label: string; icon: string }[] = [
  { value: 'efectivo', label: 'Cash wallet', icon: '💵' },
  { value: 'digital', label: 'Digital wallet', icon: '📱' },
  { value: 'ahorros', label: 'Savings account', icon: '🐷' },
  { value: 'banco', label: 'Bank account', icon: '🏦' },
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
  const [startingAmount, setStartingAmount] = useState(
    account?.starting ? String(Math.round(Number(account.starting))) : '',
  )

  const mutation = useMutation({
    mutationFn: async () => {
      const starting = normalizeAmount(startingAmount || '0')
      if (account) {
        await api.updateAccount(account.id, { name, type, starting_amount: starting })
      } else {
        await api.createAccount({ name, type, starting_amount: starting })
      }
    },
    onSuccess: () => {
      toast.success(account ? 'Account updated' : 'Account created')
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
        <DialogTitle>{account ? 'Edit account' : 'New account'}</DialogTitle>
        <DialogDescription>
          Balance is calculated only from transactions assigned to it.
        </DialogDescription>
      </DialogHeader>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="acc-name">Name</Label>
          <Input
            id="acc-name"
            required
            placeholder="E.g. Wallet, Nequi, Savings"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label>Type</Label>
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
          <Label htmlFor="acc-start">Starting balance</Label>
          <Input
            id="acc-start"
            placeholder="0"
            value={startingAmount}
            onChange={(e) => setStartingAmount(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Money you already had before using the app. Not counted in any month, only in the
            account balance.
          </p>
        </div>
        <Button type="submit" className="w-full" disabled={mutation.isPending}>
          {mutation.isPending ? 'Saving…' : 'Save'}
        </Button>
      </form>
    </>
  )
}

export function AccountsSection({ readOnly = false }: { readOnly?: boolean } = {}) {
  const queryClient = useQueryClient()
  const accounts = useQuery({ queryKey: ['accounts'], queryFn: api.listAccounts })
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Account | null>(null)
  const [deleting, setDeleting] = useState<Account | null>(null)

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteAccount(id),
    onSuccess: () => {
      toast.success('Account deleted — its transactions are now unassigned')
      setDeleting(null)
      void queryClient.invalidateQueries({ queryKey: ['accounts'] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const total = (accounts.data ?? []).reduce((sum, a) => sum + Number(a.balance), 0)

  return (
    <>
      <SectionCard
        icon={Wallet}
        title="Accounts"
        subtitle={`Where your money is${
          (accounts.data ?? []).length > 0 ? ` · total ${fmtCopDecimals(total)}` : ''
        }`}
        action={
          !readOnly ? (
            <Button
              size="icon"
              aria-label="New account"
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
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {accounts.isLoading ? (
          <>
            <Skeleton className="h-28 w-full" />
            <Skeleton className="h-28 w-full" />
            <Skeleton className="h-28 w-full" />
          </>
        ) : accounts.data?.length === 0 ? (
          <Card className="col-span-full p-6 text-center text-sm font-semibold text-muted-foreground">
            You don't have any accounts yet. Create a cash wallet, digital wallet or savings
            account to track how much you have and where.
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
                {!readOnly && (
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
                )}
              </div>
              <p className="mt-3 text-xl font-black">{fmtCopDecimals(account.balance)}</p>
              {Number(account.starting) > 0 && (
                <p className="text-xs font-bold text-muted-foreground">
                  Includes {fmtCopDecimals(account.starting)} starting balance
                </p>
              )}
            </Card>
          ))
        )}
        </div>
      </SectionCard>

      <AccountForm open={formOpen} onOpenChange={setFormOpen} account={editing} />

      <AlertDialog open={!!deleting} onOpenChange={(open) => !open && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete account?</AlertDialogTitle>
            <AlertDialogDescription>
              &quot;{deleting?.name}&quot; will be deleted. Its transactions won't be deleted, just
              left unassigned.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleting && deleteMutation.mutate(deleting.id)}
              className="bg-red-600 hover:bg-red-700"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
