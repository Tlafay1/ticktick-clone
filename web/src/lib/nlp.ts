import * as chrono from 'chrono-node'
import { PRIORITY } from '@/types'

export interface ParsedQuickAdd {
  /** Titre une fois les jetons reconnus retirés (si strip activé). */
  title: string
  due: Date | null
  hasTime: boolean
  priority: number | null
  tagNames: string[]
  /** Nom de liste saisi après ^ ou ~ (résolution faite par l'appelant). */
  projectName: string | null
}

interface Span {
  start: number
  end: number
}

const PRIORITY_WORDS: Record<string, number> = {
  high: PRIORITY.HIGH,
  medium: PRIORITY.MEDIUM,
  med: PRIORITY.MEDIUM,
  low: PRIORITY.LOW,
  none: PRIORITY.NONE,
}

/**
 * Analyse de la saisie rapide (module 10.1) :
 * dates naturelles (chrono), !high / !!! pour la priorité, #tag, ^Liste ou ~Liste.
 */
export function parseQuickAdd(
  input: string,
  opts: { strip?: boolean; reference?: Date; projectNames?: string[] } = {},
): ParsedQuickAdd {
  const strip = opts.strip ?? true
  const spans: Span[] = []
  let priority: number | null = null
  const tagNames: string[] = []
  let projectName: string | null = null

  // Priorité par mot-clé : !high, !medium, !low, !none
  const wordRe = /(^|\s)!(high|medium|med|low|none)\b/gi
  for (const m of input.matchAll(wordRe)) {
    priority = PRIORITY_WORDS[m[2].toLowerCase()]
    spans.push({ start: m.index + m[1].length, end: m.index + m[0].length })
  }

  // Priorité par points d'exclamation : ! / !! / !!!
  if (priority === null) {
    const bangRe = /(^|\s)(!{1,3})(?=\s|$)/g
    for (const m of input.matchAll(bangRe)) {
      priority = [PRIORITY.LOW, PRIORITY.MEDIUM, PRIORITY.HIGH][m[2].length - 1]
      spans.push({ start: m.index + m[1].length, end: m.index + m[0].length })
    }
  }

  // Tags : #mot (supporte la hiérarchie #Work/Marketing)
  const tagRe = /(^|\s)#([\p{L}\p{N}_/-]+)/gu
  for (const m of input.matchAll(tagRe)) {
    tagNames.push(m[2])
    spans.push({ start: m.index + m[1].length, end: m.index + m[0].length })
  }

  // Liste : ^Nom ou ~Nom. Si la liste contient des espaces, on tente la
  // correspondance la plus longue avec les noms connus.
  const projRe = /(^|\s)[~^]([^\s#!~^]+(?:\s+[^\s#!~^]+)*)/gu
  const names = (opts.projectNames ?? []).map((n) => n.toLowerCase())
  for (const m of input.matchAll(projRe)) {
    const words = m[2].split(/\s+/)
    let candidate = words[0]
    let matched = candidate
    for (let i = 1; i < words.length; i++) {
      candidate += ` ${words[i]}`
      if (names.some((n) => n === candidate.toLowerCase())) matched = candidate
    }
    if (names.length === 0 || names.some((n) => n === matched.toLowerCase()) || words.length === 1) {
      projectName = matched
      spans.push({
        start: m.index + m[1].length,
        end: m.index + m[1].length + 1 + matched.length,
      })
    }
  }

  // Dates naturelles via chrono — français d'abord (« demain 14h »,
  // « lundi prochain »), anglais en secours (« tomorrow 3pm »).
  let due: Date | null = null
  let hasTime = false
  const masked = maskSpans(input, spans)
  const reference = opts.reference ?? new Date()
  const frResults = chrono.fr.parse(masked, reference, { forwardDate: true })
  const enResults = chrono.parse(masked, reference, { forwardDate: true })
  // Les deux locales peuvent matcher partiellement (« at 1pm » vs « demain ») :
  // on garde celle qui couvre le plus de texte.
  const results =
    (enResults[0]?.text.length ?? 0) > (frResults[0]?.text.length ?? 0)
      ? enResults
      : frResults.length ? frResults : enResults
  if (results.length > 0) {
    const r = results[0]
    due = r.start.date()
    hasTime = r.start.isCertain('hour')
    if (!hasTime) due.setHours(0, 0, 0, 0)
    spans.push({ start: r.index, end: r.index + r.text.length })
  }

  const title = strip ? removeSpans(input, spans) : input.trim()
  return { title, due, hasTime, priority, tagNames, projectName }
}

/** Remplace les spans par des espaces pour que chrono ignore ces zones. */
function maskSpans(input: string, spans: Span[]): string {
  let out = input
  for (const s of spans) {
    out = out.slice(0, s.start) + ' '.repeat(s.end - s.start) + out.slice(s.end)
  }
  return out
}

function removeSpans(input: string, spans: Span[]): string {
  const keep: boolean[] = Array(input.length).fill(true)
  for (const s of spans) {
    for (let i = s.start; i < s.end; i++) keep[i] = false
  }
  return input
    .split('')
    .filter((_, i) => keep[i])
    .join('')
    .replace(/\s+/g, ' ')
    .trim()
}
