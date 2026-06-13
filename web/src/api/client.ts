/** Client HTTP minimal : JSON + JWT avec refresh automatique. */

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

  const res = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (res.status === 401 && retry && tokens.refresh) {
    if (await tryRefresh()) return request(method, url, body, false)
    window.location.href = '/login'
  }
  if (!res.ok) {
    throw new ApiError(res.status, await res.json().catch(() => null))
  }
  if (res.status === 204) return undefined as T
  return res.json()
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
