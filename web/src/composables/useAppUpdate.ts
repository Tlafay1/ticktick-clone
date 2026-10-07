// Mise à jour de l'app Android : Android n'installe pas d'APK en silence hors
// Play Store. On compare la version embarquée à la dernière release GitHub et
// on propose l'APK en un geste (le navigateur le télécharge, Android l'installe).

import { pushToast } from '@/composables/useToast'
import { isNewerVersion } from '@/lib/version'

const LATEST_RELEASE = 'https://api.github.com/repos/Tlafay1/ticktick-clone/releases/latest'
const CHECK_EVERY_MS = 6 * 3_600_000

interface Release {
  tag_name: string
  assets: Array<{ name: string; browser_download_url: string }>
}

let lastCheck = 0

export async function checkAppUpdate(): Promise<void> {
  if (!('Capacitor' in window) || !__APP_VERSION__) return
  if (Date.now() - lastCheck < CHECK_EVERY_MS) return
  lastCheck = Date.now()
  let release: Release
  try {
    const res = await fetch(LATEST_RELEASE, { headers: { Accept: 'application/vnd.github+json' } })
    if (!res.ok) return
    release = await res.json()
  } catch {
    return // hors ligne : on réessaiera au prochain retour au premier plan
  }
  const apk = release.assets.find(a => a.name.endsWith('.apk'))
  if (!apk || !isNewerVersion(__APP_VERSION__, release.tag_name)) return
  pushToast(`Nouvelle version ${release.tag_name} disponible`, 'info', 0, {
    label: 'Installer',
    // URL externe : Capacitor la confie au navigateur, qui télécharge l'APK.
    run: () => { window.location.href = apk.browser_download_url },
  })
}

/** Vérifie au démarrage puis à chaque retour au premier plan (au plus toutes les 6 h). */
export function watchAppUpdates() {
  checkAppUpdate()
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') checkAppUpdate()
  })
}
