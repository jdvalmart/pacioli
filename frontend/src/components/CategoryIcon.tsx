import { cn } from '@/lib/utils'

/**
 * A category's emoji on a soft tint of its color: identifiable at a glance
 * without the saturated circles competing with the numbers.
 */
export function CategoryIcon({
  icon,
  color,
  size = 'md',
  className,
}: {
  icon: string | null | undefined
  color: string | null | undefined
  size?: 'sm' | 'md'
  className?: string
}) {
  const tint = color || '#888888'
  return (
    <span
      aria-hidden
      className={cn(
        'flex shrink-0 items-center justify-center rounded-md',
        size === 'sm' ? 'size-7 text-sm' : 'size-9 text-base',
        className,
      )}
      style={{ backgroundColor: `color-mix(in oklch, ${tint} 16%, transparent)` }}
    >
      {icon || '•'}
    </span>
  )
}
