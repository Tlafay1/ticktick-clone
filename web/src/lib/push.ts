// Enregistrement FCM (Android/Capacitor uniquement) : demande la permission,
// récupère le jeton de l'appareil et l'envoie au backend (apps/accounts/fcm.py).
// Les rappels sont programmés en local par l'app (useReminderNotifications) :
// `local_reminders` évite que le serveur les pousse en double.

import { http } from '@/api/client'

export async function registerPush(): Promise<void> {
  const { PushNotifications } = await import('@capacitor/push-notifications')

  const perm = await PushNotifications.requestPermissions()
  if (perm.receive !== 'granted') return

  await PushNotifications.addListener('registration', async ({ value }) => {
    await http.post('/api/push/fcm-token/', { token: value, local_reminders: true }).catch(() => {})
  })

  // Notification reçue app ouverte : le rappel web (toast/notification) suffit,
  // rien à faire ici. Un tap sur la notification ouvre simplement l'app.
  await PushNotifications.register()
}
