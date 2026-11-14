/** Loans: register one, pay the installment from an account, see the balance drop. */
import { expect, test } from '@playwright/test'

test('register a loan and pay its installment', async ({ page }) => {
  await page.goto('/settings')
  await page.getByRole('button', { name: 'Nuevo crédito' }).click()
  const form = page.getByRole('dialog')
  await form.getByLabel('Nombre').fill('Crédito e2e')
  await form.getByLabel('Saldo pendiente').fill('900.000')
  await form.getByLabel('Cuota mensual').fill('300.000')
  await form.getByRole('combobox').filter({ hasText: 'Categoría' }).click()
  await page.getByRole('option', { name: /Otros gastos/ }).click()
  await form.getByRole('button', { name: 'Guardar' }).click()
  await expect(form).toBeHidden()
  await expect(page.getByText('3 cuotas')).toBeVisible()

  await page.getByRole('button', { name: 'Pagar' }).last().click()
  const pay = page.getByRole('dialog')
  await pay.getByRole('combobox').filter({ hasText: 'Selecciona la cuenta' }).click()
  await page.getByRole('option', { name: /Banco/ }).click()
  await pay.getByRole('button', { name: /^Pagar \$/ }).click()
  await expect(pay).toBeHidden()

  await expect(page.getByText('$600.000').first()).toBeVisible()
  await expect(page.getByText('2 cuotas')).toBeVisible()
})
