import DOMPurify from 'dompurify'
import { marked } from 'marked'

marked.setOptions({ gfm: true, breaks: true })

export function renderMarkdown(source: string): string {
  const html = marked.parse(source, { async: false })
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
