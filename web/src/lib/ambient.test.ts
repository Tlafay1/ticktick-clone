// @vitest-environment happy-dom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { playAmbient, stopAmbient, isPlaying, isAmbientKey, AMBIENT_PROFILES } from './ambient'

// AudioContext factice : happy-dom n'implémente pas WebAudio.
function makeFakeCtx() {
  const gainParam = () => ({ value: 0 })
  return {
    state: 'running',
    sampleRate: 8000,
    resume: vi.fn(),
    createBuffer: (_ch: number, length: number) => ({
      getChannelData: () => new Float32Array(length),
    }),
    createBufferSource: () => ({
      buffer: null, loop: false,
      connect: vi.fn(), disconnect: vi.fn(), start: vi.fn(), stop: vi.fn(),
    }),
    createBiquadFilter: () => ({ type: '', frequency: gainParam(), connect: vi.fn() }),
    createGain: () => ({ gain: gainParam(), connect: vi.fn(), disconnect: vi.fn() }),
    createOscillator: () => ({ frequency: gainParam(), connect: vi.fn(), start: vi.fn(), stop: vi.fn() }),
    destination: {},
  }
}

beforeEach(() => {
  vi.stubGlobal('AudioContext', vi.fn(makeFakeCtx))
})

afterEach(() => {
  stopAmbient()
  vi.unstubAllGlobals()
})

describe('ambient', () => {
  it('reconnaît les clés valides', () => {
    expect(isAmbientKey('rain')).toBe(true)
    expect(isAmbientKey('none')).toBe(false)
    expect(isAmbientKey('techno')).toBe(false)
  })

  it('chaque profil a un gain raisonnable (< 0.5, anti-saturation)', () => {
    for (const p of Object.values(AMBIENT_PROFILES)) {
      expect(p.gain).toBeGreaterThan(0)
      expect(p.gain).toBeLessThan(0.5)
    }
  })

  it('play démarre une lecture, stop l’arrête', () => {
    expect(isPlaying()).toBe(false)
    playAmbient('rain')
    expect(isPlaying()).toBe(true)
    stopAmbient()
    expect(isPlaying()).toBe(false)
  })

  it('une clé inconnue ne démarre rien', () => {
    playAmbient('none')
    expect(isPlaying()).toBe(false)
  })

  it('changer d’ambiance remplace la lecture en cours', () => {
    playAmbient('rain')
    playAmbient('waves')   // waves a un LFO
    expect(isPlaying()).toBe(true)
    stopAmbient()
    expect(isPlaying()).toBe(false)
  })
})
