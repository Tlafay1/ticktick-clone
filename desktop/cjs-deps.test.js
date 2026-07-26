// Garde-fou : main.js est en CommonJS, donc toute dépendance qu'il `require()`
// doit l'être aussi. Une dépendance ESM-only (`"type": "module"`) ne casse
// qu'au lancement de l'app packagée — jamais au build — d'où ce test.
// Régression : electron-store ≥ 9 est ESM-only (ERR_REQUIRE_ESM).

import { createRequire } from 'node:module'
import { describe, it, expect } from 'vitest'

const require = createRequire(import.meta.url)
const { dependencies } = require('./package.json')

describe('dépendances du main process', () => {
  for (const name of Object.keys(dependencies)) {
    it(`${name} est requérable en CommonJS`, () => {
      const pkg = require(`${name}/package.json`)
      expect(pkg.type ?? 'commonjs').toBe('commonjs')
    })
  }
})
