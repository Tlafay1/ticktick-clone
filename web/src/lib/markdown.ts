import DOMPurify from 'dompurify'
import { marked } from 'marked'

marked.setOptions({ gfm: true, breaks: true })

// M20 — résolution de deep links dans le Markdown.
// `app://task/123` et `/task/123` sont convertis en liens cliquables
// avant le rendu Markdown, pour qu'ils apparaissent en blocs inline.
const DEEP_LINK_RE = /(app:\/\/task\/(\d+))/g

export function resolveDeepLinks(source: string): string {
  return source.replace(DEEP_LINK_RE, (_m, url, id) => `[Tâche #${id}](${url})`)
}

export function renderMarkdown(source: string): string {
  const html = marked.parse(resolveDeepLinks(source), { async: false })
  return DOMPurify.sanitize(html, { ADD_ATTR: ['type', 'checked'] })
}

const CHECKBOX_RE = /^(\s*(?:[-*+]|\d+\.)\s+)\[( |x|X)\]/gm

/**
 * Tier 3 (module 31) : bascule la n-ième checkbox markdown `- [ ]` du texte
 * source. Retourne le texte modifié.
 */
export function toggleMarkdownCheckbox(source: string, index: number): string {
  let i = -1
  return source.replace(CHECKBOX_RE, (full, prefix: string, state: string) => {
    i++
    if (i !== index) return full
    return `${prefix}[${state === ' ' ? 'x' : ' '}]`
  })
}
