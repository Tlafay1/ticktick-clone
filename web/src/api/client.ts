/** Client HTTP minimal : JSON + JWT avec refresh automatique, offline queue. */
import { enqueue } from '@/lib/offlineQueue'
import { pushToast } from '@/composables/useToast'

const ACCESS_KEY = 'tt.access'
const REFRESH_KEY = 'tt.refresh'

export const tokens = {
  get access() {
    return localStorage.getItem(ACCESS_KEY)
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY)
  },
  set(access: string, refresh?: string) {
    localStorage.setItem(ACCESS_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

export class ApiError extends Error {
  status: number
  data: unknown
  constructor(status: number, data: unknown) {
    super(`API ${status}`)
    this.status = status
    this.data = data
  }
}

export class OfflineError extends Error {
  constructor() { super('hors-ligne — mutation mise en file') }
}

let refreshing: Promise<boolean> | null = null

async function tryRefresh(): Promise<boolean> {
  refreshing ??= (async () => {
    const refresh = tokens.refresh
    if (!refresh) return false
    const res = await fetch('/api/auth/token/refresh/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    })
    if (!res.ok) {
      tokens.clear()
      return false
    }
    const data = await res.json()
    tokens.set(data.access, data.refresh)
    return true
  })().finally(() => (refreshing = null))
  return refreshing
}

export async function request<T>(
  method: string,
  url: string,
  body?: unknown,
  retry = true,
): Promise<T> {
  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (tokens.access) headers.Authorization = `Bearer ${tokens.access}`

  let res: Response
  try {
    res = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    // Réseau indisponible — on enqueue les mutations (pas les GET)
    if (method !== 'GET') {
      await enqueue(method as 'POST' | 'PATCH' | 'PUT' | 'DELETE', url, body)
      throw new OfflineError()
    }
    throw new Error('réseau indisponible')
  }

  if (res.status === 401 && retry && tokens.refresh) {
    if (await tryRefresh()) return request(method, url, body, false)
    window.location.href = '/login'
  }
  if (!res.ok) {
    const data = await res.json().catch(() => null)
    // Surface les échecs de mutation (plus d'échec silencieux).
    if (method !== 'GET') {
      pushToast(extractError(data) ?? "Échec de l'enregistrement", 'error')
    }
    throw new ApiError(res.status, data)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

/** Extrait un message lisible d'une réponse d'erreur DRF (string, {detail}, {champ:[…]}). */
function extractError(data: unknown): string | null {
  if (!data) return null
  if (typeof data === 'string') return data
  if (typeof data === 'object') {
    const obj = data as Record<string, unknown>
    if (typeof obj.detail === 'string') return obj.detail
    const first = Object.values(obj)[0]
    if (Array.isArray(first) && typeof first[0] === 'string') return first[0]
    if (typeof first === 'string') return first
  }
  return null
}

export const http = {
  get: <T>(url: string) => request<T>('GET', url),
  post: <T>(url: string, body?: unknown) => request<T>('POST', url, body),
  patch: <T>(url: string, body?: unknown) => request<T>('PATCH', url, body),
  delete: <T = void>(url: string) => request<T>('DELETE', url),
}

export function qs(params: Record<string, string | number | boolean | undefined>) {
  const search = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== '') search.set(k, String(v))
  }
  const s = search.toString()
  return s ? `?${s}` : ''
}
