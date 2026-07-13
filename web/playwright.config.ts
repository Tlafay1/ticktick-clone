import { defineConfig, devices } from '@playwright/test'

/**
 * E2E navigateur réel. Nécessite le backend Django sur :8001 (le dev server
 * Vite proxifie /api → :8001). En CI, un job dédié démarre Postgres/Redis +
 * migrate + runserver, puis lance ces tests. En local :
 *   1. cd backend && POSTGRES_PORT=5432 uv run python manage.py runserver 8001
 *   2. cd web && npm run e2e
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
