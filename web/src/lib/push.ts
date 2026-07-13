// Enregistrement FCM (Android/Capacitor uniquement) : demande la permission,
// récupère le jeton de l'appareil et l'envoie au backend qui pousse ensuite
// les rappels via FCM HTTP v1 (apps/accounts/fcm.py).

import { http } from '@/api/client'

export async function registerPush(): Promise<void> {
  const { PushNotifications } = await import('@capacitor/push-notifications')

  const perm = await PushNotifications.requestPermissions()
  if (perm.receive !== 'granted') return

  await PushNotifications.addListener('registration', async ({ value }) => {
    await http.post('/api/push/fcm-token/', { token: value }).catch(() => {})
  })

  // Notification reçue app ouverte : le rappel web (toast/notification) suffit,
  // rien à faire ici. Un tap sur la notification ouvre simplement l'app.
  await PushNotifications.register()
}
