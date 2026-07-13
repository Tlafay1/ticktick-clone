import { describe, expect, it } from 'vitest'
import { dueLabel, dueTone, postponeTarget, toLocalInput, toDateInput } from '../dates'

const day = (y: number, m: number, d: number, h = 0, min = 0) =>
  new Date(y, m, d, h, min).toISOString()

describe('dueLabel', () => {
  it('affiche l\'heure quand la tâche n\'est pas all-day', () => {
    const today = new Date()
    const iso = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 14, 30)
    expect(dueLabel(iso.toISOString(), false)).toMatch(/Aujourd'hui 14:30/)
  })

  it('dit "Aujourd\'hui" pour aujourd\'hui en all-day', () => {
    const t = new Date()
    expect(dueLabel(day(t.getFullYear(), t.getMonth(), t.getDate()), true)).toBe("Aujourd'hui")
  })

  it('renvoie vide sans date', () => {
    expect(dueLabel(null, true)).toBe('')
  })
})

describe('dueTone', () => {
  it('overdue pour une date passée non terminée', () => {
    expect(dueTone(day(2020, 0, 1), true, 0)).toBe('overdue')
  })
  it('muted si terminé', () => {
    expect(dueTone(day(2020, 0, 1), true, 2)).toBe('muted')
  })
})

describe('postponeTarget', () => {
  it('+1d ajoute un jour en conservant l\'heure', () => {
    const base = new Date(2026, 5, 12, 9, 0)
    const r = postponeTarget('+1d', base.toISOString())
    expect(r.getDate()).toBe(13)
    expect(r.getHours()).toBe(9)
  })
  it('next-week ajoute 7 jours', () => {
    const base = new Date(2026, 5, 12)
    expect(postponeTarget('next-week', base.toISOString()).getDate()).toBe(19)
  })
})

describe('toLocalInput', () => {
  it('formate un ISO en yyyy-MM-ddTHH:mm (heure locale)', () => {
    const local = new Date(2026, 5, 15, 14, 30)  // heure locale
    const result = toLocalInput(local.toISOString())
    expect(result).toBe('2026-06-15T14:30')
  })
  it('retourne vide pour null', () => {
    expect(toLocalInput(null)).toBe('')
  })
})

describe('toDateInput', () => {
  it('formate en yyyy-MM-dd sans heure', () => {
    const local = new Date(2026, 5, 15, 14, 30)
    expect(toDateInput(local.toISOString())).toBe('2026-06-15')
  })
  it('retourne vide pour null', () => {
    expect(toDateInput(null)).toBe('')
  })
})
