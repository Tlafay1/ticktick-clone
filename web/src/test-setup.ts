/**
 * Setup vitest : fournit les globals navigateur minimaux nécessaires
 * pour que le router Vue (createWebHistory) s'initialise sans crasher.
 * On reste en environnement Node (pas jsdom) pour garder la légèreté.
 */

const _location = {
  protocol: 'http:',
  host: 'localhost',
  pathname: '/',
  search: '',
  hash: '',
  href: 'http://localhost/',
  origin: 'http://localhost',
}

const _history = {
  state: null,
  pushState: () => {},
  replaceState: () => {},
  go: () => {},
  back: () => {},
  forward: () => {},
  length: 1,
  scrollRestoration: 'auto' as ScrollRestoration,
}

// Minimal window pour Vue Router
if (typeof globalThis.window === 'undefined') {
  Object.defineProperty(globalThis, 'window', {
    value: {
      location: _location,
      history: _history,
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => true,
      document: { createElement: () => ({ href: '', pathname: '', hostname: '' }) },
    },
    writable: true,
  })
}

// Vue Router accède aussi à `location` directement (sans window.)
if (typeof globalThis.location === 'undefined') {
  Object.defineProperty(globalThis, 'location', { value: _location, writable: true })
}

if (typeof globalThis.history === 'undefined') {
  Object.defineProperty(globalThis, 'history', { value: _history, writable: true })
}

if (typeof globalThis.navigator === 'undefined') {
  Object.defineProperty(globalThis, 'navigator', {
    value: { onLine: true, userAgent: 'vitest' },
    writable: true,
  })
}

if (typeof globalThis.localStorage === 'undefined') {
  const _store: Record<string, string> = {}
  Object.defineProperty(globalThis, 'localStorage', {
    value: {
      getItem: (k: string) => _store[k] ?? null,
      setItem: (k: string, v: string) => { _store[k] = v },
      removeItem: (k: string) => { delete _store[k] },
      clear: () => { Object.keys(_store).forEach(k => delete _store[k]) },
    },
    writable: true,
  })
}
