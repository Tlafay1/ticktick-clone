// Instantané du widget Android « Prochaine action » : l'app l'écrit à chaque
// synchro, le widget (natif) le relit sans réseau. Les instants voyagent en
// millisecondes : le code natif n'a rien à parser (Android 5 n'a pas java.time).

import type { DayColor, MethodToday, OccurrenceStatus, SlotOccurrence, Task } from '@/types'

export interface WidgetSnapshot {
  updated_at: number
  /** Thème choisi dans l'app : « auto » suit le mode sombre du téléphone. */
  theme: 'auto' | 'light' | 'dark'
  color: DayColor | null
  today_count: number
  today_limit: number
  /** Jusqu'à 3 titres d'« Aujourd'hui » (en retard d'abord, puis par priorité). */
  tasks: string[]
  slots: Array<{
    id: number
    start_ms: number
    end_ms: number
    title: string
    kind: 'work' | 'buffer'
    status: OccurrenceStatus
  }>
}

const MISSED_GRACE_MS = 15 * 60_000
const MAX_SLOTS = 10

export function buildWidgetSnapshot(
  today: MethodToday | null,
  occurrences: SlotOccurrence[],
  tasks: Task[],
  now: Date,
  theme: WidgetSnapshot['theme'] = 'auto',
): WidgetSnapshot {
  const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1)
  const todays = tasks
    .filter(t => t.status === 0 && t.due_date && new Date(t.due_date) < tomorrow)
    .sort((a, b) =>
      new Date(a.due_date!).getTime() - new Date(b.due_date!).getTime() || b.priority - a.priority)
  const slots = occurrences
    // Ce que le widget peut encore proposer : à venir ou en cours, jamais le temps libre.
    .filter(o => (o.status === 'planned' || o.status === 'missed')
      && (o.kind === 'work' || o.recovers !== null)
      && new Date(o.end_at).getTime() + MISSED_GRACE_MS > now.getTime())
    .sort((a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime())
    .slice(0, MAX_SLOTS)
    .map(o => ({
      id: o.id,
      start_ms: new Date(o.start_at).getTime(),
      end_ms: new Date(o.end_at).getTime(),
      title: o.next_action?.title ?? '',
      kind: o.kind,
      status: o.status,
    }))
  return {
    updated_at: now.getTime(),
    theme,
    color: today?.color ?? null,
    today_count: today?.today_count ?? todays.length,
    today_limit: today?.today_limit ?? 3,
    tasks: todays.slice(0, 3).map(t => t.title),
    slots,
  }
}

/** Action déclenchée depuis le widget, relue par l'app à son retour au premier plan. */
export type WidgetAction = { type: 'start'; occurrence: number } | { type: 'add' }

export function parseWidgetAction(value: string | null): WidgetAction | null {
  if (!value) return null
  if (value === 'add') return { type: 'add' }
  const m = /^start:(\d+)$/.exec(value)
  return m ? { type: 'start', occurrence: Number(m[1]) } : null
}
