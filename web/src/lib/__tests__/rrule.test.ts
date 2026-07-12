import { describe, it, expect } from 'vitest'
import { buildRRule, parseRRule, nextOccurrence, RRULE_PRESETS, buildRDates, parseRDates, isRDates } from '../rrule'

describe('buildRRule', () => {
  it('quotidien simple', () => {
    expect(buildRRule({ freq: 'DAILY' })).toBe('RRULE:FREQ=DAILY')
  })

  it('hebdomadaire toutes les 2 semaines', () => {
    expect(buildRRule({ freq: 'WEEKLY', interval: 2 })).toBe('RRULE:FREQ=WEEKLY;INTERVAL=2')
  })

  it('hebdomadaire jours spécifiques', () => {
    const r = buildRRule({ freq: 'WEEKLY', byDay: ['MO', 'WE', 'FR'] })
    expect(r).toBe('RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR')
  })

  it('mensuel', () => {
    expect(buildRRule({ freq: 'MONTHLY' })).toBe('RRULE:FREQ=MONTHLY')
  })

  it('annuel', () => {
    expect(buildRRule({ freq: 'YEARLY' })).toBe('RRULE:FREQ=YEARLY')
  })

  it('avec COUNT', () => {
    expect(buildRRule({ freq: 'DAILY', count: 5 })).toBe('RRULE:FREQ=DAILY;COUNT=5')
  })

  it('avec UNTIL (formate en UTC)', () => {
    expect(buildRRule({ freq: 'WEEKLY', until: '2026-12-31' }))
      .toBe('RRULE:FREQ=WEEKLY;UNTIL=20261231T000000Z')
  })

  it('interval=1 est omis', () => {
    expect(buildRRule({ freq: 'DAILY', interval: 1 })).toBe('RRULE:FREQ=DAILY')
  })
})

describe('parseRRule', () => {
  it('parse quotidien', () => {
    const r = parseRRule('RRULE:FREQ=DAILY')
    expect(r?.freq).toBe('DAILY')
    expect(r?.interval).toBe(1)
  })

  it('parse hebdomadaire avec INTERVAL', () => {
    const r = parseRRule('RRULE:FREQ=WEEKLY;INTERVAL=2')
    expect(r?.freq).toBe('WEEKLY')
    expect(r?.interval).toBe(2)
  })

  it('parse BYDAY', () => {
    const r = parseRRule('RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR')
    expect(r?.byDay).toEqual(['MO', 'WE', 'FR'])
  })

  it('parse UNTIL vers yyyy-MM-dd', () => {
    const r = parseRRule('RRULE:FREQ=DAILY;UNTIL=20261231T000000Z')
    expect(r?.until).toBe('2026-12-31')
  })

  it('retourne null pour une chaîne vide', () => {
    expect(parseRRule('')).toBeNull()
  })
})

describe('nextOccurrence', () => {
  const base = new Date(2026, 5, 13)  // samedi 13 juin 2026

  it('DAILY avance d\'un jour', () => {
    const next = nextOccurrence('RRULE:FREQ=DAILY', base)
    expect(next.getDate()).toBe(14)
    expect(next.getMonth()).toBe(5)
  })

  it('WEEKLY avance d\'une semaine', () => {
    const next = nextOccurrence('RRULE:FREQ=WEEKLY', base)
    expect(next.getDate()).toBe(20)
  })

  it('WEEKLY;INTERVAL=2 avance de deux semaines', () => {
    const next = nextOccurrence('RRULE:FREQ=WEEKLY;INTERVAL=2', base)
    expect(next.getDate()).toBe(27)
  })

  it('MONTHLY avance d\'un mois', () => {
    const next = nextOccurrence('RRULE:FREQ=MONTHLY', base)
    expect(next.getMonth()).toBe(6)  // juillet
  })

  it('YEARLY avance d\'un an', () => {
    const next = nextOccurrence('RRULE:FREQ=YEARLY', base)
    expect(next.getFullYear()).toBe(2027)
  })

  // BYDAY
  it('WEEKLY;BYDAY=MO,WE,FR depuis un samedi → lundi suivant', () => {
    // base = samedi 13 juin → prochain MO = 15 juin
    const next = nextOccurrence('RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR', base)
    expect(next.getDate()).toBe(15)
    expect(next.getDay()).toBe(1)  // lundi
  })

  it('WEEKLY;BYDAY=MO,WE,FR depuis un lundi → mercredi', () => {
    const lundi = new Date(2026, 5, 15)  // lundi 15 juin
    const next = nextOccurrence('RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR', lundi)
    expect(next.getDate()).toBe(17)
    expect(next.getDay()).toBe(3)  // mercredi
  })

  it('WEEKLY;BYDAY=MO,WE,FR depuis un vendredi → lundi suivant', () => {
    const vendredi = new Date(2026, 5, 19)  // vendredi 19 juin
    const next = nextOccurrence('RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR', vendredi)
    expect(next.getDate()).toBe(22)
    expect(next.getDay()).toBe(1)  // lundi
  })

  it('WEEKLY;BYDAY=SA,SU depuis un vendredi → samedi', () => {
    const vendredi = new Date(2026, 5, 19)
    const next = nextOccurrence('RRULE:FREQ=WEEKLY;BYDAY=SA,SU', vendredi)
    expect(next.getDate()).toBe(20)
    expect(next.getDay()).toBe(6)  // samedi
  })

  // UNTIL
  it('respecte UNTIL : retourne from si plus d\'occurrences', () => {
    // UNTIL dans le passé par rapport à base
    const next = nextOccurrence('RRULE:FREQ=DAILY;UNTIL=20260601T000000Z', base)
    expect(next).toBe(base)  // même référence = signal "fini"
  })

  it('retourne la date si UNTIL dans le futur', () => {
    const next = nextOccurrence('RRULE:FREQ=DAILY;UNTIL=20261231T000000Z', base)
    expect(next.getDate()).toBe(14)  // lendemain normal
  })
})

describe('RRULE_PRESETS', () => {
  it('contient les 5 presets TickTick', () => {
    expect(RRULE_PRESETS).toHaveLength(5)
    const rrules = RRULE_PRESETS.map(p => p.rrule)
    expect(rrules).toContain('RRULE:FREQ=DAILY')
    expect(rrules).toContain('RRULE:FREQ=WEEKLY')
    expect(rrules).toContain('RRULE:FREQ=MONTHLY')
    expect(rrules).toContain('RRULE:FREQ=YEARLY')
  })
})

describe('dates spécifiques (RDATE)', () => {
  it('build + parse aller-retour (tri, dédup)', () => {
    const s = buildRDates(['2026-09-15', '2026-08-01', '2026-08-01'])
    expect(s).toBe('RDATE:20260801T000000,20260915T000000')
    expect(isRDates(s)).toBe(true)
    expect(parseRDates(s)).toEqual(['2026-08-01', '2026-09-15'])
  })

  it('liste vide → chaîne vide', () => {
    expect(buildRDates([])).toBe('')
  })

  it('nextOccurrence avance à la prochaine date de la liste', () => {
    const s = buildRDates(['2026-08-01', '2026-09-15'])
    const next = nextOccurrence(s, new Date('2026-07-13T10:00:00'))
    expect(next.getMonth()).toBe(7)  // août
    expect(next.getDate()).toBe(1)
    const next2 = nextOccurrence(s, next)
    expect(next2.getMonth()).toBe(8)  // septembre
    expect(next2.getDate()).toBe(15)
  })

  it('plus de dates après from → retourne from (fin de récurrence)', () => {
    const s = buildRDates(['2026-08-01'])
    const from = new Date('2026-09-01T00:00:00')
    expect(nextOccurrence(s, from)).toEqual(from)
  })
})
