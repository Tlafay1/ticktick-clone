import { onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { habitsApi, methodApi, occurrencesApi, tasksApi } from '@/api'
import { http } from '@/api/client'
import { electronAPI } from '@/lib/electron'
import { buildWidgetSnapshot, parseWidgetAction } from '@/lib/widget'
import { pushToast } from '@/composables/useToast'
import { useUserStore } from '@/stores/user'
import {
  nextReviewNotification, plannedHabitReminders, plannedSlotNotifications, plannedTaskReminders,
  type PlannedNotification,
} from '@/lib/reminders'
import type { MethodConfig, Task, User } from '@/types'

// Rappels côté client, toutes les 60 secondes :
// - web / Electron : notifications en page pour les rappels dus maintenant ;
// - Android : programmation locale des 7 prochains jours (l'OS les déclenche
//   même app fermée, sans dépendre de Firebase).

const NOTIFIED_KEY = 'tt.notified'
const NATIVE_HORIZON_DAYS = 7
// Plafond de notifications programmées : AlarmManager limite le nombre d'alarmes par app.
const NATIVE_MAX = 60

/** Tags déjà notifiés (persistés : un rechargement ne renotifie pas). */
function loadNotified(): Record<string, number> {
  try {
    const all: Record<string, number> = JSON.parse(localStorage.getItem(NOTIFIED_KEY) ?? '{}')
    const limit = Date.now() - 2 * 86_400_000
    for (const [tag, at] of Object.entries(all)) if (at < limit) delete all[tag]
    return all
  } catch {
    return {}
  }
}

function markNotified(tag: string) {
  const all = loadNotified()
  all[tag] = Date.now()
  try { localStorage.setItem(NOTIFIED_KEY, JSON.stringify(all)) } catch { /* stockage plein */ }
}

const isNative = () => typeof window !== 'undefined' && 'Capacitor' in window
// Écouteurs natifs posés une seule fois par session (la vue se remonte souvent).
let nativeListenersReady = false

export function useReminderNotifications() {
  const router = useRouter()
  const userStore = useUserStore()
  let timer: ReturnType<typeof setInterval> | null = null
  let stopped = false
  let lastNativeSignature = ''
  // Alertes persistantes en cours, par tag : stoppées au clic, à la fermeture
  // ou quand la tâche n'est plus ouverte.
  const repeats = new Map<string, ReturnType<typeof setInterval>>()

  function stopRepeat(tag: string) {
    const r = repeats.get(tag)
    if (r) { clearInterval(r); repeats.delete(tag) }
  }

  function showInPage(n: PlannedNotification) {
    const opts = {
      body: n.body,
      tag: n.tag,
      requireInteraction: n.annoying,
    }
    const notif = new Notification(n.title, opts)
    notif.onclick = () => { stopRepeat(n.tag); window.focus(); router.push(n.url) }
    if (!n.annoying) return
    // Annoying Alert : relance toutes les 30 s (même tag : remplace au lieu
    // d'empiler) jusqu'à interaction, 10 fois au plus.
    let count = 0
    repeats.set(n.tag, setInterval(() => {
      if (count++ >= 10) { stopRepeat(n.tag); return }
      const again = new Notification(n.title, {
        ...opts,
        body: 'Rappel persistant – cliquez pour arrêter',
        renotify: true,
      } as NotificationOptions)
      again.onclick = notif.onclick
      again.onclose = () => stopRepeat(n.tag)
    }, 30_000))
    notif.onclose = () => stopRepeat(n.tag)
  }

  // Réglages de la méthode (heure de revue) : relus au plus une fois par heure.
  let methodConfig: MethodConfig | null = null
  let methodConfigAt = 0

  /** Créneaux et revue dus maintenant (Electron n'a pas de Web Push). */
  async function dueMethodNotifications(from: Date, to: Date): Promise<PlannedNotification[]> {
    const today = new Date().toLocaleDateString('sv-SE')
    const occurrences = await occurrencesApi.list(today, today).catch(() => [])
    if (!occurrences.length) return []
    if (Date.now() - methodConfigAt > 3_600_000) {
      methodConfig = await methodApi.config().catch(() => methodConfig)
      methodConfigAt = Date.now()
    }
    const review = methodConfig ? [nextReviewNotification(methodConfig, from)] : []
    return [...plannedSlotNotifications(occurrences, from), ...review].filter(n => n.at <= to)
  }

  async function checkInPage(tasks: Task[]) {
    if (typeof Notification === 'undefined' || Notification.permission !== 'granted') return
    const now = Date.now()
    // Dû dans la minute qui vient, ou en retard de moins de 5 min.
    const from = new Date(now - 300_000)
    const to = new Date(now + 60_000)
    // La méthode ne doit jamais priver des rappels de tâches (données partielles, hors ligne…).
    const method = await dueMethodNotifications(from, to).catch(() => [])
    const due = [...plannedTaskReminders(tasks, from, to), ...method]
    const live = new Set(due.map(n => n.tag))
    for (const tag of [...repeats.keys()]) if (!live.has(tag)) stopRepeat(tag)

    const notified = loadNotified()
    for (const n of due) {
      if (notified[n.tag]) continue
      markNotified(n.tag)
      // Sous Electron : notification native du main pour les rappels de tâche
      // (actions Terminer / Snooze 10 min, id = tâche à terminer). Créneaux et
      // revue n'ont pas de tâche à terminer : notification standard.
      const eapi = electronAPI()
      if (eapi && n.taskId) {
        eapi.notify({ id: n.taskId, title: n.title, body: n.body, persistent: n.annoying })
        continue
      }
      showInPage(n)
    }
  }

  async function syncNative(tasks: Task[]) {
    const now = new Date()
    const horizon = new Date(now.getTime() + NATIVE_HORIZON_DAYS * 86_400_000)
    const day = (d: Date) => d.toLocaleDateString('sv-SE') // AAAA-MM-JJ locale
    // Hors ligne : chaque source manquante est simplement ignorée.
    const [habits, occurrences, config, today] = await Promise.all([
      habitsApi.list().catch(() => []),
      occurrencesApi.list(day(now), day(horizon)).catch(() => []),
      methodApi.config().catch(() => null),
      methodApi.today().catch(() => null),
    ])
    const { capacitorPlatform } = await import('@/platform/capacitor')
    // Le widget relit cet instantané sans réseau ; une panne ici ne doit pas priver
    // des rappels programmés juste après.
    await capacitorPlatform.updateWidget?.(
      JSON.stringify(buildWidgetSnapshot(today, occurrences, tasks, now, userStore.theme)),
    ).catch(() => {})
    const planned = [
      ...plannedTaskReminders(tasks, now, horizon),
      ...plannedHabitReminders(habits, now, NATIVE_HORIZON_DAYS),
      ...plannedSlotNotifications(occurrences, now),
      ...(config && occurrences.length ? [nextReviewNotification(config, now)] : []),
    ].sort((a, b) => a.at.getTime() - b.at.getTime()).slice(0, NATIVE_MAX)

    // Reprogrammer seulement si le plan a changé (évite de tout annuler chaque minute).
    const signature = JSON.stringify(planned.map(n => [n.id, n.at.getTime(), n.title]))
    if (signature === lastNativeSignature) return
    await capacitorPlatform.syncScheduledNotifications?.(planned.map(n => ({
      id: n.id, title: n.title, body: n.body, at: n.at, persistent: n.annoying, url: n.url,
    })))
    lastNativeSignature = signature
  }

  async function check() {
    let tasks: Task[]
    try {
      tasks = await tasksApi.list({ status: 0 })
    } catch {
      return
    }
    if (stopped) return
    if (isNative()) await syncNative(tasks).catch(() => {})
    else await checkInPage(tasks)
  }

  async function checkDailyReview() {
    if (typeof Notification === 'undefined' || Notification.permission !== 'granted') return
    let user: User
    try { user = await http.get<User>('/api/me/') } catch { return }
    const settings = user.settings
    const today = new Date().toISOString().slice(0, 10)
    const shownKey = 'tt.daily-review-shown'
    const shown: Record<string, string> = JSON.parse(localStorage.getItem(shownKey) ?? '{}')

    const now = new Date()
    const nowHHMM = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`

    if (settings.daily_review_morning && nowHHMM >= settings.daily_review_morning && shown.morning !== today) {
      shown.morning = today
      localStorage.setItem(shownKey, JSON.stringify(shown))
      new Notification('🌅 Révision du matin', { body: 'Bonne journée ! Consultez vos tâches du jour.', tag: 'daily-review-morning' })
    }
    if (settings.daily_review_evening && nowHHMM >= settings.daily_review_evening && shown.evening !== today) {
      shown.evening = today
      localStorage.setItem(shownKey, JSON.stringify(shown))
      new Notification('🌆 Révision du soir', { body: 'Bilan de la journée : quelles tâches avez-vous accomplies ?', tag: 'daily-review-evening' })
    }
  }

  /** Geste fait sur le widget pendant que l'app dormait : on l'exécute maintenant. */
  async function handleWidgetAction() {
    const { capacitorPlatform } = await import('@/platform/capacitor')
    const action = parseWidgetAction(await capacitorPlatform.consumeWidgetAction?.() ?? null)
    if (action?.type === 'start') {
      try {
        await occurrencesApi.start(action.occurrence)
        router.push('/focus')
      } catch {
        pushToast('Ce créneau ne se démarre plus — ouvre Aujourd\'hui.', 'info')
        router.push('/today')
      }
    } else if (action?.type === 'add') {
      await router.push('/today')
      setTimeout(() => window.dispatchEvent(new CustomEvent('tt:focus-quickadd')), 300)
    }
  }

  // Retour au premier plan (Android) : resynchronise tout de suite.
  function onVisible() {
    if (document.visibilityState !== 'visible') return
    handleWidgetAction().catch(() => {})
    check()
  }

  async function startNative() {
    const { capacitorPlatform } = await import('@/platform/capacitor')
    handleWidgetAction().catch(() => {})  // l'app vient peut-être d'être lancée par le widget
    if (!(await capacitorPlatform.requestNotificationPermission())) return
    document.addEventListener('visibilitychange', onVisible)
    if (nativeListenersReady) return
    nativeListenersReady = true
    const { LocalNotifications } = await import('@capacitor/local-notifications')
    await LocalNotifications.addListener('localNotificationActionPerformed', ({ notification }) => {
      const url = (notification.extra as { url?: string } | undefined)?.url
      if (url) router.push(url)
    })
    // FCM après connexion (le jeton exige d'être authentifié) : sert aux
    // événements serveur, pas aux rappels programmés localement.
    import('@/lib/push').then(m => m.registerPush()).catch(() => {})
  }

  async function start() {
    if (isNative()) {
      await startNative().catch(() => {})
    } else if (!(await requestPermission())) {
      return
    }
    if (stopped) return
    await check()
    if (!isNative()) await checkDailyReview()
    if (stopped) return  // démonté pendant les await : ne pas fuiter l'intervalle
    timer = setInterval(async () => {
      await check()
      if (!isNative()) await checkDailyReview()
    }, 60_000)
  }

  async function requestPermission() {
    if (typeof Notification === 'undefined') return false
    if (Notification.permission === 'granted') return true
    if (Notification.permission === 'denied') return false
    const res = await Notification.requestPermission()
    return res === 'granted'
  }

  function stop() {
    stopped = true
    if (timer) clearInterval(timer)
    for (const tag of [...repeats.keys()]) stopRepeat(tag)
    if (isNative()) document.removeEventListener('visibilitychange', onVisible)
  }

  // Le widget suit le thème de l'app : un changement le redessine aussitôt.
  watch(() => userStore.theme, () => { if (isNative() && !stopped) check() })

  onUnmounted(stop)

  return { start, stop }
}
