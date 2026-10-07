import { describe, expect, it } from 'vitest'
import { plannedHabitReminders, plannedTaskReminders } from '../reminders'
import type { Habit, Task } from '@/types'

const NOW = new Date(2026, 9, 7, 18, 0) // mercredi 7 octobre 2026, 18:00 locale

function task(over: Partial<Task> = {}): Task {
  return {
    id: 1, title: 'Appeler l\'agence', status: 0,
    due_date: new Date(2026, 9, 7, 18, 30).toISOString(),
    reminders: [{ id: 7, trigger_type: 'relative', minutes_before: 10, trigger_at: null, annoying: false }],
    ...over,
  } as Task
}

function habit(over: Partial<Habit> = {}): Habit {
  return {
    id: 3, name: 'Rituel du soir', motto: '', archived: false,
    frequency: 'daily', freq_config: {},
    reminders: [{ id: 5, time: '21:30:00' }],
    due_today: true, completed_today: false,
    ...over,
  } as Habit
}

describe('plannedTaskReminders', () => {
  it('calcule l\'instant relatif et le tag partagé avec le Web Push serveur', () => {
    const [n] = plannedTaskReminders([task()], NOW, new Date(2026, 9, 8))
    const at = new Date(2026, 9, 7, 18, 20)
    expect(n.at).toEqual(at)
    expect(n.id).toBe(7)
    expect(n.tag).toBe(`reminder-7-${at.getTime() / 1000}`)
    expect(n.url).toBe('/task/1')
  })

  it('ignore les tâches terminées et les rappels hors fenêtre', () => {
    expect(plannedTaskReminders([task({ status: 2 })], NOW, new Date(2026, 9, 8))).toEqual([])
    expect(plannedTaskReminders([task()], NOW, new Date(2026, 9, 7, 18, 10))).toEqual([])
  })

  it('gère le déclencheur absolu', () => {
    const at = new Date(2026, 9, 7, 19, 0)
    const t = task({
      reminders: [{ id: 8, trigger_type: 'absolute', minutes_before: null, trigger_at: at.toISOString(), annoying: true }],
    })
    const [n] = plannedTaskReminders([t], NOW, new Date(2026, 9, 8))
    expect(n.at).toEqual(at)
    expect(n.annoying).toBe(true)
  })
})

describe('plannedHabitReminders', () => {
  it('programme une habitude quotidienne sur 7 jours à l\'heure murale', () => {
    const list = plannedHabitReminders([habit()], NOW)
    expect(list).toHaveLength(7)
    expect(list[0].at).toEqual(new Date(2026, 9, 7, 21, 30))
    expect(list[6].at).toEqual(new Date(2026, 9, 13, 21, 30))
    expect(new Set(list.map(n => n.id)).size).toBe(7) // ids natifs distincts
  })

  it('saute aujourd\'hui si l\'habitude est déjà faite ou non due', () => {
    expect(plannedHabitReminders([habit({ completed_today: true })], NOW)[0].at)
      .toEqual(new Date(2026, 9, 8, 21, 30))
    expect(plannedHabitReminders([habit({ due_today: false })], NOW)).toHaveLength(6)
  })

  it('respecte les jours précis (lundi = 0) et ignore les heures passées', () => {
    // Mercredi = 2 : seul le rappel du jour (déjà passé à 8:00) puis rien avant le mercredi suivant.
    const h = habit({ frequency: 'specific_days', freq_config: { days: [2] }, reminders: [{ id: 5, time: '08:00:00' }] })
    const list = plannedHabitReminders([h], NOW)
    expect(list).toEqual([])
    const h2 = habit({ frequency: 'specific_days', freq_config: { days: [4] }, due_today: false }) // vendredi
    expect(plannedHabitReminders([h2], NOW).map(n => n.at)).toEqual([new Date(2026, 9, 9, 21, 30)])
  })

  it('ne devine pas les jours futurs d\'une habitude à intervalle', () => {
    expect(plannedHabitReminders([habit({ frequency: 'interval' })], NOW)).toHaveLength(1)
  })
})
