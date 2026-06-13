import {
  addDays,
  format,
  isSameDay,
  isSameYear,
  startOfDay,
} from 'date-fns'

export const today = () => startOfDay(new Date())
export const tomorrow = () => addDays(today(), 1)

/** Borne ISO de fin de journée locale (exclusive). */
export const endOfTodayIso = () => addDays(today(), 1).toISOString()

export function dueLabel(iso: string | null, allDay: boolean): string {
  if (!iso) return ''
  const d = new Date(iso)
  let day: string
  if (isSameDay(d, today())) day = 'Today'
  else if (isSameDay(d, tomorrow())) day = 'Tomorrow'
  else if (isSameDay(d, addDays(today(), -1))) day = 'Yesterday'
  else day = isSameYear(d, new Date()) ? format(d, 'MMM d') : format(d, 'MMM d, yyyy')
  return allDay ? day : `${day} ${format(d, 'HH:mm')}`
}

/** Classe CSS de la date : en retard / aujourd'hui / futur. */
export function dueTone(iso: string | null, allDay: boolean, status: number) {
  if (!iso || status !== 0) return 'muted'
  const d = new Date(iso)
  const overdue = allDay ? startOfDay(d) < today() : d < new Date()
  if (overdue) return 'overdue'
  if (isSameDay(d, today())) return 'today'
  return 'future'
}

/** Date d'échéance pour un report rapide. Conserve l'heure si présente. */
export function postponeTarget(
  kind: 'today' | 'tomorrow' | 'next-week' | '+1d' | '+3d',
  current: string | null,
): Date {
  const base = current ? new Date(current) : new Date()
  switch (kind) {
    case 'today': {
      const t = new Date(base)
      t.setFullYear(new Date().getFullYear(), new Date().getMonth(), new Date().getDate())
      return t
    }
    case 'tomorrow': {
      const t = new Date(base)
      const tm = tomorrow()
      t.setFullYear(tm.getFullYear(), tm.getMonth(), tm.getDate())
      return t
    }
    case 'next-week':
      return addDays(base, 7)
    case '+1d':
      return addDays(base, 1)
    case '+3d':
      return addDays(base, 3)
  }
}

/** Convertit une Date en valeur pour <input type="datetime-local">. */
export function toLocalInput(iso: string | null): string {
  if (!iso) return ''
  return format(new Date(iso), "yyyy-MM-dd'T'HH:mm")
}

export function toDateInput(iso: string | null): string {
  if (!iso) return ''
  return format(new Date(iso), 'yyyy-MM-dd')
}
