import { PageHeader } from '@/components/PageHeader'
import { AccountsSection } from '@/components/AccountsSection'
import { CreditCardsSection } from '@/components/CreditCardsSection'
import { SavingsSection } from '@/components/SavingsSection'
import { CategoriesSection } from '@/components/CategoriesSection'

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Ajustes"
        description="Tus cuentas, tarjetas, ahorros y categorías"
      />

      <AccountsSection />

      <CreditCardsSection />

      <SavingsSection />

      <CategoriesSection />
    </div>
  )
}
