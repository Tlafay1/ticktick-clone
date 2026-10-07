// Logique pure de la méthode d'organisation (modules 36 à 41) côté client :
// libellés, règles d'affichage. Les règles qui comptent vivent côté serveur ;
// ici on ne fait que les refléter sans les réinventer.

import type { Blocker, DayColor, OccurrenceStatus, SlotOccurrence } from '@/types'

export const WEEKDAYS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']

export const DAY_COLORS: Array<{ key: DayColor; emoji: string; label: string; hint: string }> = [
  { key: 'green', emoji: '🟢', label: 'Vert', hint: 'Journée normale' },
  { key: 'orange', emoji: '🟠', label: 'Orange', hint: 'Version minimale : 10 min par créneau' },
  { key: 'red', emoji: '🔴', label: 'Rouge', hint: 'Repos : seul le rituel du soir compte' },
]

export const BLOCKERS: Array<{ key: Blocker; label: string }> = [
  { key: 'boring', label: 'Ennuyeuse' },
  { key: 'unclear', label: 'Floue' },
  { key: 'too_big', label: 'Trop grosse' },
  { key: 'unpleasant', label: 'Désagréable' },
  { key: 'useless', label: 'Plus utile' },
]

const STATUS_LABELS: Record<OccurrenceStatus, string> = {
  planned: 'Prévu',
  honored: 'Fait',
  missed: 'Raté',
  excused: 'Excusé',
  recovered: 'Rattrapé',
  free: 'Libre',
}

const EXCUSE_LABELS: Record<string, string> = {
  joker: 'joker',
  rouge: 'journée rouge',
  pause: 'pause',
}

/** « Excusé (joker) », « Raté », « Libre »… — jamais culpabilisant. */
export function occurrenceLabel(occ: Pick<SlotOccurrence, 'status' | 'excuse_reason'>): string {
  const base = STATUS_LABELS[occ.status]
  return occ.status === 'excused' && occ.excuse_reason
    ? `${base} (${EXCUSE_LABELS[occ.excuse_reason] ?? occ.excuse_reason})`
    : base
}

/** « 20:30:00 » → « 20:30 ». */
export function hhmm(time: string): string {
  return time.slice(0, 5)
}

/** Heure locale d'un instant ISO, « 20:30 ». */
export function localTime(iso: string): string {
  const d = new Date(iso)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const START_EARLY_MS = 60 * 60_000

/** Même règle que le serveur : le jour même, au plus tôt une heure avant (M36.4). */
export function canStart(occ: SlotOccurrence, now = new Date()): boolean {
  if (occ.status !== 'planned' && occ.status !== 'missed') return false
  const start = new Date(occ.start_at)
  const sameDay = start.toDateString() === now.toDateString()
  return sameDay && now.getTime() >= start.getTime() - START_EARLY_MS
}

/** État du compteur « Aujourd'hui » (règle douce, M41.4). */
export function todayLimitState(count: number, limit: number): 'ok' | 'full' | 'over' {
  if (count > limit) return 'over'
  return count === limit ? 'full' : 'ok'
}

export function scorePercent(rate: number | null): string {
  return rate === null ? '—' : `${Math.round(rate * 100)} %`
}

export const SUGGESTION_TEXT: Record<'up' | 'down' | 'keep', string> = {
  up: 'Deux semaines à 80 % ou plus : tu peux monter d\'un cran (un créneau de plus, ou des créneaux plus longs — pas les deux).',
  down: 'Deux semaines sous 50 % : on allège d\'un cran. Ce n\'est pas un échec, c\'est un réglage.',
  keep: 'On garde le rythme actuel.',
}
