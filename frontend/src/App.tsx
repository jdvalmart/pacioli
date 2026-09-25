import { lazy, Suspense, useState } from 'react'
import { ChevronLeft, ChevronRight, LayoutDashboard, PiggyBank, Plus, ReceiptText, ChartColumnBig, Settings, Loader2 } from 'lucide-react'
import { NavLink, Route, Routes, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { ChatBubble } from '@/components/ChatBubble'
import { Logo } from '@/components/Logo'
import { monthLabel, useMonth } from '@/hooks/useMonth'
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
      <Loader2 className="size-6 animate-spin" />
    </div>
  )
}

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/transactions', label: 'Transacciones', icon: ReceiptText },
  { to: '/budgets', label: 'Presupuestos', icon: PiggyBank },
  { to: '/reports', label: 'Reportes', icon: ChartColumnBig },
  { to: '/settings', label: 'Configuración', icon: Settings },
]

function NewTransactionFab() {
  const navigate = useNavigate()
  return (
    <button
      type="button"
      onClick={() => navigate('/transactions?new=1')}
      className="fixed right-6 bottom-6 z-50 flex size-14 items-center justify-center rounded-full bg-rose-500 text-white shadow-lg shadow-rose-500/30 transition-all hover:scale-105 hover:shadow-xl active:scale-95"
      aria-label="Nueva transacción"
    >
      <Plus className="size-6" />
    </button>
  )
}

export default function App() {
  const { month, shiftMonth } = useMonth()
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem('pacioli-sidebar') === 'collapsed',
  )

  const toggleSidebar = () => {
    setCollapsed((prev) => {
      const next = !prev
      localStorage.setItem('pacioli-sidebar', next ? 'collapsed' : 'expanded')
      return next
    })
  }

  return (
    <div
      className="flex h-screen overflow-hidden bg-background"
      style={{ '--sidebar-w': collapsed ? '5rem' : '15rem' } as React.CSSProperties}
    >
      <aside
        className={cn(
          'relative hidden shrink-0 flex-col border-r-2 border-border transition-all duration-200 md:flex',
          collapsed ? 'w-20' : 'w-60',
        )}
      >
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label={collapsed ? 'Expandir menú' : 'Contraer menú'}
          className="absolute top-6 -right-3 z-20 hidden size-6 items-center justify-center rounded-full border-2 border-border bg-card text-muted-foreground shadow-sm transition-colors hover:text-foreground md:flex"
        >
          {collapsed ? <ChevronRight className="size-3.5" /> : <ChevronLeft className="size-3.5" />}
        </button>
        <div
          className={cn(
            'flex items-center gap-2.5 py-6',
            collapsed ? 'justify-center px-2' : 'px-5',
          )}
        >
          <Logo className="size-10 shrink-0 rounded-xl shadow-sm" />
          {!collapsed && (
            <span className="font-heading text-xl font-extrabold tracking-tight">Pacioli</span>
          )}
        </div>
        <nav className="flex flex-1 flex-col gap-1.5 overflow-y-auto px-3">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              title={collapsed ? label : undefined}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-bold transition-all',
                  collapsed && 'justify-center px-0',
                  isActive
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                )
              }
            >
              <Icon className="size-4.5 shrink-0" />
              {!collapsed && label}
            </NavLink>
          ))}
        </nav>
        {!collapsed && (
          <div className="border-t-2 border-border p-3">
            <p className="px-3 text-xs font-semibold text-muted-foreground">
              Tus finanzas, en tus manos.
            </p>
          </div>
        )}
      </aside>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b-2 border-border bg-background/95 px-4 py-3 backdrop-blur sm:px-6">
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="icon-sm"
              className="rounded-full"
              onClick={() => shiftMonth(-1)}
              aria-label="Mes anterior"
            >
              <ChevronLeft />
            </Button>
            <span className="w-36 text-center text-sm font-extrabold sm:w-44">
              {monthLabel(month)}
            </span>
            <Button
              variant="outline"
              size="icon-sm"
              className="rounded-full"
              onClick={() => shiftMonth(1)}
              aria-label="Mes siguiente"
            >
              <ChevronRight />
            </Button>
          </div>
          <nav className="flex gap-1 md:hidden">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to}>
                {({ isActive }) => (
                  <Button variant={isActive ? 'secondary' : 'ghost'} size="sm">
                    <Icon className="mr-1 size-4" />
                    {label}
                  </Button>
                )}
              </NavLink>
            ))}
          </nav>
        </header>

        <main className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6">
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/transactions" element={<TransactionsPage />} />
              <Route path="/budgets" element={<BudgetsPage />} />
              <Route path="/reports" element={<ReportsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </Suspense>
        </main>
      </div>

      <ChatBubble />
      <NewTransactionFab />
    </div>
  )
}
