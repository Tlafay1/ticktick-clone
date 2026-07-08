'use strict'

// Mini serveur HTTP loopback servant le build web en mode packagé.
// L'UI buildée référence ses assets en chemins absolus (/assets/…) et son
// router est en mode history : file:// ne peut pas la servir. Module séparé
// de main.js pour être testable sans Electron (node + curl suffisent).

const http = require('node:http')
const fs = require('node:fs')
const path = require('node:path')

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.json': 'application/json',
  '.webmanifest': 'application/manifest+json',
  '.woff2': 'font/woff2',
}

/** Démarre le serveur sur un port libre du loopback ; résout l'URL de base. */
function startWebServer(distDir) {
  const root = path.resolve(distDir)
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const urlPath = decodeURIComponent(new URL(req.url, 'http://localhost').pathname)
      let filePath = path.normalize(path.join(root, urlPath))
      // Hors racine (traversée), introuvable ou dossier → fallback SPA.
      if (!filePath.startsWith(root) || !fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
        filePath = path.join(root, 'index.html')
      }
      res.setHeader('Content-Type', MIME[path.extname(filePath).toLowerCase()] || 'application/octet-stream')
      fs.createReadStream(filePath).pipe(res)
    })
    server.listen(0, '127.0.0.1', () => resolve(`http://127.0.0.1:${server.address().port}`))
  })
}

module.exports = { startWebServer }
