import { Pencil, Trash2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { fmtCopDecimals } from '@/lib/money'
import type { Transaction } from '@/lib/types'

import { KIND_META, amountClass } from '@/components/transactions/kinds'

export function TransactionsTable({
  rows,
  emptyMessage,
  onEdit,
  onDelete,
}: {
  rows: Transaction[]
  emptyMessage: string
  onEdit: (tx: Transaction) => void
  onDelete: (tx: Transaction) => void
}) {
  return (
    <div className="rounded-2xl border border-border bg-card shadow-[0_4px_0_0_rgba(0,0,0,0.05)]">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Fecha</TableHead>
            <TableHead>Tipo</TableHead>
            <TableHead>Subcategoría</TableHead>
            <TableHead>Detalle</TableHead>
            <TableHead className="text-right">Monto</TableHead>
            <TableHead className="w-24" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} className="py-10 text-center text-muted-foreground">
                {emptyMessage}
              </TableCell>
            </TableRow>
          )}
          {rows.map((tx) => (
            <TableRow key={tx.id}>
              <TableCell className="whitespace-nowrap">
                {new Date(`${tx.date}T00:00:00`).toLocaleDateString('es-CO', {
                  day: '2-digit',
                  month: 'short',
                })}
                {(tx.is_recurring || tx.generated_from) && (
                  <Badge variant="outline" className="ml-2">
                    recurrente
                  </Badge>
                )}
              </TableCell>
              <TableCell>
                <Badge className={KIND_META[tx.kind].badgeClass}>
                  {KIND_META[tx.kind].label}
                </Badge>
                {tx.kind !== 'transferencia' && (
                  <span className="ml-2">
                    <span
                      className="inline-block size-2.5 rounded-full align-middle"
                      style={{ backgroundColor: tx.color || '#888' }}
                    />
                    <span className="ml-1.5">
                      {tx.icon} {tx.category_name}
                    </span>
                  </span>
                )}
              </TableCell>
              <TableCell className="max-w-40 truncate font-bold text-muted-foreground">
                {tx.subcategory_name || '—'}
              </TableCell>
              <TableCell className="max-w-64 truncate">
                <div className="truncate">{tx.description || '—'}</div>
                <div className="mt-0.5 truncate text-xs font-bold text-muted-foreground">
                  {tx.kind === 'transferencia'
                    ? `${tx.account_icon} ${tx.account_name ?? '—'} → ${tx.to_account_icon} ${tx.to_account_name ?? '—'}`
                    : tx.kind === 'gasto_tc'
                      ? `💳 ${tx.card_name ?? 'Tarjeta de crédito'}${
                          tx.installments > 1 && tx.installment_number
                            ? ` · cuota ${tx.installment_number}/${tx.installments} de ${fmtCopDecimals(tx.amount)}`
                            : ''
                        }`
                      : tx.kind === 'pago_tc'
                        ? `${tx.account_icon} ${tx.account_name ?? '—'} → 💳 ${tx.card_name ?? 'Tarjeta'}`
                        : tx.kind === 'ahorro' || tx.kind === 'retiro'
                          ? `${tx.account_icon} ${tx.account_name ?? '—'} ⇄ 👝 ${tx.savings_name ?? 'Ahorro'}`
                          : tx.account_name
                            ? `${tx.account_icon} ${tx.account_name}`
                            : '—'}
              </div>
            </TableCell>
              <TableCell className={`text-right font-bold ${amountClass(tx)}`}>
                {tx.kind === 'ingreso' ? '+' : tx.kind === 'transferencia' ? '⇄' : '−'}
                {fmtCopDecimals(tx.billed_amount ?? tx.amount)}
              </TableCell>
              <TableCell>
                <div className="flex justify-end gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Editar movimiento ${tx.description || tx.category_name || ''}`.trim()}
                    onClick={() => onEdit(tx)}
                  >
                    <Pencil />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Eliminar movimiento ${tx.description || tx.category_name || ''}`.trim()}
                    onClick={() => onDelete(tx)}
                  >
                    <Trash2 className="text-red-500" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
