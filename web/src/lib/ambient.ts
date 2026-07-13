// Sons d'ambiance du focus : bruit synthétisé en WebAudio (aucun asset).
// Chaque ambiance = un type de bruit + filtre passe-bas + éventuelle
// modulation lente du volume (vagues).

export type AmbientKey = 'rain' | 'forest' | 'cafe' | 'waves'

interface Profile {
  noise: 'white' | 'pink' | 'brown'
  filterFreq: number
  gain: number
  lfo?: { freq: number; depth: number }
}

export const AMBIENT_PROFILES: Record<AmbientKey, Profile> = {
  rain:   { noise: 'white', filterFreq: 1400, gain: 0.14 },
  forest: { noise: 'pink',  filterFreq: 900,  gain: 0.12 },
  cafe:   { noise: 'brown', filterFreq: 700,  gain: 0.18 },
  waves:  { noise: 'brown', filterFreq: 450,  gain: 0.22, lfo: { freq: 0.12, depth: 0.45 } },
}

let ctx: AudioContext | null = null
let nodes: { source: AudioBufferSourceNode; gain: GainNode; lfo?: OscillatorNode } | null = null

/** Buffer de 2 s de bruit blanc/rose/brun, joué en boucle. */
function makeNoiseBuffer(context: AudioContext, type: Profile['noise']): AudioBuffer {
  const length = context.sampleRate * 2
  const buffer = context.createBuffer(1, length, context.sampleRate)
  const data = buffer.getChannelData(0)

  if (type === 'white') {
    for (let i = 0; i < length; i++) data[i] = Math.random() * 2 - 1
  } else if (type === 'pink') {
    // Approximation de Voss-McCartney (filtre IIR de Paul Kellet)
    let b0 = 0, b1 = 0, b2 = 0
    for (let i = 0; i < length; i++) {
      const w = Math.random() * 2 - 1
      b0 = 0.99765 * b0 + w * 0.099046
      b1 = 0.963 * b1 + w * 0.2965164
      b2 = 0.57 * b2 + w * 1.0526913
      data[i] = (b0 + b1 + b2 + w * 0.1848) * 0.25
    }
  } else {
    // brun : intégration du bruit blanc
    let last = 0
    for (let i = 0; i < length; i++) {
      const w = Math.random() * 2 - 1
      last = (last + 0.02 * w) / 1.02
      data[i] = last * 3.5
    }
  }
  return buffer
}

export function isAmbientKey(key: string): key is AmbientKey {
  return key in AMBIENT_PROFILES
}

export function playAmbient(key: string) {
  stopAmbient()
  if (!isAmbientKey(key)) return
  if (typeof AudioContext === 'undefined') return

  const profile = AMBIENT_PROFILES[key]
  ctx = ctx ?? new AudioContext()
  if (ctx.state === 'suspended') void ctx.resume()

  const source = ctx.createBufferSource()
  source.buffer = makeNoiseBuffer(ctx, profile.noise)
  source.loop = true

  const filter = ctx.createBiquadFilter()
  filter.type = 'lowpass'
  filter.frequency.value = profile.filterFreq

  const gain = ctx.createGain()
  gain.gain.value = profile.gain

  source.connect(filter)
  filter.connect(gain)
  gain.connect(ctx.destination)

  let lfo: OscillatorNode | undefined
  if (profile.lfo) {
    lfo = ctx.createOscillator()
    lfo.frequency.value = profile.lfo.freq
    const lfoGain = ctx.createGain()
    lfoGain.gain.value = profile.gain * profile.lfo.depth
    lfo.connect(lfoGain)
    lfoGain.connect(gain.gain)
    lfo.start()
  }

  source.start()
  nodes = { source, gain, lfo }
}

export function stopAmbient() {
  if (!nodes) return
  try {
    nodes.source.stop()
    nodes.lfo?.stop()
    nodes.source.disconnect()
    nodes.gain.disconnect()
  } catch { /* déjà arrêté */ }
  nodes = null
}

export function isPlaying() {
  return nodes !== null
}
