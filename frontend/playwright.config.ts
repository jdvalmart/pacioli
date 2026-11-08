/**
 * End-to-end tests against the real app: FastAPI serving the built SPA.
 *
 * Each run starts the backend on 127.0.0.1:8099 with a brand-new data
 * directory (.e2e-data/), so tests never touch the always-on service on
 * :8000 or the real database. Run `npm run test:e2e` (it builds first).
 */
import { existsSync } from 'node:fs'
import path from 'node:path'

import { defineConfig, devices } from '@playwright/test'

const PORT = 8099
const root = path.resolve(import.meta.dirname, '..')
const venvPython = path.join(root, 'backend', '.venv', 'bin', 'python')
// Local runs use the project venv; CI installs the backend into the system Python.
const python = process.env.PACIOLI_E2E_PYTHON ?? (existsSync(venvPython) ? venvPython : 'python')
const dataDir = path.join(import.meta.dirname, '.e2e-data')

export default defineConfig({
  testDir: './e2e',
  // One shared database per run: keep tests sequential and deterministic.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    locale: 'es-CO',
    timezoneId: 'America/Bogota',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `rm -rf "${dataDir}" && "${python}" -m uvicorn app.main:app --app-dir "${path.join(root, 'backend')}" --host 127.0.0.1 --port ${PORT}`,
    url: `http://127.0.0.1:${PORT}/health`,
    reuseExistingServer: false,
    timeout: 60_000,
    env: {
      PACIOLI_DATA_DIR: dataDir,
      PACIOLI_FRONTEND_DIST: path.join(import.meta.dirname, 'dist'),
      DATABASE_URL: '',
    },
  },
})
