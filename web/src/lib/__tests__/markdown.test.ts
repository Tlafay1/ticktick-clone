import { describe, expect, it } from 'vitest'
import { toggleMarkdownCheckbox, resolveDeepLinks } from '../markdown'

describe('toggleMarkdownCheckbox', () => {
  const src = 'Intro\n- [ ] un\n- [x] deux\n  - [ ] trois\nFin'

  it('coche la première case', () => {
    expect(toggleMarkdownCheckbox(src, 0)).toContain('- [x] un')
  })

  it('décoche la deuxième', () => {
    expect(toggleMarkdownCheckbox(src, 1)).toContain('- [ ] deux')
  })

  it('gère les cases imbriquées', () => {
    expect(toggleMarkdownCheckbox(src, 2)).toContain('  - [x] trois')
  })
})

describe('resolveDeepLinks (M20)', () => {
  it('convertit app://task/123 en lien Markdown cliquable', () => {
    const src = 'Voir app://task/123 pour les détails'
    const result = resolveDeepLinks(src)
    expect(result).toContain('[Tâche #123](app://task/123)')
  })

  it('convertit plusieurs deep links dans le même texte', () => {
    const src = 'Cf. app://task/1 et app://task/456'
    const result = resolveDeepLinks(src)
    expect(result).toContain('[Tâche #1](app://task/1)')
    expect(result).toContain('[Tâche #456](app://task/456)')
  })

  it('ne modifie pas un texte sans deep link', () => {
    const src = 'Texte normal sans lien'
    expect(resolveDeepLinks(src)).toBe(src)
  })
})
