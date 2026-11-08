import { Monitor, Moon, Sun } from 'lucide-react'
import { useTheme } from 'next-themes'

import { Button } from '@/components/ui/button'

const NEXT = { system: 'light', light: 'dark', dark: 'system' } as const
const LABEL = { system: 'Tema del sistema', light: 'Tema claro', dark: 'Tema oscuro' } as const
const ICON = { system: Monitor, light: Sun, dark: Moon } as const

type Mode = keyof typeof NEXT

/** Cycles system → light → dark; the button shows the current mode. */
export function ThemeToggle({ withLabel = false }: { withLabel?: boolean }) {
  const { theme, setTheme } = useTheme()
  const mode: Mode = theme === 'light' || theme === 'dark' ? theme : 'system'
  const Icon = ICON[mode]
  return (
    <Button
      variant="ghost"
      size={withLabel ? 'sm' : 'icon-sm'}
      onClick={() => setTheme(NEXT[mode])}
      aria-label={`${LABEL[mode]} (cambiar)`}
      title={LABEL[mode]}
      className={withLabel ? 'w-full justify-start gap-2 text-muted-foreground' : 'text-muted-foreground'}
    >
      <Icon className="size-4" />
      {withLabel && LABEL[mode]}
    </Button>
  )
}
