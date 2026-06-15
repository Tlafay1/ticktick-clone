'use strict'

const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  notify: (opts) => ipcRenderer.invoke('notify', opts),
  cancelNotify: (id) => ipcRenderer.invoke('cancel-notify', id),
  storeGet: (key) => ipcRenderer.invoke('store-get', key),
  storeSet: (key, value) => ipcRenderer.invoke('store-set', key, value),
  storeRemove: (key) => ipcRenderer.invoke('store-remove', key),
  onNotificationAction: (cb) => ipcRenderer.on('notification-action', (_e, data) => cb(data)),
  updateTray: (data) => ipcRenderer.send('tray-update', data),
})
