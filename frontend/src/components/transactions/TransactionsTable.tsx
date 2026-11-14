import { MoreHorizontal, Pencil, Repeat, Trash2 } from 'lucide-react'

import { CategoryIcon } from '@/components/CategoryIcon'
import { KIND_META } from '@/components/transactions/kinds'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { fmtMoney, fmtSigned } from '@/lib/money'
import type { Transaction } from '@/lib/types'
import { cn } from '@/lib/utils'

const fmtDate = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' })

/** Where the money moved, in words: "Bancolombia → Nequi", "Visa · cuota 2/6 de $3.600.000". */
function context(tx: Transaction): string {
  const account = tx.account_name ?? 'Cuenta'
  switch (tx.kind) {
    case 'transferencia':
      return `${account} → ${tx.to_account_name ?? 'Cuenta'}`
    case 'gasto_tc': {
      const card = tx.card_name ?? 'Tarjeta de crédito'
      return tx.installments > 1 && tx.installment_number
        ? `${card} · cuota ${tx.installment_number}/${tx.installments} de ${fmtMoney(tx.amount)}`
        : card
    }
    case 'pago_tc':
      return `${account} → ${tx.card_name ?? 'Tarjeta'}`
    case 'ahorro':
      return `${account} → ${tx.savings_name ?? 'Ahorro'}`
    case 'retiro':
      return `${tx.savings_name ?? 'Ahorro'} → ${account}`
    default:
      return tx.loan_name ? `${account} → ${tx.loan_name}` : (tx.account_name ?? '')
  }
}

/** Category column: the category when there is one, otherwise the kind itself. */
function CategoryCell({ tx }: { tx: Transaction }) {
  const meta = KIND_META[tx.kind]
  if (tx.category_name) {
    const detail =
      tx.subcategory_name ?? (tx.kind === 'gasto' || tx.kind === 'ingreso' ? null : meta.label)
    return (
      <div className="flex min-w-0 items-center gap-2.5">
        <CategoryIcon icon={tx.icon} color={tx.color} size="sm" />
        <div className="min-w-0">
          <p className="truncate">{tx.category_name}</p>
          {detail && <p className="truncate text-xs text-muted-foreground">{detail}</p>}
        </div>
      </div>
    )
  }
  const Icon = meta.icon
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
        <Icon className="size-3.5" />
      </span>
      <p className="truncate">{meta.label}</p>
    </div>
  )
}

function Amount({ tx, className }: { tx: Transaction; className?: string }) {
  const meta = KIND_META[tx.kind]
  return (
    <span className={cn('font-medium whitespace-nowrap', meta.amountClass, className)}>
      {fmtSigned(tx.billed_amount ?? tx.amount, meta.sign)}
    </span>
  )
}

function RowActions({
  tx,
  onEdit,
  onDelete,
}: {
  tx: Transaction
  onEdit: (tx: Transaction) => void
  onDelete: (tx: Transaction) => void
}) {
  const name = (tx.description || tx.category_name || '').trim()
  return (
    <div className="flex justify-end gap-0.5">
      <Button
        variant="ghost"
        size="icon-sm"
        className="text-muted-foreground hover:text-foreground"
        aria-label={`Editar movimiento ${name}`.trim()}
        onClick={() => onEdit(tx)}
      >
        <Pencil />
      </Button>
      <Button
        variant="ghost"
        size="icon-sm"
        className="text-muted-foreground hover:text-destructive"
        aria-label={`Eliminar movimiento ${name}`.trim()}
        onClick={() => onDelete(tx)}
      >
        <Trash2 />
      </Button>
    </div>
  )
}

/** Mobile: one compact menu instead of two buttons, so descriptions keep their room. */
function RowMenu({
  tx,
  onEdit,
  onDelete,
}: {
  tx: Transaction
  onEdit: (tx: Transaction) => void
  onDelete: (tx: Transaction) => void
}) {
  const name = (tx.description || tx.category_name || '').trim()
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant="ghost"
            size="icon-sm"
            className="-mr-1 text-muted-foreground"
            aria-label={`Opciones de ${name || 'movimiento'}`}
          />
        }
      >
        <MoreHorizontal />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => onEdit(tx)}>
          <Pencil /> Editar
        </DropdownMenuItem>
        <DropdownMenuItem variant="destructive" onClick={() => onDelete(tx)}>
          <Trash2 /> Eliminar
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

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
  if (rows.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border px-4 py-10 text-center text-sm text-muted-foreground">
        {emptyMessage}
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card shadow-xs">
      {/* Desktop: statement-style table */}
      <Table className="hidden md:table">
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-24 pl-4 text-xs font-medium text-muted-foreground">Fecha</TableHead>
            <TableHead className="text-xs font-medium text-muted-foreground">Descripción</TableHead>
            <TableHead className="w-64 text-xs font-medium text-muted-foreground">Categoría</TableHead>
            <TableHead className="w-40 text-right text-xs font-medium text-muted-foreground">Monto</TableHead>
            <TableHead className="w-24 pr-4" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((tx) => (
            <TableRow key={tx.id} className="group">
              <TableCell className="pl-4 whitespace-nowrap text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  {fmtDate(tx.date)}
                  {(tx.is_recurring || tx.generated_from) && (
                    <Repeat className="size-3.5" aria-label="Recurrente" />
                  )}
                </span>
              </TableCell>
              <TableCell className="max-w-0">
                <p className="truncate font-medium">{tx.description || KIND_META[tx.kind].label}</p>
                <p className="truncate text-xs text-muted-foreground">{context(tx)}</p>
              </TableCell>
              <TableCell className="max-w-64">
                <CategoryCell tx={tx} />
              </TableCell>
              <TableCell className="text-right">
                <Amount tx={tx} />
              </TableCell>
              <TableCell className="pr-4">
                <div className="opacity-60 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
                  <RowActions tx={tx} onEdit={onEdit} onDelete={onDelete} />
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {/* Mobile: one card-like row per movement, no sideways scrolling */}
      <ul className="divide-y divide-border md:hidden">
        {rows.map((tx) => (
          <li key={tx.id} className="flex items-start gap-3 px-3 py-3">
            {tx.category_name ? (
              <CategoryIcon icon={tx.icon} color={tx.color} />
            ) : (
              <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                {(() => {
                  const Icon = KIND_META[tx.kind].icon
                  return <Icon className="size-4" />
                })()}
              </span>
            )}
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-2">
                <p className="truncate text-sm font-medium">
                  {tx.description || tx.category_name || KIND_META[tx.kind].label}
                </p>
                <Amount tx={tx} className="text-sm" />
              </div>
              <p className="truncate text-xs text-muted-foreground">
                {fmtDate(tx.date)} · {tx.category_name ?? KIND_META[tx.kind].label}
                {context(tx) && ` · ${context(tx)}`}
              </p>
            </div>
            <RowMenu tx={tx} onEdit={onEdit} onDelete={onDelete} />
          </li>
        ))}
      </ul>
    </div>
  )
}
