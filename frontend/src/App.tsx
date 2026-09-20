import { ChevronLeft, ChevronRight, Landmark, LayoutDashboard, PiggyBank, ReceiptText, Tags, ChartColumnBig, MessageSquare } from 'lucide-react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { monthLabel, useMonth } from '@/hooks/useMonth'
import { BudgetsPage } from '@/pages/BudgetsPage'
import { CategoriesPage } from '@/pages/CategoriesPage'
import { ChatPage } from '@/pages/ChatPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { ReportsPage } from '@/pages/ReportsPage'
import { TransactionsPage } from '@/pages/TransactionsPage'

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
      <aside className="hidden w-56 shrink-0 flex-col border-r border-border md:flex">
        <div className="flex items-center gap-2 px-4 py-5">
          <Landmark className="size-6 text-primary" />
          <span className="text-lg font-semibold tracking-tight">Pacioli</span>
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-3">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                }`
              }
            >
              <Icon className="size-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-border p-4 text-xs text-muted-foreground">
          Tus finanzas, en tus manos.
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-background/95 px-4 py-3 backdrop-blur sm:px-6">
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" onClick={() => shiftMonth(-1)} aria-label="Mes anterior">
              <ChevronLeft />
            </Button>
            <span className="w-36 text-center text-sm font-semibold sm:w-44">{monthLabel(month)}</span>
            <Button variant="ghost" size="icon" onClick={() => shiftMonth(1)} aria-label="Mes siguiente">
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
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/transactions" element={<TransactionsPage />} />
            <Route path="/budgets" element={<BudgetsPage />} />
            <Route path="/categories" element={<CategoriesPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/chat" element={<ChatPage />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
