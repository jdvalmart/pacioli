/**
 * Layout guards: the app must stay usable on a phone and the theme toggle
 * must work. Runs after core-flows, so pages have real data.
 */
import { expect, test } from '@playwright/test'

const PAGES = ['/', '/transactions', '/budgets', '/reports', '/settings']

test.describe('on a phone (390 px)', () => {
  test.use({ viewport: { width: 390, height: 844 } })

  test('no page scrolls sideways', async ({ page }) => {
    for (const url of PAGES) {
      await page.goto(url)
      await page.waitForLoadState('networkidle')
      // Content scrolls inside <main>, so measure it as well as the document.
      const overflow = await page.evaluate(() =>
        Math.max(
          ...[document.documentElement, document.querySelector('main')].map((el) =>
            el ? el.scrollWidth - el.clientWidth : 0,
          ),
        ),
      )
      expect(overflow, `${url} overflows horizontally by ${overflow}px`).toBeLessThanOrEqual(0)
    }
  })

  test('the bottom tab bar navigates between pages', async ({ page }) => {
    await page.goto('/')
    const tabs = page.getByRole('navigation', { name: 'Principal' })
    await tabs.getByRole('link', { name: 'Presupuestos' }).click()
    await expect(page.getByRole('heading', { name: 'Presupuestos', level: 1 })).toBeVisible()
    await tabs.getByRole('link', { name: 'Movimientos' }).click()
    await expect(page.getByRole('heading', { name: 'Movimientos', level: 1 })).toBeVisible()
  })
})

test('the theme toggle switches to dark and remembers it', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' })
  await page.goto('/')
  const html = page.locator('html')
  await expect(html).not.toHaveClass(/dark/)

  // system -> light -> dark
  await page.getByRole('button', { name: /Tema del sistema/ }).click()
  await page.getByRole('button', { name: /Tema claro/ }).click()
  await expect(html).toHaveClass(/dark/)

  await page.reload()
  await expect(html).toHaveClass(/dark/)
})
