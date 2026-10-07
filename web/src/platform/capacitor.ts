/**
 * Adaptateur Capacitor (Android).
 * Imports dynamiques : les plugins natifs ne sont chargés qu'à l'exécution
 * dans le WebView Capacitor (jamais sur le web).
 */
import type { Platform, NotificationOptions } from './types'

export const capacitorPlatform: Platform = {
  name: 'capacitor',

  async requestNotificationPermission() {
    const { LocalNotifications } = await import('@capacitor/local-notifications')
    const { display } = await LocalNotifications.requestPermissions()
    return display === 'granted'
  },

  async scheduleNotification(opts: NotificationOptions) {
    const { LocalNotifications } = await import('@capacitor/local-notifications')
    await LocalNotifications.schedule({
      notifications: [{
        id: opts.id,
        title: opts.title,
        body: opts.body,
        schedule: opts.at ? { at: opts.at } : undefined,
        ongoing: opts.persistent,
      }],
    })
  },

  async cancelNotification(id: number) {
    const { LocalNotifications } = await import('@capacitor/local-notifications')
    await LocalNotifications.cancel({ notifications: [{ id }] })
  },

  async syncScheduledNotifications(items: NotificationOptions[]) {
    const { LocalNotifications } = await import('@capacitor/local-notifications')
    const { notifications: pending } = await LocalNotifications.getPending()
    if (pending.length) {
      await LocalNotifications.cancel({ notifications: pending.map(n => ({ id: n.id })) })
    }
    if (!items.length) return
    await LocalNotifications.schedule({
      notifications: items.map(o => ({
        id: o.id,
        title: o.title,
        body: o.body,
        // allowWhileIdle : sinon le mode Doze retarde le rappel de plusieurs minutes.
        schedule: o.at ? { at: o.at, allowWhileIdle: true } : undefined,
        ongoing: o.persistent,
        extra: { url: o.url ?? '/' },
      })),
    })
  },

  store: {
    async get(key: string) {
      const { Preferences } = await import('@capacitor/preferences')
      const { value } = await Preferences.get({ key })
      return value
    },
    async set(key: string, value: string) {
      const { Preferences } = await import('@capacitor/preferences')
      await Preferences.set({ key, value })
    },
    async remove(key: string) {
      const { Preferences } = await import('@capacitor/preferences')
      await Preferences.remove({ key })
    },
  },

  isOffline() { return !navigator.onLine },
}
