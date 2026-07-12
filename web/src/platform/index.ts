import type { Platform } from './types'
import { webPlatform } from './web'
import { electronPlatform } from './electron'

function detect(): Platform {
  if (typeof window === 'undefined') return webPlatform
  // Electron expose window.electronAPI via contextBridge (preload.js)
  if ('electronAPI' in window) return electronPlatform
  // Capacitor : l'app native appelle setPlatform() au démarrage (l'adaptateur
  // n'est pas importé ici pour garder @capacitor/* hors du build web).
  return webPlatform
}

export let platform: Platform = detect()

/** Appelé par main.ts natif pour surcharger la plateforme détectée. */
export function setPlatform(p: Platform) { platform = p }

export type { Platform, NotificationOptions } from './types'
