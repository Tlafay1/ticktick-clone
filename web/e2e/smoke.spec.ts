import { test, expect } from '@playwright/test'

/**
 * Parcours de fumée : inscription ouverte → arrivée dans l'app → création d'une
 * tâche via le Quick Add. Chaque exécution crée un utilisateur unique.
 */
test('inscription puis création d\'une tâche', async ({ page }) => {
  const email = `e2e-${Date.now()}@test.local`

  await page.goto('/login')
  await page.getByRole('button', { name: /Créer un compte/i }).click()
  await page.getByPlaceholder('Email').fill(email)
  await page.getByPlaceholder('Mot de passe').fill('secret123')
  await page.getByRole('button', { name: "S'inscrire" }).click()

  // On arrive dans l'app : le Quick Add est visible.
  const quickAdd = page.getByText('Ajouter une tâche')
  await expect(quickAdd).toBeVisible({ timeout: 10_000 })

  // Créer une tâche.
  await quickAdd.click()
  await page.getByPlaceholder(/Titre/).fill('Ma première tâche E2E')
  await page.getByRole('button', { name: 'Ajouter' }).click()

  await expect(page.getByText('Ma première tâche E2E')).toBeVisible()
})
