// Captures d'écran des vues clés (dev only). Backend :8001, front :5173.
import { chromium } from '@playwright/test'

const API = 'http://localhost:8001/api'
const APP = 'http://localhost:5173'
const OUT = process.env.SHOT_DIR || '/tmp/shots'
const THEME = process.env.THEME || 'light'

const res = await fetch(`${API}/auth/token/`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: 'demo@ticktick.local', password: 'demo12345' }),
})
const { access, refresh } = await res.json()

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
const page = await ctx.newPage()

// Injecter les tokens avant tout chargement d'app.
await page.addInitScript(([a, r, theme]) => {
  localStorage.setItem('tt.access', a)
  localStorage.setItem('tt.refresh', r)
  localStorage.setItem('tt-theme', theme)
}, [access, refresh, THEME])

const views = [
  ['today', '/today'],
  ['project', '/project/'],   // complété plus bas avec un id réel
  ['calendar', '/calendar'],
  ['kanban-redirect', '/today'],
  ['stats', '/stats'],
  ['habits', '/habits'],
  ['settings', '/settings'],
  ['eisenhower', '/eisenhower'],
]

// Récupérer un projet réel pour /project/:id et son kanban
const projects = await (await fetch(`${API}/projects/`, {
  headers: { Authorization: `Bearer ${access}` },
})).json()
const work = projects.find(p => p.name === 'Travail') || projects[0]
views[1][1] = `/project/${work.id}`

for (const [name, path] of views) {
  await page.goto(`${APP}${path}`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(800)
  await page.screenshot({ path: `${OUT}/${THEME}-${name}.png` })
  console.log('shot', name)
}

// Détail d'une tâche : cliquer la 1re tâche de la liste projet
await page.goto(`${APP}/project/${work.id}`, { waitUntil: 'networkidle' })
await page.waitForTimeout(600)
const firstTask = page.locator('.task-row').first()
if (await firstTask.count()) {
  await firstTask.click()
  await page.waitForTimeout(600)
  await page.screenshot({ path: `${OUT}/${THEME}-task-detail.png` })
  console.log('shot task-detail')
}

await browser.close()
console.log('done', THEME)
