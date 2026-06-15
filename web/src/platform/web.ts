import type { Platform, NotificationOptions } from './types'

export const webPlatform: Platform = {
  name: 'web',

  async requestNotificationPermission() {
    if (typeof Notification === 'undefined') return false
    if (Notification.permission === 'granted') return true
    const res = await Notification.requestPermission()
    return res === 'granted'
  },

  async scheduleNotification(opts: NotificationOptions) {
    if (typeof Notification === 'undefined') return
    if (Notification.permission !== 'granted') return
    if (opts.at) {
      const delay = opts.at.getTime() - Date.now()
      if (delay > 0) {
        setTimeout(() => {
          new Notification(opts.title, {
            body: opts.body,
            tag: String(opts.id),
            requireInteraction: opts.persistent,
          })
        }, delay)
        return
      }
    }
    new Notification(opts.title, {
      body: opts.body,
      tag: String(opts.id),
      requireInteraction: opts.persistent,
    })
  },

  async cancelNotification(_id: number) {
    // Web Notifications API ne supporte pas l'annulation par ID sans SW
  },

  store: {
    async get(key: string) {
      if (typeof localStorage === 'undefined') return null
      return localStorage.getItem(key)
    },
    async set(key: string, value: string) {
      if (typeof localStorage === 'undefined') return
      localStorage.setItem(key, value)
    },
    async remove(key: string) {
      if (typeof localStorage === 'undefined') return
      localStorage.removeItem(key)
    },
  },

  isOffline() { return !navigator.onLine },
}
