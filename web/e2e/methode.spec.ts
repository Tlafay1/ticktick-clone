import { test, expect } from '@playwright/test'

/**
 * Méthode (jalon 9) : un créneau ouvert propose sa prochaine action, « ▶ 10 min »
 * lance le contrat dans Focus, et la revue de la semaine se valide en un clic.
 * Tout en UTC (navigateur et compte) : l'heure du créneau est calculée ici.
 */
test.use({ timezoneId: 'UTC' })

test('créneau → 10 minutes de focus → revue validée', async ({ page, request }) => {
  const email = `e2e-methode-${Date.now()}@test.local`
  const reg = await (await request.post('/api/auth/register/', {
    data: { email, password: 'secret123' },
  })).json()
  const headers = { Authorization: `Bearer ${reg.access}` }
  await request.patch('/api/me/settings/', { headers, data: { timezone: 'UTC' } })

  const objective = await (await request.post('/api/projects/', {
    headers, data: { name: 'Objectif E2E', objective: 'active' },
  })).json()
  await request.post('/api/tasks/', { headers, data: { project: objective.id, title: 'Lab E2E' } })

  // Créneau dans 2 minutes : démarrable tout de suite (1 h d'avance permise).
  const at = new Date(Date.now() + 2 * 60_000)
  const hhmm = at.toISOString().slice(11, 16)
  const slot = await request.post('/api/slots/', {
    headers, data: { weekday: (at.getUTCDay() + 6) % 7, start_time: hhmm },
  })
  expect(slot.ok()).toBeTruthy()

  await page.goto('/login')
  await page.evaluate(([a, r]) => {
    localStorage.setItem('tt.access', a)
    localStorage.setItem('tt.refresh', r)
  }, [reg.access, reg.refresh])
  await page.goto('/today')

  await expect(page.getByText('Lab E2E')).toBeVisible({ timeout: 10_000 })
  await page.getByRole('button', { name: /10 min/ }).first().click()

  await expect(page).toHaveURL(/\/focus$/)
  await expect(page.getByText(/^(10:00|09:5\d)$/)).toBeVisible({ timeout: 10_000 })

  await page.goto('/review')
  await page.getByRole('button', { name: 'Valider la revue' }).click()
  await expect(page.getByText(/Revue validée le/)).toBeVisible({ timeout: 10_000 })
})
