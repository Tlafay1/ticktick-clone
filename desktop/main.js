'use strict'

const { app, BrowserWindow, Tray, Menu, globalShortcut, ipcMain, Notification, nativeImage } = require('electron')
const path = require('node:path')
const Store = require('electron-store')

const store = new Store()
let mainWindow = null
let tray = null
let quickAddWindow = null

// ── Serveur web local (mode packagé) ─────────────────────────────────────────
// En mode packagé, l'UI (web/dist embarqué) est servie par un mini serveur
// HTTP loopback — cf. serve-dist.js. En dev, on garde vite (proxy /api).

const { startWebServer } = require('./serve-dist')

let webBaseUrl = 'http://localhost:5173'

// ── Fenêtre principale ────────────────────────────────────────────────────────

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    show: false,
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
  })

  mainWindow.loadURL(webBaseUrl)
  if (!app.isPackaged) {
    mainWindow.webContents.openDevTools()
  }

  mainWindow.once('ready-to-show', () => {
    if (!app.getLoginItemSettings().wasOpenedAsHidden) {
      mainWindow.show()
    }
  })

  mainWindow.on('close', (e) => {
    if (!app.isQuitting) {
      e.preventDefault()
      mainWindow.hide()
    }
  })
}

// ── Fenêtre Quick Add (raccourci global) ─────────────────────────────────────

function createQuickAddWindow() {
  quickAddWindow = new BrowserWindow({
    width: 500,
    height: 80,
    frame: false,
    resizable: false,
    alwaysOnTop: true,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
    },
  })
  quickAddWindow.loadURL(`${webBaseUrl}/#/quick-add`)

  quickAddWindow.on('blur', () => quickAddWindow.hide())
}

function toggleQuickAdd() {
  if (!quickAddWindow) return
  if (quickAddWindow.isVisible()) {
    quickAddWindow.hide()
  } else {
    quickAddWindow.center()
    quickAddWindow.show()
    quickAddWindow.focus()
  }
}

// ── Tray ─────────────────────────────────────────────────────────────────────

function createTray() {
  const iconPath = path.join(__dirname, 'assets', 'tray-icon.png')
  const icon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 })
  tray = new Tray(icon)
  tray.setToolTip('TickTick Clone')
  updateTrayMenu()
  tray.on('double-click', () => {
    mainWindow.show()
    mainWindow.focus()
  })
}

function updateTrayMenu(todayCount = 0, focusLabel = null) {
  const menu = Menu.buildFromTemplate([
    { label: `${todayCount} tâche${todayCount !== 1 ? 's' : ''} aujourd'hui`, enabled: false },
    focusLabel ? { label: `🍅 ${focusLabel}`, enabled: false } : { type: 'separator' },
    { type: 'separator' },
    { label: 'Ouvrir TickTick Clone', click: () => { mainWindow.show(); mainWindow.focus() } },
    { label: 'Saisie rapide', accelerator: 'CmdOrCtrl+Shift+A', click: toggleQuickAdd },
    { type: 'separator' },
    { label: 'Quitter', click: () => { app.isQuitting = true; app.quit() } },
  ])
  tray.setContextMenu(menu)
}

// ── Notifications natives ─────────────────────────────────────────────────────

const scheduledNotifications = new Map()

ipcMain.handle('notify', (_e, opts) => {
  const delay = opts.at ? opts.at - Date.now() : 0
  const fire = () => {
    const n = new Notification({
      title: opts.title,
      body: opts.body,
      timeoutType: opts.persistent ? 'never' : 'default',
      actions: [
        { type: 'button', text: 'Terminer' },
        { type: 'button', text: 'Snooze 10 min' },
      ],
    })
    n.show()
    n.on('action', (_e, idx) => {
      if (idx === 0) mainWindow.webContents.send('notification-action', { id: opts.id, action: 'complete' })
      if (idx === 1) {
        // Snooze : replanifier dans 10 min
        const t = setTimeout(fire, 10 * 60_000)
        scheduledNotifications.set(opts.id, t)
      }
    })
  }
  if (delay > 0) {
    const t = setTimeout(fire, delay)
    scheduledNotifications.set(opts.id, t)
  } else {
    fire()
  }
})

ipcMain.handle('cancel-notify', (_e, id) => {
  const t = scheduledNotifications.get(id)
  if (t) { clearTimeout(t); scheduledNotifications.delete(id) }
})

ipcMain.handle('store-get', (_e, key) => store.get(key, null))
ipcMain.handle('store-set', (_e, key, value) => store.set(key, value))
ipcMain.handle('store-remove', (_e, key) => store.delete(key))

// Mise à jour du tray depuis le renderer
ipcMain.on('tray-update', (_e, data) => updateTrayMenu(data.todayCount, data.focusLabel))

// ── App lifecycle ─────────────────────────────────────────────────────────────

app.whenReady().then(async () => {
  if (app.isPackaged) {
    // web/dist est embarqué par electron-builder (extraResources → web-dist).
    webBaseUrl = await startWebServer(path.join(process.resourcesPath, 'web-dist'))
  }
  createMainWindow()
  createQuickAddWindow()
  createTray()

  // Raccourci global quick-add
  globalShortcut.register('CmdOrCtrl+Shift+A', toggleQuickAdd)

  // Lancer au démarrage (Windows)
  if (process.platform === 'win32') {
    app.setLoginItemSettings({
      openAtLogin: store.get('openAtLogin', true),
      openAsHidden: true,
    })
  }
})

app.on('window-all-closed', (e) => {
  // Ne pas quitter quand on ferme toutes les fenêtres (reste dans le tray)
  e.preventDefault()
})

app.on('will-quit', () => {
  globalShortcut.unregisterAll()
})

app.on('activate', () => {
  if (mainWindow) { mainWindow.show(); mainWindow.focus() }
})
