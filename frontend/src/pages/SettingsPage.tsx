import { AccountsSection } from '@/components/AccountsSection'
import { CreditCardsSection } from '@/components/CreditCardsSection'
import { SavingsSection } from '@/components/SavingsSection'
import { CategoriesSection } from '@/pages/CategoriesPage'

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-extrabold">Ajustes</h1>
        <p className="text-sm font-semibold text-muted-foreground">
          Creá y gestioná tus cuentas y tarjetas de crédito, y configurá la app
        </p>
      </div>

      <AccountsSection />

      <CreditCardsSection />

      <SavingsSection />

      <CategoriesSection />
    </div>
  )
}
