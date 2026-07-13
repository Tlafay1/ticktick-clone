// Intégration Electron (tray, actions de notification). No-op hors Electron.

interface ElectronAPI {
  notify(opts: { id: number; title: string; body: string; at?: number; persistent?: boolean }): void
  cancelNotify(id: number): void
  updateTray(data: { todayCount: number; focusLabel: string | null }): void
  onNotificationAction(cb: (data: { id: number; action: string }) => void): void
}

export function electronAPI(): ElectronAPI | null {
  if (typeof window === 'undefined') return null
  return (window as unknown as { electronAPI?: ElectronAPI }).electronAPI ?? null
}

// Le menu du tray affiche compteur du jour ET label focus : on fusionne les
// mises à jour partielles pour ne pas écraser l'autre moitié.
let trayState: { todayCount: number; focusLabel: string | null } = {
  todayCount: 0,
  focusLabel: null,
}

export function updateTray(patch: Partial<typeof trayState>) {
  const api = electronAPI()
  if (!api) return
  trayState = { ...trayState, ...patch }
  api.updateTray(trayState)
}
