import type { LucideIcon } from 'lucide-react'
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

export function SectionCard({
  icon: Icon,
  title,
  subtitle,
  action,
  children,
}: {
  icon: LucideIcon
  title: string
  subtitle: string
  action?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-[0_3px_0_0_color-mix(in_oklch,var(--primary),black_18%)]">
            <Icon className="size-5" />
          </div>
          <div>
            <CardTitle>{title}</CardTitle>
            <CardDescription className="font-semibold">{subtitle}</CardDescription>
          </div>
        </div>
        {action && <CardAction>{action}</CardAction>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}
