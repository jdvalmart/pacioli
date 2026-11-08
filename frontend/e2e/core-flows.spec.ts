/**
 * Core user flows, driven through the real UI against a fresh database.
 * Tests run in order and share the database (see playwright.config.ts).
 */
import { expect, test, type Page } from '@playwright/test'

async function pick(page: Page, placeholder: string, option: string): Promise<void> {
  const dialog = page.getByRole('dialog')
  await dialog.getByRole('combobox').filter({ hasText: placeholder }).click()
  await page.getByRole('option', { name: option }).click()
}

test('create an account with an opening balance', async ({ page }) => {
  await page.goto('/settings')
  await page.getByRole('button', { name: 'Nueva cuenta' }).click()

  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('Nombre').fill('Banco')
  await dialog.getByLabel('Saldo inicial').fill('1.000.000')
  await dialog.getByRole('button', { name: /guardar|crear/i }).click()

  await expect(page.getByText('Banco').first()).toBeVisible()
  await expect(page.getByText('$1.000.000,00').first()).toBeVisible()
})

test('register an expense and see the account balance drop', async ({ page }) => {
  await page.goto('/transactions')
  await page.getByRole('button', { name: 'Nuevo movimiento' }).click()

  const dialog = page.getByRole('dialog')
  await dialog.getByRole('button', { name: /^Gasto/ }).click()
  await dialog.getByLabel('Monto').fill('250.000')
  await pick(page, 'Selecciona una categoría', 'Alimentación')
  await pick(page, 'Selecciona una cuenta', 'Banco')
  await dialog.getByLabel('Descripción').fill('Mercado e2e')
  await dialog.getByRole('button', { name: 'Guardar' }).click()

  const row = page.getByRole('row').filter({ hasText: 'Mercado e2e' })
  await expect(row).toContainText('Alimentación')
  await expect(row).toContainText('$250.000,00')

  await page.goto('/')
  await expect(page.getByText('$750.000,00').first()).toBeVisible()
})

test('edit and delete a movement', async ({ page }) => {
  await page.goto('/transactions')
  await page.getByRole('button', { name: 'Editar movimiento Mercado e2e' }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByRole('heading', { name: 'Editar movimiento' })).toBeVisible()
  await dialog.getByLabel('Monto').fill('200.000')
  await dialog.getByRole('button', { name: 'Guardar' }).click()

  const row = page.getByRole('row').filter({ hasText: 'Mercado e2e' })
  await expect(row).toContainText('$200.000,00')

  await page.getByRole('button', { name: 'Eliminar movimiento Mercado e2e' }).click()
  await page.getByRole('alertdialog').getByRole('button', { name: /eliminar/i }).click()
  await expect(page.getByText('Mercado e2e')).toHaveCount(0)

  // The account is back to its opening balance.
  await page.goto('/')
  await expect(page.getByText('$1.000.000,00').first()).toBeVisible()
})

test('a purchase in installments is billed one cuota per month', async ({ page, request }) => {
  // Fixed dates through the API: cutoff 10 / payment 25, bought Jan 5 ->
  // cuotas paid on Jan 25, Feb 25 and Mar 25.
  const card = await request.post('/api/credit-cards', {
    data: { name: 'Visa e2e', limit: '5000000', cutoff_day: 10, payment_day: 25 },
  })
  expect(card.ok()).toBeTruthy()
  const categories = (await (await request.get('/api/categories?type=expense')).json()) as {
    id: number
    name: string
  }[]
  const compras = categories.find((c) => c.name === 'Compras')!
  const purchase = await request.post('/api/transactions', {
    data: {
      date: '2026-01-05',
      amount: '300000',
      kind: 'gasto_tc',
      category_id: compras.id,
      card_id: (await card.json()).id,
      installments: 3,
      description: 'Televisor e2e',
    },
  })
  expect(purchase.ok()).toBeTruthy()

  for (const [month, cuota] of [
    [1, 1],
    [2, 2],
    [3, 3],
  ]) {
    await page.goto(`/transactions?month=${month}&year=2026`)
    const row = page.getByRole('row').filter({ hasText: 'Televisor e2e' })
    await expect(row).toContainText(`cuota ${cuota}/3 de $300.000,00`)
    await expect(row).toContainText('$100.000,00')
  }

  await page.goto('/transactions?month=4&year=2026')
  await expect(page.getByText('Televisor e2e')).toHaveCount(0)
})

test('the savings category is a system category that cannot be deleted', async ({ page }) => {
  await page.goto('/settings')
  await expect(page.getByText('Agrupa tus movimientos de ahorro')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Editar categoría Ahorro' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Eliminar categoría Ahorro' })).toHaveCount(0)
  // Regular categories keep their delete button.
  await expect(page.getByRole('button', { name: 'Eliminar categoría Compras' })).toBeVisible()
})
