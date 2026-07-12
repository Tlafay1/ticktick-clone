/**
 * Constructeur / parseur RRULE simplifié (sous-ensemble TickTick).
 * RFC 5545 — seules les options utilisées dans l'app sont implémentées.
 */

export type RRuleFreq = 'DAILY' | 'WEEKLY' | 'MONTHLY' | 'YEARLY'

export interface RRuleOptions {
  freq: RRuleFreq
  interval?: number
  byDay?: string[]    // MO, TU, WE, TH, FR, SA, SU (ou +1MO pour MONTHLY)
  count?: number | null
  until?: string      // yyyy-MM-dd
}

export const RRULE_PRESETS: Array<{ label: string; rrule: string }> = [
  { label: 'Quotidien',             rrule: 'RRULE:FREQ=DAILY' },
  { label: 'Chaque semaine',        rrule: 'RRULE:FREQ=WEEKLY' },
  { label: 'Toutes les 2 semaines', rrule: 'RRULE:FREQ=WEEKLY;INTERVAL=2' },
  { label: 'Mensuel',               rrule: 'RRULE:FREQ=MONTHLY' },
  { label: 'Annuel',                rrule: 'RRULE:FREQ=YEARLY' },
]

export function buildRRule(opts: RRuleOptions): string {
  const parts: string[] = [`FREQ=${opts.freq}`]
  if (opts.interval && opts.interval > 1) parts.push(`INTERVAL=${opts.interval}`)
  if (opts.byDay?.length) parts.push(`BYDAY=${opts.byDay.join(',')}`)
  if (opts.count) parts.push(`COUNT=${opts.count}`)
  if (opts.until) parts.push(`UNTIL=${opts.until.replace(/-/g, '')}T000000Z`)
  return `RRULE:${parts.join(';')}`
}

// ── Dates spécifiques (RDATE) ────────────────────────────────────────────────
// Format stocké : `RDATE:20260801T000000,20260915T000000` (naïf, local).
// dateutil (backend) sait avancer dans cette liste à la complétion.

export function isRDates(rrule: string): boolean {
  return rrule.startsWith('RDATE:')
}

/** RDATE:… → dates ISO `yyyy-MM-dd`, triées. */
export function parseRDates(rrule: string): string[] {
  if (!isRDates(rrule)) return []
  return rrule
    .slice('RDATE:'.length)
    .split(',')
    .map(s => s.trim())
    .filter(s => /^\d{8}/.test(s))
    .map(s => `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`)
    .sort()
}

/** dates ISO `yyyy-MM-dd` → chaîne RDATE (dédupliquées, triées). */
export function buildRDates(dates: string[]): string {
  const uniq = [...new Set(dates)].sort()
  if (!uniq.length) return ''
  return `RDATE:${uniq.map(d => `${d.replace(/-/g, '')}T000000`).join(',')}`
}

export function parseRRule(rrule: string): RRuleOptions | null {
  if (!rrule) return null
  const body = rrule.replace(/^RRULE:/, '')
  const parts = body.split(';')
  const get = (k: string) => parts.find(p => p.startsWith(k + '='))?.split('=')[1] ?? ''
  const freq = get('FREQ') as RRuleFreq
  if (!freq) return null
  const interval = parseInt(get('INTERVAL') || '1')
  const byDay = get('BYDAY') ? get('BYDAY').split(',') : []
  const countRaw = get('COUNT')
  const count = countRaw ? parseInt(countRaw) : null
  const untilRaw = get('UNTIL')
  const until = untilRaw
    ? `${untilRaw.slice(0, 4)}-${untilRaw.slice(4, 6)}-${untilRaw.slice(6, 8)}`
    : ''
  return { freq, interval, byDay, count, until }
}

// Correspondance RFC 5545 jour → numéro JS (0=dim)
const DAY_NUMS: Record<string, number> = { SU: 0, MO: 1, TU: 2, WE: 3, TH: 4, FR: 5, SA: 6 }

/**
 * Retourne la prochaine occurrence d'une rrule après `from`.
 *
 * BYDAY pour FREQ=WEEKLY : trouve le prochain jour de la semaine correspondant.
 * UNTIL : si la prochaine occurrence dépasse la date limite, retourne `from`
 *         (signal "plus d'occurrences").
 * COUNT : non géré côté client (la fin par COUNT est gérée par le backend).
 */
export function nextOccurrence(rrule: string, from: Date): Date {
  // Dates spécifiques : première date de la liste strictement après `from`.
  if (isRDates(rrule)) {
    for (const d of parseRDates(rrule)) {
      const dt = new Date(`${d}T00:00:00`)
      if (dt > from) return dt
    }
    return from  // plus d'occurrences
  }

  const opts = parseRRule(rrule)
  if (!opts) return from

  const n = opts.interval ?? 1
  const next = computeNext(opts, from, n)

  if (opts.until) {
    const until = new Date(opts.until)
    if (next > until) return from
  }

  return next
}

function computeNext(opts: RRuleOptions, from: Date, n: number): Date {
  // WEEKLY + BYDAY : trouver le prochain jour de semaine dans la liste
  if (opts.freq === 'WEEKLY' && opts.byDay?.length) {
    const targetDays = opts.byDay
      .map(d => DAY_NUMS[d.replace(/^[+-]?\d*/, '')])  // +1MO → MO → 1
      .filter((d): d is number => d !== undefined)
      .sort((a, b) => a - b)

    const probe = new Date(from)
    probe.setDate(probe.getDate() + 1)
    for (let i = 0; i < 7 * n; i++) {
      if (targetDays.includes(probe.getDay())) return new Date(probe)
      probe.setDate(probe.getDate() + 1)
    }
    // Repli : ajouter n semaines (ne devrait pas arriver avec un BYDAY valide)
    const fallback = new Date(from)
    fallback.setDate(fallback.getDate() + 7 * n)
    return fallback
  }

  const d = new Date(from)
  switch (opts.freq) {
    case 'DAILY':   d.setDate(d.getDate() + n);         break
    case 'WEEKLY':  d.setDate(d.getDate() + 7 * n);     break
    case 'MONTHLY': d.setMonth(d.getMonth() + n);       break
    case 'YEARLY':  d.setFullYear(d.getFullYear() + n); break
  }
  return d
}
