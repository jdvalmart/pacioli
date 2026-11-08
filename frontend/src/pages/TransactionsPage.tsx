import { useEffect, useState } from 'react'
import { CreditCard, Plus, Wallet } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useMonth } from '@/hooks/useMonth'
import { api } from '@/lib/api'
import { useInvalidate, useTransactions } from '@/lib/queries'
import type { Transaction } from '@/lib/types'

import { DeleteTransactionDialog } from '@/components/transactions/DeleteTransactionDialog'
import { KindFilter, type KindFilterValue } from '@/components/transactions/KindFilter'
import { KIND_META } from '@/components/transactions/kinds'
import { TransactionForm } from '@/components/transactions/TransactionForm'
import { TransactionsTable } from '@/components/transactions/TransactionsTable'

export function TransactionsPage() {
  const { month } = useMonth()
  const invalidate = useInvalidate()
  const [searchParams, setSearchParams] = useSearchParams()
  // ?new=1 (the floating "new movement" button) opens the create form, even
  // when this page is already open: derived from the URL, not synced by an effect.
  const wantsNew = searchParams.get('new') === '1'
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Transaction | null>(null)
  const [deleting, setDeleting] = useState<Transaction | null>(null)
  const [kindFilter, setKindFilter] = useState<KindFilterValue>('all')

  const handleFormOpenChange = (open: boolean) => {
    setFormOpen(open)
    if (!open && wantsNew) {
      searchParams.delete('new')
      setSearchParams(searchParams, { replace: true })
    }
  }

  const transactions = useTransactions(month)

  useEffect(() => {
    let cancelled = false
    api
      .materializeRecurring(month.month, month.year)
      .then((result) => {
        if (!cancelled && result.created > 0) {
          void invalidate('movement')
        }
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [month, invalidate])

  const openCreate = () => {
    setEditing(null)
    setFormOpen(true)
  }
  const openEdit = (transaction: Transaction) => {
    setEditing(transaction)
    setFormOpen(true)
  }

  const allTransactions = transactions.data ?? []
  const accountTransactions = allTransactions.filter((tx) => tx.kind !== 'gasto_tc')
  const cardTransactions = allTransactions.filter((tx) => tx.kind === 'gasto_tc')
  const filteredTransactions =
    kindFilter === 'all'
      ? allTransactions
      : allTransactions.filter((tx) => tx.kind === kindFilter)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-extrabold">Movimientos</h1>
          <p className="text-sm font-semibold text-muted-foreground">
            Todos los movimientos del mes
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus /> Nuevo movimiento
        </Button>
      </div>

      <KindFilter transactions={allTransactions} value={kindFilter} onChange={setKindFilter} />

      {kindFilter === 'all' ? (
        <>
          <section className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Wallet className="size-4 text-primary" />
              <h2 className="text-base font-extrabold">Cuentas</h2>
              <Badge variant="secondary">{accountTransactions.length}</Badge>
              <span className="text-xs font-semibold text-muted-foreground">
                Ingresos, gastos, transferencias, ahorros y pagos de tarjeta
              </span>
            </div>
            <TransactionsTable
              rows={accountTransactions}
              emptyMessage="Sin movimientos de cuenta este mes."
              onEdit={openEdit}
              onDelete={setDeleting}
            />
          </section>

          <section className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <CreditCard className="size-4 text-orange-500" />
              <h2 className="text-base font-extrabold">Tarjetas de crédito</h2>
              <Badge variant="secondary">{cardTransactions.length}</Badge>
              <span className="text-xs font-semibold text-muted-foreground">
                Compras con tarjeta (no se descuentan de tus cuentas hasta que las pagues)
              </span>
            </div>
            <TransactionsTable
              rows={cardTransactions}
              emptyMessage="Sin compras con tarjeta este mes."
              onEdit={openEdit}
              onDelete={setDeleting}
            />
          </section>
        </>
      ) : (
        <section className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-base font-extrabold">{KIND_META[kindFilter].label}</h2>
            <Badge variant="secondary">{filteredTransactions.length}</Badge>
            <span className="text-xs font-semibold text-muted-foreground">
              Movimientos de tipo {KIND_META[kindFilter].label.toLowerCase()}
            </span>
          </div>
          <TransactionsTable
            rows={filteredTransactions}
            emptyMessage={`Sin movimientos de tipo ${KIND_META[kindFilter].label.toLowerCase()} este mes.`}
            onEdit={openEdit}
            onDelete={setDeleting}
          />
        </section>
      )}

      <TransactionForm
        open={formOpen || wantsNew}
        onOpenChange={handleFormOpenChange}
        transaction={editing}
      />

      <DeleteTransactionDialog transaction={deleting} onClose={() => setDeleting(null)} />
    </div>
  )
}
