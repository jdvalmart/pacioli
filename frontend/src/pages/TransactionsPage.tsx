import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { monthLabel, useMonth } from '@/hooks/useMonth'
import { PageHeader, SectionHeading } from '@/components/PageHeader'
import { fmtMoney, fmtSigned } from '@/lib/money'
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

  // Net effect on the user's cash for a list of movements.
  const cashTotals = (rows: Transaction[]) => {
    let inflow = 0
    let outflow = 0
    for (const tx of rows) {
      const amount = Number(tx.billed_amount ?? tx.amount)
      const sign = KIND_META[tx.kind].sign
      if (sign === '+') inflow += amount
      else if (sign === '-') outflow += amount
    }
    return { inflow, outflow }
  }
  const accountTotals = cashTotals(accountTransactions)
  const cardTotal = cardTransactions.reduce(
    (sum, tx) => sum + Number(tx.billed_amount ?? tx.amount),
    0,
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="Movimientos"
        description={`Todo lo que entró y salió en ${monthLabel(month).toLowerCase()}`}
        action={
          <Button onClick={openCreate}>
            <Plus /> Nuevo movimiento
          </Button>
        }
      />

      <KindFilter transactions={allTransactions} value={kindFilter} onChange={setKindFilter} />

      {kindFilter === 'all' ? (
        <>
          <section className="space-y-3">
            <SectionHeading
              title="Cuentas"
              count={accountTransactions.length}
              detail="Ingresos, gastos, transferencias, ahorros y pagos de tarjeta"
              aside={
                <>
                  <span className="text-positive">{fmtSigned(accountTotals.inflow, '+')}</span>
                  <span className="mx-1.5">·</span>
                  <span className="text-foreground">{fmtSigned(accountTotals.outflow, '-')}</span>
                </>
              }
            />
            <TransactionsTable
              rows={accountTransactions}
              emptyMessage="Sin movimientos de cuenta este mes."
              onEdit={openEdit}
              onDelete={setDeleting}
            />
          </section>

          <section className="space-y-3">
            <SectionHeading
              title="Tarjetas de crédito"
              count={cardTransactions.length}
              detail="Cuotas que se pagan este mes; no salen de tus cuentas hasta que pagues la tarjeta"
              aside={cardTransactions.length > 0 ? fmtMoney(cardTotal) : undefined}
            />
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
          <SectionHeading title={KIND_META[kindFilter].label} count={filteredTransactions.length} />
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
