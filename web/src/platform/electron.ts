/**
 * Adaptateur Electron (Windows).
 * Communique avec le main process via contextBridge (window.electronAPI).
 */
import type { Platform, NotificationOptions } from './types'

interface ElectronAPI {
  notify(opts: { id: number; title: string; body: string; at?: number; persistent?: boolean }): void
  cancelNotify(id: number): void
  storeGet(key: string): Promise<string | null>
  storeSet(key: string, value: string): Promise<void>
  storeRemove(key: string): Promise<void>
}

function api(): ElectronAPI {
  return (window as unknown as { electronAPI: ElectronAPI }).electronAPI
}

export const electronPlatform: Platform = {
  name: 'electron',

  async requestNotificationPermission() { return true },

  async scheduleNotification(opts: NotificationOptions) {
    api().notify({
      id: opts.id,
      title: opts.title,
      body: opts.body,
      at: opts.at?.getTime(),
      persistent: opts.persistent,
    })
  },

  async cancelNotification(id: number) {
    api().cancelNotify(id)
  },

  store: {
    async get(key: string) { return api().storeGet(key) },
    async set(key: string, value: string) { return api().storeSet(key, value) },
    async remove(key: string) { return api().storeRemove(key) },
  },

  isOffline() { return !navigator.onLine },
}
