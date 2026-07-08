import { onUnmounted } from 'vue'
import { tasksApi, remindersApi } from '@/api'
import { http } from '@/api/client'
import type { User } from '@/types'

// Vérifie les rappels dus toutes les 60 secondes et déclenche des notifications navigateur.
// Garde une trace des rappels déjà notifiés pour éviter les doublons.

const notified = new Set<number>()

export function useReminderNotifications() {
  let timer: ReturnType<typeof setInterval> | null = null

  async function requestPermission() {
    if (typeof Notification === 'undefined') return false
    if (Notification.permission === 'granted') return true
    if (Notification.permission === 'denied') return false
    const res = await Notification.requestPermission()
    return res === 'granted'
  }

  async function check() {
    if (typeof Notification === 'undefined') return
    if (Notification.permission !== 'granted') return

    const now = new Date()
    // Récupère les tâches avec rappel dû dans la prochaine minute
    let tasks: Awaited<ReturnType<typeof tasksApi.list>>
    try {
      tasks = await tasksApi.list({ status: 0 })
    } catch {
      return
    }

    for (const task of tasks) {
      if (!task.due_date) continue
      let reminders: Awaited<ReturnType<typeof remindersApi.list>>
      try {
        reminders = await remindersApi.list(task.id)
      } catch {
        continue
      }
      for (const r of reminders) {
        if (notified.has(r.id)) continue

        let triggerAt: Date | null = null
        if (r.trigger_type === 'absolute' && r.trigger_at) {
          triggerAt = new Date(r.trigger_at)
        } else if (r.trigger_type === 'relative' && task.due_date && r.minutes_before != null) {
          triggerAt = new Date(new Date(task.due_date).getTime() - r.minutes_before * 60_000)
        }

        if (!triggerAt) continue
        const diff = triggerAt.getTime() - now.getTime()
        // Notifie si le rappel est dû dans les 60 prochaines secondes ou en retard de moins de 5 min
        if (diff <= 60_000 && diff >= -300_000) {
          notified.add(r.id)
          const n = new Notification(`⏰ ${task.title}`, {
            body: r.minutes_before
              ? `Rappel ${r.minutes_before > 0 ? r.minutes_before + ' min avant' : 'maintenant'}`
              : 'Rappel',
            tag: `reminder-${r.id}`,
            requireInteraction: r.annoying,
          })
          if (r.annoying) {
            // Annoying Alert : relance la notification toutes les 30 s jusqu'à interaction
            let count = 0
            const repeat = setInterval(() => {
              if (count++ > 10) { clearInterval(repeat); return }
              new Notification(`⏰ ${task.title}`, {
                body: 'Rappel persistant – cliquez pour arrêter',
                tag: `reminder-${r.id}-repeat-${count}`,
                requireInteraction: true,
              })
            }, 30_000)
            n.onclick = () => clearInterval(repeat)
          }
        }
      }
    }
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

  async function start() {
    const ok = await requestPermission()
    if (!ok) return
    await check()
    await checkDailyReview()
    timer = setInterval(async () => { await check(); await checkDailyReview() }, 60_000)
  }

  function stop() {
    if (timer) clearInterval(timer)
  }

  onUnmounted(stop)

  return { start, stop }
}
