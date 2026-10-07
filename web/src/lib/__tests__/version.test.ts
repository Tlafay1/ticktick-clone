import { describe, expect, it } from 'vitest'
import { isNewerVersion } from '../version'

describe('isNewerVersion', () => {
  it('compare numériquement chaque segment (0.2.10 > 0.2.9)', () => {
    expect(isNewerVersion('0.2.9', 'v0.2.10')).toBe(true)
    expect(isNewerVersion('0.2.10', 'v0.2.9')).toBe(false)
    expect(isNewerVersion('0.2.9', 'v0.3.0')).toBe(true)
    expect(isNewerVersion('1.0.0', 'v0.9.9')).toBe(false)
  })

  it('même version ou version illisible : pas de mise à jour', () => {
    expect(isNewerVersion('0.2.3', 'v0.2.3')).toBe(false)
    expect(isNewerVersion('', 'v0.2.3')).toBe(false) // build de dev
    expect(isNewerVersion('0.2.3', 'nightly')).toBe(false)
  })
})
