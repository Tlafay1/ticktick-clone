/**
 * Adaptateur Capacitor (Android).
 * Les imports @capacitor/* sont résolus au moment du build Capacitor ;
 * sur web ils sont absent → l'arbre de module ne doit jamais importer ce fichier.
 */
import type { Platform, NotificationOptions } from './types'

// Import dynamique pour éviter les erreurs au build web
async function getLocalNotifications() {
  // @ts-ignore — résolu uniquement dans le contexte Capacitor
  const { LocalNotifications } = await import('@capacitor/local-notifications')
  return LocalNotifications as { requestPermissions: () => Promise<{ display: string }>; schedule: (o: unknown) => Promise<void>; cancel: (o: unknown) => Promise<void> }
}
async function getPreferences() {
  // @ts-ignore — résolu uniquement dans le contexte Capacitor
  const { Preferences } = await import('@capacitor/preferences')
  return Preferences as { get: (o: { key: string }) => Promise<{ value: string | null }>; set: (o: { key: string; value: string }) => Promise<void>; remove: (o: { key: string }) => Promise<void> }
}

export const capacitorPlatform: Platform = {
  name: 'capacitor',

  async requestNotificationPermission() {
    const LN = await getLocalNotifications()
    const { display } = await LN.requestPermissions()
    return display === 'granted'
  },

  async scheduleNotification(opts: NotificationOptions) {
    const LN = await getLocalNotifications()
    await LN.schedule({
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
    const LN = await getLocalNotifications()
    await LN.cancel({ notifications: [{ id }] })
  },

  store: {
    async get(key: string) {
      const P = await getPreferences()
      const { value } = await P.get({ key })
      return value
    },
    async set(key: string, value: string) {
      const P = await getPreferences()
      await P.set({ key, value })
    },
    async remove(key: string) {
      const P = await getPreferences()
      await P.remove({ key })
    },
  },

  isOffline() { return !navigator.onLine },
}
