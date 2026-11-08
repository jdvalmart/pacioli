import path from 'node:path'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  test: {
    // Unit tests only; end-to-end specs in e2e/ run with Playwright.
    include: ['src/**/*.test.ts'],
  },
  server: {
    proxy: {
      '/api': {
        // dev.sh exports PACIOLI_API_PORT (8001 by default, next to the service on 8000).
        target: `http://localhost:${process.env.PACIOLI_API_PORT ?? '8000'}`,
        changeOrigin: true,
      },
    },
  },
})
