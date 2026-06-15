import type { Platform } from './types'
import { webPlatform } from './web'

function detect(): Platform {
  if (typeof window === 'undefined') return webPlatform
  // Electron expose window.electronAPI via contextBridge
  if ('electronAPI' in window) {
    // Import synchrone impossible ici — on retourne l'implémentation electron chargée paresseusement
    // Pour l'instant, on retourne web ; le main.ts Electron peut écraser platform.value
    return webPlatform
  }
  // Capacitor expose window.Capacitor
  if ('Capacitor' in window) {
    // Même logique — l'app Capacitor appelle setPlatform() au démarrage
    return webPlatform
  }
  return webPlatform
}

export let platform: Platform = detect()

/** Appelé par main.ts natif pour surcharger la plateforme détectée. */
export function setPlatform(p: Platform) { platform = p }

export type { Platform, NotificationOptions } from './types'
