import { lazy, Suspense } from 'react'
import { ChevronLeft, ChevronRight, Landmark, LayoutDashboard, PiggyBank, ReceiptText, Tags, ChartColumnBig, MessageSquare, Loader2 } from 'lucide-react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { monthLabel, useMonth } from '@/hooks/useMonth'

// Pages load on demand so charts (Recharts) and other heavy
// dependencies only ship when their route is actually visited.
const BudgetsPage = lazy(() =>
  import('@/pages/BudgetsPage').then((m) => ({ default: m.BudgetsPage })),
)
const CategoriesPage = lazy(() =>
  import('@/pages/CategoriesPage').then((m) => ({ default: m.CategoriesPage })),
)
const ChatPage = lazy(() => import('@/pages/ChatPage').then((m) => ({ default: m.ChatPage })))
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
  { to: '/categories', label: 'Categorías', icon: Tags },
  { to: '/reports', label: 'Reportes', icon: ChartColumnBig },
  { to: '/chat', label: 'Asistente', icon: MessageSquare },
]

export default function App() {
  const { month, shiftMonth } = useMonth()

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="hidden w-60 shrink-0 flex-col border-r-2 border-border md:flex">
        <div className="flex items-center gap-2.5 px-5 py-6">
          <div className="flex size-10 items-center justify-center rounded-xl bg-primary shadow-[0_4px_0_0_color-mix(in_oklch,var(--primary),black_18%)]">
            <Landmark className="size-5 text-primary-foreground" />
          </div>
          <span className="text-xl font-black tracking-tight">Pacioli</span>
        </div>
        <nav className="flex flex-1 flex-col gap-1.5 px-3">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl border-2 px-3 py-2.5 text-sm font-bold transition-all ${
                  isActive
                    ? 'border-[color-mix(in_oklch,var(--primary),black_18%)] bg-primary text-primary-foreground shadow-[0_4px_0_0_color-mix(in_oklch,var(--primary),black_18%)]'
                    : 'border-transparent text-muted-foreground hover:bg-muted hover:text-foreground'
                }`
              }
            >
              <Icon className="size-4.5" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t-2 border-border p-4 text-xs font-semibold text-muted-foreground">
          Tus finanzas, en tus manos.
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
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

        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/transactions" element={<TransactionsPage />} />
              <Route path="/budgets" element={<BudgetsPage />} />
              <Route path="/categories" element={<CategoriesPage />} />
              <Route path="/reports" element={<ReportsPage />} />
              <Route path="/chat" element={<ChatPage />} />
            </Routes>
          </Suspense>
        </main>
      </div>
    </div>
  )
}
