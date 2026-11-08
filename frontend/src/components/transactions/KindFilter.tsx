import { KIND_META, KIND_ORDER } from '@/components/transactions/kinds'
import type { Transaction, TransactionKind } from '@/lib/types'

export type KindFilterValue = TransactionKind | 'all'

const FILTERS: { value: KindFilterValue; label: string }[] = [
  { value: 'all', label: 'Todos' },
  ...KIND_ORDER.map((kind) => ({ value: kind, label: KIND_META[kind].label })),
]

/** Kind chips with per-kind counts; ``value`` is the selected filter. */
export function KindFilter({
  transactions,
  value: selected,
  onChange,
}: {
  transactions: Transaction[]
  value: KindFilterValue
  onChange: (value: KindFilterValue) => void
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {FILTERS.map(({ value, label }) => {
        const active = selected === value
        const count =
          value === 'all'
            ? transactions.length
            : transactions.filter((tx) => tx.kind === value).length
        return (
          <button
            key={value}
            type="button"
            onClick={() => onChange(value)}
            className={`rounded-xl border px-3 py-1.5 text-xs font-bold transition-colors ${
              active
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border bg-background text-muted-foreground hover:bg-muted'
            }`}
          >
            {label}
            <span className={`ml-1.5 ${active ? 'opacity-80' : 'opacity-60'}`}>{count}</span>
          </button>
        )
      })}
    </div>
  )
}
