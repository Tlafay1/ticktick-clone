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

// Port FIXE : l'origine (http://127.0.0.1:<port>) délimite le localStorage où
// vivent la session et l'URL du serveur. Un port aléatoire changeait d'origine à
// chaque lancement — donc déconnexion à chaque démarrage de Windows.
const DEFAULT_PORT = 47821

/**
 * Démarre le serveur sur le loopback ; résout l'URL de base. Port fixe, sauf
 * s'il est pris par un autre programme : repli sur un port libre (l'app
 * démarre, au prix d'une reconnexion).
 */
function startWebServer(distDir, port = DEFAULT_PORT) {
  const root = path.resolve(distDir)
  return new Promise((resolve, reject) => {
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
    const listen = (p) => server.listen(p, '127.0.0.1')
    server.on('listening', () => resolve(`http://127.0.0.1:${server.address().port}`))
    server.on('error', (err) => {
      if (err.code === 'EADDRINUSE' && port !== 0) {
        port = 0
        listen(0)
      } else {
        reject(err)
      }
    })
    listen(port)
  })
}

module.exports = { startWebServer, DEFAULT_PORT }
