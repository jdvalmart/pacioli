import { AccountsSection } from '@/components/AccountsSection'
import { CreditCardsSection } from '@/components/CreditCardsSection'
import { SavingsSection } from '@/components/SavingsSection'
import { CategoriesSection } from '@/pages/CategoriesPage'

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-extrabold">Settings</h1>
        <p className="text-sm font-semibold text-muted-foreground">
          Create and manage your accounts and credit cards, and configure settings
        </p>
      </div>

      <AccountsSection />

      <CreditCardsSection />

      <SavingsSection />

      <CategoriesSection />
    </div>
  )
}
