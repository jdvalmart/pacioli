/**
 * Shared Recharts styling that follows the theme tokens (light and dark).
 * Colors are CSS variables, so charts switch with the rest of the app.
 */
export const CHART = {
  income: 'var(--chart-3)',
  expense: 'var(--chart-4)',
  balance: 'var(--chart-2)',
  grid: 'var(--border)',
  reference: 'var(--muted-foreground)',
} as const

export const axisProps = {
  stroke: 'var(--muted-foreground)',
  tick: { fill: 'var(--muted-foreground)', fontSize: 12 },
  tickLine: false,
  axisLine: false,
} as const

export const tooltipProps = {
  cursor: { fill: 'var(--muted)', opacity: 0.6 },
  contentStyle: {
    background: 'var(--popover)',
    border: '1px solid var(--border)',
    borderRadius: 8,
    color: 'var(--popover-foreground)',
    fontSize: 13,
    boxShadow: '0 4px 16px rgb(0 0 0 / 0.08)',
  },
  labelStyle: { color: 'var(--muted-foreground)', marginBottom: 4 },
} as const
