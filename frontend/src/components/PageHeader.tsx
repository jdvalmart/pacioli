/** The same title block on every page: title, one-line description, primary action. */
export function PageHeader({
  title,
  description,
  action,
}: {
  title: string
  description?: React.ReactNode
  action?: React.ReactNode
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>}
      </div>
      {action && <div className="flex shrink-0 items-center gap-2">{action}</div>}
    </div>
  )
}

/** Heading of a block inside a page, with an optional count and trailing detail. */
export function SectionHeading({
  title,
  count,
  detail,
  aside,
}: {
  title: string
  count?: number
  detail?: string
  aside?: React.ReactNode
}) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
      <div className="flex min-w-0 items-baseline gap-2">
        <h2 className="text-base font-semibold">{title}</h2>
        {count != null && <span className="text-sm text-muted-foreground">{count}</span>}
        {detail && <span className="hidden truncate text-xs text-muted-foreground sm:inline">{detail}</span>}
      </div>
      {aside && <div className="text-sm text-muted-foreground">{aside}</div>}
    </div>
  )
}
