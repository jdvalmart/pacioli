import { lazy, Suspense, useState } from 'react'
import {
  ChartColumnBig,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  Loader2,
  PanelLeftClose,
  PanelLeftOpen,
  PiggyBank,
  Plus,
  ReceiptText,
  Settings,
} from 'lucide-react'
import { NavLink, Route, Routes, useNavigate } from 'react-router-dom'

import { Logo } from '@/components/Logo'
import { ThemeToggle } from '@/components/ThemeToggle'
import { Button } from '@/components/ui/button'
import { currentMonth, monthLabel, useMonth } from '@/hooks/useMonth'
import { cn } from '@/lib/utils'

// Pages load on demand so charts (Recharts) and other heavy
// dependencies only ship when their route is actually visited.
const BudgetsPage = lazy(() =>
  import('@/pages/BudgetsPage').then((m) => ({ default: m.BudgetsPage })),
)
const SettingsPage = lazy(() =>
  import('@/pages/SettingsPage').then((m) => ({ default: m.SettingsPage })),
)
const DashboardPage = lazy(() =>
  import('@/pages/DashboardPage').then((m) => ({ default: m.DashboardPage })),
)
const ReportsPage = lazy(() =>
  import('@/pages/ReportsPage').then((m) => ({ default: m.ReportsPage })),
)
const TransactionsPage = lazy(() =>
  import('@/pages/TransactionsPage').then((m) => ({ default: m.TransactionsPage })),
)

function PageLoader() {
  return (
    <div className="flex h-64 items-center justify-center text-muted-foreground">
      <Loader2 className="size-5 animate-spin" />
    </div>
  )
}

const NAV_ITEMS = [
  { to: '/', label: 'Panel', icon: LayoutDashboard, end: true },
  { to: '/transactions', label: 'Movimientos', icon: ReceiptText },
  { to: '/budgets', label: 'Presupuestos', icon: PiggyBank },
  { to: '/reports', label: 'Reportes', icon: ChartColumnBig },
  { to: '/settings', label: 'Ajustes', icon: Settings },
]

const SIDEBAR_KEY = 'pacioli-sidebar'

function readCollapsed(): boolean {
  try {
    return localStorage.getItem(SIDEBAR_KEY) === 'collapsed'
  } catch {
    return false
  }
}

/** Floating "new movement" action; sits above the mobile tab bar. */
function NewTransactionFab() {
  const navigate = useNavigate()
  return (
    <button
      type="button"
      onClick={() => navigate('/transactions?new=1')}
      className="fixed right-4 bottom-20 z-40 flex size-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg ring-1 ring-black/5 transition-colors hover:bg-[color-mix(in_oklch,var(--primary),black_6%)] focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none md:right-6 md:bottom-6 md:size-14"
      aria-label="Nuevo movimiento"
      title="Nuevo movimiento"
    >
      <Plus className="size-6" />
    </button>
  )
}

function MonthPicker() {
  const { month, shiftMonth, setMonth } = useMonth()
  const thisMonth = currentMonth()
  const isCurrentMonth = month.month === thisMonth.month && month.year === thisMonth.year
  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center rounded-lg border border-border bg-card shadow-xs">
        <Button
          variant="ghost"
          size="icon-sm"
          className="rounded-r-none"
          onClick={() => shiftMonth(-1)}
          aria-label="Mes anterior"
        >
          <ChevronLeft />
        </Button>
        <span className="min-w-[8.5rem] px-1 text-center text-sm font-medium whitespace-nowrap">
          {monthLabel(month)}
        </span>
        <Button
          variant="ghost"
          size="icon-sm"
          className="rounded-l-none"
          onClick={() => shiftMonth(1)}
          aria-label="Mes siguiente"
        >
          <ChevronRight />
        </Button>
      </div>
      {!isCurrentMonth && (
        <Button variant="outline" size="sm" onClick={() => setMonth(currentMonth())}>
          Hoy
        </Button>
      )}
    </div>
  )
}

export default function App() {
  const [collapsed, setCollapsed] = useState(readCollapsed)

  const toggleSidebar = () => {
    setCollapsed((prev) => {
      const next = !prev
      try {
        localStorage.setItem(SIDEBAR_KEY, next ? 'collapsed' : 'expanded')
      } catch {
        // storage unavailable: the choice just won't persist
      }
      return next
    })
  }

  return (
    <div className="flex h-dvh overflow-hidden bg-background">
      {/* Desktop sidebar */}
      <aside
        className={cn(
          'hidden shrink-0 flex-col border-r border-sidebar-border bg-sidebar transition-[width] duration-200 md:flex',
          collapsed ? 'w-16' : 'w-60',
        )}
      >
        <div className={cn('flex h-14 items-center gap-2.5', collapsed ? 'justify-center' : 'px-4')}>
          <Logo className="size-8 shrink-0 rounded-lg" />
          {!collapsed && <span className="text-base font-semibold tracking-tight">Pacioli</span>}
        </div>
        <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2 py-2" aria-label="Principal">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              title={collapsed ? label : undefined}
              className={({ isActive }) =>
                cn(
                  'relative flex h-9 items-center gap-3 rounded-md px-3 text-sm font-medium transition-colors',
                  collapsed && 'justify-center px-0',
                  isActive
                    ? 'bg-sidebar-accent text-foreground before:absolute before:top-2 before:bottom-2 before:left-0 before:w-0.5 before:rounded-full before:bg-primary'
                    : 'text-muted-foreground hover:bg-sidebar-accent/70 hover:text-foreground',
                )
              }
            >
              <Icon className="size-4 shrink-0" />
              {!collapsed && label}
            </NavLink>
          ))}
        </nav>
        <div className={cn('flex flex-col gap-1 border-t border-sidebar-border p-2', collapsed && 'items-center')}>
          <ThemeToggle withLabel={!collapsed} />
          <Button
            variant="ghost"
            size={collapsed ? 'icon-sm' : 'sm'}
            onClick={toggleSidebar}
            aria-label={collapsed ? 'Expandir menú' : 'Contraer menú'}
            className={cn('text-muted-foreground', !collapsed && 'w-full justify-start gap-2')}
          >
            {collapsed ? <PanelLeftOpen className="size-4" /> : <PanelLeftClose className="size-4" />}
            {!collapsed && 'Contraer menú'}
          </Button>
        </div>
      </aside>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-border bg-background/90 px-4 backdrop-blur sm:px-6">
          <div className="flex items-center gap-2 md:hidden">
            <Logo className="size-7 rounded-md" />
          </div>
          <MonthPicker />
          <div className="md:hidden">
            <ThemeToggle />
          </div>
        </header>

        {/* Bottom padding keeps the last rows clear of the floating button and tab bar. */}
        <main className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-7xl px-4 pt-6 pb-36 sm:px-6 md:pb-24">
            <Suspense fallback={<PageLoader />}>
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/transactions" element={<TransactionsPage />} />
                <Route path="/budgets" element={<BudgetsPage />} />
                <Route path="/reports" element={<ReportsPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
            </Suspense>
          </div>
        </main>

        {/* Mobile tab bar */}
        <nav
          aria-label="Principal"
          className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-border bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
        >
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  'flex h-14 flex-col items-center justify-center gap-0.5 text-[0.7rem] font-medium',
                  isActive ? 'text-foreground' : 'text-muted-foreground',
                )
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    className={cn(
                      'flex h-6 w-10 items-center justify-center rounded-full',
                      isActive && 'bg-brand-soft',
                    )}
                  >
                    <Icon className="size-4" />
                  </span>
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </div>

      <NewTransactionFab />
    </div>
  )
}
