let ctx: AudioContext | null = null

function getCtx(): AudioContext {
  if (!ctx) ctx = new AudioContext()
  return ctx
}

export function playCompletionSound(sound: string) {
  if (sound === 'none') return
  try {
    const ac = getCtx()
    const osc = ac.createOscillator()
    const gain = ac.createGain()
    osc.connect(gain)
    gain.connect(ac.destination)

    if (sound === 'bell') {
      osc.type = 'sine'
      osc.frequency.setValueAtTime(880, ac.currentTime)
      osc.frequency.exponentialRampToValueAtTime(440, ac.currentTime + 0.3)
      gain.gain.setValueAtTime(0.3, ac.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 0.5)
      osc.start(ac.currentTime)
      osc.stop(ac.currentTime + 0.5)
    } else if (sound === 'chime') {
      osc.type = 'sine'
      osc.frequency.setValueAtTime(1047, ac.currentTime)
      gain.gain.setValueAtTime(0.2, ac.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 0.4)
      osc.start(ac.currentTime)
      osc.stop(ac.currentTime + 0.4)
    } else {
      // default : court "ding"
      osc.type = 'triangle'
      osc.frequency.setValueAtTime(660, ac.currentTime)
      gain.gain.setValueAtTime(0.2, ac.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 0.25)
      osc.start(ac.currentTime)
      osc.stop(ac.currentTime + 0.25)
    }
  } catch {
    // AudioContext non disponible (ex: SSR)
  }
}
