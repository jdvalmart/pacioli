import type { LucideIcon } from 'lucide-react'

import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'

export type StatTone = 'primary' | 'income' | 'expense' | 'neutral'

/** Small, quiet icon tint per tone; the number is the hero, not the icon. */
const ICON_TONE: Record<StatTone, string> = {
  primary: 'bg-brand-soft text-[color-mix(in_oklch,var(--primary),black_45%)] dark:text-primary',
  income: 'bg-positive/10 text-positive',
  expense: 'bg-negative/10 text-negative',
  neutral: 'bg-muted text-muted-foreground',
}

export function StatCard({
  title,
  value,
  detail,
  icon: Icon,
  tone = 'neutral',
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
    <Card className="gap-3 p-4 sm:p-5">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium text-muted-foreground">{title}</p>
        <span
          className={cn('flex size-7 shrink-0 items-center justify-center rounded-md', ICON_TONE[tone])}
          aria-hidden
        >
          <Icon className="size-4" />
        </span>
      </div>
      {/* Never truncate money: shrink on small screens and wrap if it must. */}
      <p
        className={cn(
          'text-xl leading-tight font-semibold tracking-tight break-words sm:text-2xl',
          valueClassName,
        )}
      >
        {value}
      </p>
      {detail && <p className="-mt-1.5 text-xs text-muted-foreground">{detail}</p>}
    </Card>
  )
}
