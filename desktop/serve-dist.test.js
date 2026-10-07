// Le port du serveur loopback fixe l'origine de l'UI, donc son localStorage
// (session, URL du serveur) : il doit rester le même d'un lancement à l'autre.

import { createRequire } from 'node:module'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, it, expect } from 'vitest'

const require = createRequire(import.meta.url)
const { startWebServer } = require('./serve-dist')

function distDir() {
  const dir = mkdtempSync(join(tmpdir(), 'web-dist-'))
  writeFileSync(join(dir, 'index.html'), '<!doctype html><title>ok</title>')
  return dir
}

const freePort = () => new Promise((resolve) => {
  const s = createServer().listen(0, '127.0.0.1', () => {
    const { port } = s.address()
    s.close(() => resolve(port))
  })
})

describe('startWebServer', () => {
  it('écoute sur le port demandé : même origine à chaque lancement', async () => {
    const port = await freePort()
    const url = await startWebServer(distDir(), port)
    expect(url).toBe(`http://127.0.0.1:${port}`)
    const res = await fetch(`${url}/login`) // fallback SPA
    expect(await res.text()).toContain('<title>ok</title>')
  })

  it('se replie sur un port libre si le port fixe est déjà pris', async () => {
    const port = await freePort()
    const squatter = createServer().listen(port, '127.0.0.1')
    await new Promise((r) => squatter.once('listening', r))
    const url = await startWebServer(distDir(), port)
    expect(url).not.toBe(`http://127.0.0.1:${port}`)
    expect(url).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/)
    squatter.close()
  })
})
