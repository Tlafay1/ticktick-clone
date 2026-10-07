// Calcul pur des rappels à notifier, partagé par les notifications web
// (polling en page) et la programmation locale Android. Les tags reprennent
// ceux du Web Push serveur pour que les canaux se remplacent au lieu de
// s'empiler (apps/tasks/tasks.py:reminder_tag).

import { format } from 'date-fns'
import type { Habit, MethodConfig, NestedReminder, SlotOccurrence, Task } from '@/types'

export interface PlannedNotification {
  /** Identifiant natif (entier 32 bits), stable pour une même occurrence. */
  id: number
  /** Clé de dédoublonnage, identique au tag Web Push du serveur. */
  tag: string
  at: Date
  title: string
  body: string
  url: string
  annoying: boolean
  /** Tâche concernée (actions Terminer / Snooze du desktop). */
  taskId?: number
}

// Plages d'identifiants natifs disjointes (les ids Android sont des int 32 bits).
const HABIT_ID_BASE = 1_000_000_000
const REVIEW_ID = 1_900_000_000
const SLOT_ID_BASE = 2_000_000_000

/** Instant de déclenchement d'un rappel de tâche, ou null si indéterminable. */
export function reminderTriggerAt(task: Pick<Task, 'due_date'>, r: NestedReminder): Date | null {
  if (r.trigger_type === 'absolute') return r.trigger_at ? new Date(r.trigger_at) : null
  if (task.due_date && r.minutes_before != null) {
    return new Date(new Date(task.due_date).getTime() - r.minutes_before * 60_000)
  }
  return null
}

function reminderBody(r: NestedReminder): string {
  if (!r.minutes_before) return 'Rappel'
  return `Rappel ${r.minutes_before > 0 ? r.minutes_before + ' min avant' : 'maintenant'}`
}

/** Rappels des tâches ouvertes dont l'instant tombe dans [from, to]. */
export function plannedTaskReminders(tasks: Task[], from: Date, to: Date): PlannedNotification[] {
  const out: PlannedNotification[] = []
  for (const task of tasks) {
    if (task.status !== 0) continue
    for (const r of task.reminders ?? []) {
      const at = reminderTriggerAt(task, r)
      if (!at || at < from || at > to) continue
      out.push({
        id: r.id,
        tag: `reminder-${r.id}-${Math.floor(at.getTime() / 1000)}`,
        at,
        title: `⏰ ${task.title}`,
        body: reminderBody(r),
        url: `/task/${task.id}`,
        annoying: r.annoying,
        taskId: task.id,
      })
    }
  }
  return out.sort((a, b) => a.at.getTime() - b.at.getTime())
}

/** Jour de semaine façon Python (lundi = 0), comme `freq_config.days`. */
function pyWeekday(d: Date): number {
  return (d.getDay() + 6) % 7
}

/**
 * Rappels d'habitude des `days` prochains jours, à l'heure murale locale.
 * Aujourd'hui suit `due_today`/`completed_today` (calculés par le serveur) ;
 * les jours suivants se déduisent de la fréquence, sauf l'intervalle qui
 * dépend du prochain check-in (reprogrammé à la synchro suivante).
 */
export function plannedHabitReminders(habits: Habit[], now: Date, days = 7): PlannedNotification[] {
  const out: PlannedNotification[] = []
  for (const habit of habits) {
    if (habit.archived) continue
    const specificDays = habit.frequency === 'specific_days'
      ? ((habit.freq_config.days as number[] | undefined) ?? [])
      : null
    for (let offset = 0; offset < days; offset++) {
      const day = new Date(now.getFullYear(), now.getMonth(), now.getDate() + offset)
      if (offset === 0) {
        if (!habit.due_today || habit.completed_today) continue
      } else {
        if (habit.frequency === 'interval') continue
        if (specificDays && !specificDays.includes(pyWeekday(day))) continue
      }
      for (const r of habit.reminders) {
        const [h, m] = r.time.split(':').map(Number)
        const at = new Date(day.getFullYear(), day.getMonth(), day.getDate(), h, m)
        if (at <= now) continue
        out.push({
          id: HABIT_ID_BASE + r.id * 10 + offset,
          tag: `habit-${r.id}-${format(at, 'yyyy-MM-dd')}`,
          at,
          title: habit.name,
          body: habit.motto || "C'est l'heure de votre habitude !",
          url: '/habits',
          annoying: false,
        })
      }
    }
  }
  return out.sort((a, b) => a.at.getTime() - b.at.getTime())
}

/**
 * Créneaux de la méthode à venir : une notification à l'heure, avec la
 * prochaine action (un tampon sans rattrapage est du temps libre : silence).
 */
export function plannedSlotNotifications(occurrences: SlotOccurrence[], now: Date): PlannedNotification[] {
  return occurrences
    .filter(o => o.status === 'planned' && new Date(o.start_at) > now)
    .filter(o => o.kind === 'work' || o.recovers !== null)
    .map(o => ({
      id: SLOT_ID_BASE + o.id,
      tag: `slot-${o.id}`,
      at: new Date(o.start_at),
      title: o.kind === 'buffer' ? '🎯 Rattrapage' : "🎯 C'est l'heure",
      body: o.next_action ? `${o.next_action.title} — 10 minutes suffisent.` : '10 minutes suffisent.',
      url: '/today',
      annoying: false,
    }))
}

/** Prochain rendez-vous de revue (jour + heure murale de la config). */
export function nextReviewNotification(config: MethodConfig, now: Date): PlannedNotification {
  const [h, m] = config.review_time.split(':').map(Number)
  const at = new Date(now.getFullYear(), now.getMonth(), now.getDate(), h, m)
  at.setDate(at.getDate() + ((config.review_weekday - pyWeekday(now) + 7) % 7))
  if (at <= now) at.setDate(at.getDate() + 7)
  return {
    id: REVIEW_ID,
    tag: `review-${format(at, 'yyyy-MM-dd')}`,
    at,
    title: '🗓️ Ta revue de la semaine',
    body: '10 minutes pour décider à froid.',
    url: '/review',
    annoying: false,
  }
}
