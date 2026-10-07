// Comparaison de versions « majeur.mineur.patch » (préfixe « v » toléré).

function parts(v: string): number[] | null {
  const m = /^v?(\d+)\.(\d+)\.(\d+)/.exec(v.trim())
  return m ? m.slice(1).map(Number) : null
}

/** Vrai si `latest` est strictement plus récente que `current` (faux si l'une est illisible). */
export function isNewerVersion(current: string, latest: string): boolean {
  const a = parts(current)
  const b = parts(latest)
  if (!a || !b) return false
  for (let i = 0; i < 3; i++) {
    if (b[i] !== a[i]) return b[i] > a[i]
  }
  return false
}
