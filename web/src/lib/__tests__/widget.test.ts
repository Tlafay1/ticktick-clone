import { describe, expect, it } from 'vitest'
import { buildWidgetSnapshot, parseWidgetAction } from '../widget'
import type { MethodToday, SlotOccurrence, Task } from '@/types'

const NOW = new Date(2026, 9, 12, 19, 0)

function occ(over: Partial<SlotOccurrence>): SlotOccurrence {
  return {
    id: 1, slot: 1, date: '2026-10-12', duration_minutes: 25, kind: 'work',
    start_at: new Date(2026, 9, 12, 20, 30).toISOString(),
    end_at: new Date(2026, 9, 12, 20, 55).toISOString(),
    status: 'planned', excuse_reason: '', task: null,
    next_action: { id: 3, title: 'Lab SQLi 1', project: 2 },
    started_at: null, focus_session: null, recovers: null,
    ...over,
  }
}

function task(title: string, due: Date | null, priority = 0): Task {
  return { id: Math.random(), title, status: 0, priority, due_date: due?.toISOString() ?? null } as Task
}

describe('buildWidgetSnapshot', () => {
  it('garde les créneaux à venir triés, en millisecondes, sans le temps libre ni le passé', () => {
    const snap = buildWidgetSnapshot(null, [
      occ({ id: 2, start_at: new Date(2026, 9, 14, 20, 30).toISOString(), end_at: new Date(2026, 9, 14, 20, 55).toISOString() }),
      occ({ id: 1 }),
      occ({ id: 3, kind: 'buffer' }),
      occ({ id: 4, status: 'honored' }),
      occ({ id: 5, start_at: new Date(2026, 9, 12, 17, 0).toISOString(), end_at: new Date(2026, 9, 12, 17, 25).toISOString() }),
    ], [], NOW)
    expect(snap.slots.map(s => s.id)).toEqual([1, 2])
    expect(snap.slots[0].start_ms).toBe(new Date(2026, 9, 12, 20, 30).getTime())
    expect(snap.slots[0].title).toBe('Lab SQLi 1')
  })

  it('liste les 3 premières tâches d\'aujourd\'hui (retards compris), pas celles de demain', () => {
    const snap = buildWidgetSnapshot(null, [], [
      task('Demain', new Date(2026, 9, 13, 9)),
      task('Ce soir', new Date(2026, 9, 12, 21)),
      task('En retard', new Date(2026, 9, 10, 9)),
      task('Sans date', null),
    ], NOW)
    expect(snap.tasks).toEqual(['En retard', 'Ce soir'])
    expect(snap.today_count).toBe(2)
  })

  it('reprend la couleur et la limite du tableau de bord quand il est là', () => {
    const today = { color: 'orange', today_count: 4, today_limit: 3 } as MethodToday
    const snap = buildWidgetSnapshot(today, [], [], NOW)
    expect([snap.color, snap.today_count, snap.today_limit]).toEqual(['orange', 4, 3])
  })
})

describe('parseWidgetAction', () => {
  it('lit les deux gestes du widget et ignore le reste', () => {
    expect(parseWidgetAction('start:12')).toEqual({ type: 'start', occurrence: 12 })
    expect(parseWidgetAction('add')).toEqual({ type: 'add' })
    expect(parseWidgetAction('start:abc')).toBeNull()
    expect(parseWidgetAction(null)).toBeNull()
  })
})
