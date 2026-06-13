import { describe, expect, it } from 'vitest'
import { toggleMarkdownCheckbox } from '../markdown'

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
