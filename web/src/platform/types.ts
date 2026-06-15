/** Interface commune à toutes les plateformes (web, Capacitor, Electron). */

export interface NotificationOptions {
  id: number
  title: string
  body: string
  at?: Date          // programmation locale
  persistent?: boolean
}

export interface Platform {
  /** Demande la permission de notifications. Retourne true si accordée. */
  requestNotificationPermission(): Promise<boolean>
  /** Planifie ou affiche une notification. */
  scheduleNotification(opts: NotificationOptions): Promise<void>
  /** Annule une notification par son id. */
  cancelNotification(id: number): Promise<void>
  /** Stockage clé/valeur persistant. */
  store: {
    get(key: string): Promise<string | null>
    set(key: string, value: string): Promise<void>
    remove(key: string): Promise<void>
  }
  /** Vrai si l'app tourne en mode offline. */
  isOffline(): boolean
  /** Plateforme courante. */
  readonly name: 'web' | 'capacitor' | 'electron'
}
