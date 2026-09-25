import type { LucideIcon } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'

export type StatTone = 'primary' | 'income' | 'expense' | 'neutral'

const TONE_CLASS: Record<StatTone, string> = {
  primary:
    'bg-primary text-primary-foreground shadow-[0_4px_0_0_color-mix(in_oklch,var(--primary),black_18%)]',
  income: 'bg-emerald-500 text-white shadow-[0_4px_0_0_#059669]',
  expense: 'bg-rose-500 text-white shadow-[0_4px_0_0_#e11d48]',
  neutral: 'bg-slate-700 text-white shadow-[0_4px_0_0_#334155]',
}

export function StatCard({
  title,
  value,
  detail,
  icon: Icon,
  tone = 'primary',
  valueClassName,
}: {
  title: string
  value: string
  detail?: string
  icon: LucideIcon
  tone?: StatTone
  valueClassName?: string
}) {
  return (
    <Card className="flex-row items-center gap-4 p-5">
      <div
        className={cn(
          'flex size-14 shrink-0 items-center justify-center rounded-2xl',
          TONE_CLASS[tone],
        )}
      >
        <Icon className="size-7" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-extrabold tracking-wider text-muted-foreground uppercase">
          {title}
        </p>
        <p className={cn('truncate text-2xl font-black', valueClassName)}>{value}</p>
        {detail && <p className="text-xs font-bold text-muted-foreground">{detail}</p>}
      </div>
    </Card>
  )
}
