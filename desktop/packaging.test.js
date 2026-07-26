// Garde-fous sur la chaîne d'installation Windows. Ces invariants ne cassent
// ni le build ni le lancement en dev : ils ne se voient qu'à l'installation
// d'un exe déjà publié, donc trop tard.

import { createRequire } from 'node:module'
import { readFileSync } from 'node:fs'
import { describe, it, expect } from 'vitest'

const require = createRequire(import.meta.url)
const pkg = require('./package.json')
const mainSrc = readFileSync(new URL('./main.js', import.meta.url), 'utf8')

describe('contrôle « app en cours d\'exécution » de l\'installeur', () => {
  const nsh = readFileSync(new URL('./build/installer.nsh', import.meta.url), 'utf8')

  // electron-builder n'insère notre macro que sous ce nom exact
  // (allowOnlyOneInstallerInstance.nsh : `!ifmacrodef customCheckAppRunning`).
  // Une faute de frappe ne casse pas le build : elle rétablit silencieusement
  // le contrôle par défaut, qui bloque l'installation sur une boîte de dialogue.
  it('définit la macro au nom attendu par electron-builder', () => {
    expect(nsh).toMatch(/^!macro\s+customCheckAppRunning\s*$/m)
  })

  // L'app vit dans le tray : un taskkill sans /f ne fait que masquer sa fenêtre.
  it('ferme l\'app de force', () => {
    expect(nsh).toMatch(/taskkill\.exe["`\s].*\/f\b/)
  })

  // Le fichier n'est inclus que s'il s'appelle installer.nsh dans buildResources
  // (défaut : « build »), sauf nsis.include explicite.
  it('est déposé là où electron-builder le cherche', () => {
    const { buildResources } = pkg.build.directories ?? {}
    expect(buildResources ?? 'build').toBe('build')
    expect(pkg.build.nsis?.include).toBeUndefined()
  })
})

describe('sortie propre du main process', () => {
  // Sans ce drapeau, le handler `close` annule la sortie : l'installeur ne peut
  // pas fermer l'app et electron-updater n'applique jamais sa mise à jour.
  // Vérification statique — le comportement lui-même demande un vrai Electron.
  it('marque isQuitting sur before-quit', () => {
    expect(mainSrc).toMatch(/on\('before-quit'[\s\S]{0,120}?isQuitting\s*=\s*true/)
  })

  it('ne tolère qu\'une instance', () => {
    expect(mainSrc).toContain('requestSingleInstanceLock')
  })
})

describe('contenu du paquet', () => {
  // Un module local oublié dans `files` donne un MODULE_NOT_FOUND au premier
  // lancement de l'app installée, jamais avant.
  it('embarque tous les modules locaux requis par le main process', () => {
    const entries = ['main.js', 'preload.js', 'serve-dist.js']
    for (const entry of entries) {
      const src = readFileSync(new URL(`./${entry}`, import.meta.url), 'utf8')
      for (const [, rel] of src.matchAll(/require\('\.\/([^']+)'\)/g)) {
        const file = rel.endsWith('.js') ? rel : `${rel}.js`
        expect(pkg.build.files, `${entry} requiert ./${rel}`).toContain(file)
      }
    }
  })
})
