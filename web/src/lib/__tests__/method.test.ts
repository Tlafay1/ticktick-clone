import { describe, expect, it } from 'vitest'
import { canStart, hhmm, occurrenceLabel, scorePercent, todayLimitState } from '../method'
import type { SlotOccurrence } from '@/types'

function occ(over: Partial<SlotOccurrence> = {}): SlotOccurrence {
  return {
    id: 1, slot: 1, date: '2026-10-12', duration_minutes: 25, kind: 'work',
    start_at: new Date(2026, 9, 12, 20, 30).toISOString(),
    end_at: new Date(2026, 9, 12, 20, 55).toISOString(),
    status: 'planned', excuse_reason: '', task: null, next_action: null,
    started_at: null, focus_session: null, recovers: null,
    ...over,
  }
}

describe('canStart', () => {
  it('suit la règle serveur : le jour même, au plus tôt 1 h avant', () => {
    expect(canStart(occ(), new Date(2026, 9, 12, 19, 29))).toBe(false)
    expect(canStart(occ(), new Date(2026, 9, 12, 19, 30))).toBe(true)
    expect(canStart(occ({ status: 'missed' }), new Date(2026, 9, 12, 23, 0))).toBe(true)
    expect(canStart(occ(), new Date(2026, 9, 13, 8, 0))).toBe(false)
  })

  it('refuse une occurrence déjà faite ou excusée', () => {
    expect(canStart(occ({ status: 'honored' }), new Date(2026, 9, 12, 20, 30))).toBe(false)
    expect(canStart(occ({ status: 'excused' }), new Date(2026, 9, 12, 20, 30))).toBe(false)
  })
})

describe('libellés', () => {
  it('précise la raison d\'une excuse', () => {
    expect(occurrenceLabel({ status: 'excused', excuse_reason: 'joker' })).toBe('Excusé (joker)')
    expect(occurrenceLabel({ status: 'missed', excuse_reason: '' })).toBe('Raté')
  })

  it('formate heures et score', () => {
    expect(hhmm('20:30:00')).toBe('20:30')
    expect(scorePercent(0.5)).toBe('50 %')
    expect(scorePercent(null)).toBe('—')
  })
})

describe('todayLimitState', () => {
  it('distingue sous, à et au-delà de la limite', () => {
    expect(todayLimitState(2, 3)).toBe('ok')
    expect(todayLimitState(3, 3)).toBe('full')
    expect(todayLimitState(4, 3)).toBe('over')
  })
})
