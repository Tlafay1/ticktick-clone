/** Abonnement aux notifications Web Push (VAPID) côté navigateur. */
import { http } from '@/api/client'
import { pushToast } from '@/composables/useToast'

function urlBase64ToUint8Array(base64: string): Uint8Array {
  const padding = '='.repeat((4 - (base64.length % 4)) % 4)
  const b64 = (base64 + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(b64)
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)))
}

export function pushSupported(): boolean {
  return 'serviceWorker' in navigator && 'PushManager' in window
}

/** Demande la permission et enregistre l'abonnement push auprès du backend. */
export async function enablePushNotifications(): Promise<boolean> {
  if (!pushSupported()) {
    pushToast("Notifications push non supportées par ce navigateur.", 'error')
    return false
  }
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') {
    pushToast('Permission de notification refusée.', 'error')
    return false
  }

  const { public_key } = await http.get<{ public_key: string }>('/api/push/public-key/')
  if (!public_key) {
    pushToast('Web Push non configuré côté serveur (clés VAPID manquantes).', 'error')
    return false
  }

  const reg = await navigator.serviceWorker.ready
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(public_key) as BufferSource,
  })

  await http.post('/api/push/subscribe/', sub.toJSON())
  pushToast('Notifications activées sur cet appareil.', 'success')
  return true
}
