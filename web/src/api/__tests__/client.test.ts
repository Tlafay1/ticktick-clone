// @vitest-environment happy-dom
import { describe, it, expect, beforeEach, vi } from 'vitest'

const enqueueMock = vi.fn()
vi.mock('@/lib/offlineQueue', () => ({ enqueue: (...a: unknown[]) => enqueueMock(...a) }))
const toastMock = vi.fn()
vi.mock('@/composables/useToast', () => ({ pushToast: (...a: unknown[]) => toastMock(...a) }))

import { http, tokens, ApiError, OfflineError, qs } from '@/api/client'

function jsonResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

beforeEach(() => {
  localStorage.clear()
  enqueueMock.mockClear()
  toastMock.mockClear()
  vi.restoreAllMocks()
})

describe('client HTTP', () => {
  it('ajoute le header Authorization quand un access token est présent', async () => {
    tokens.set('acc', 'ref')
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { ok: 1 }))
    vi.stubGlobal('fetch', fetchMock)

    await http.get('/api/tasks/')
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer acc')
  })

  it('rafraîchit le token sur 401 puis rejoue la requête', async () => {
    tokens.set('old', 'ref')
    // Séquence : 401 (data) → refresh ok → 200 (data rejouée)
    const seq = [
      jsonResponse(401, { detail: 'expiré' }),
      jsonResponse(200, { access: 'new', refresh: 'ref2' }),
      jsonResponse(200, { id: 1 }),
    ]
    let i = 0
    vi.stubGlobal('fetch', vi.fn(async () => seq[i++]))

    const data = await http.get<{ id: number }>('/api/tasks/1/')
    expect(data).toEqual({ id: 1 })
    expect(tokens.access).toBe('new')
  })

  it('ne lance qu\'UN seul refresh pour plusieurs 401 concurrents (single-flight)', async () => {
    tokens.set('old', 'ref')
    let refreshCalls = 0
    const fetchMock = vi.fn(async (url: string) => {
      if (url === '/api/auth/token/refresh/') {
        refreshCalls++
        return jsonResponse(200, { access: 'new', refresh: 'ref2' })
      }
      // 1re fois par URL : 401 ; ensuite : 200
      const seen = fetchMock.mock.calls.filter(c => c[0] === url).length
      return seen <= 1 ? jsonResponse(401, {}) : jsonResponse(200, { url })
    })
    vi.stubGlobal('fetch', fetchMock)

    await Promise.all([http.get('/api/a/'), http.get('/api/b/'), http.get('/api/c/')])
    expect(refreshCalls).toBe(1)
  })

  it('vide les tokens quand le refresh échoue', async () => {
    tokens.set('old', 'ref')
    const seq = [jsonResponse(401, {}), jsonResponse(401, { detail: 'refresh mort' })]
    let i = 0
    vi.stubGlobal('fetch', vi.fn(async () => seq[i++]))

    await expect(http.get('/api/tasks/')).rejects.toBeInstanceOf(ApiError)
    expect(tokens.access).toBeNull()
    expect(tokens.refresh).toBeNull()
  })

  it('met en file les mutations quand le réseau est indisponible', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network')))
    await expect(http.post('/api/tasks/', { title: 'x' })).rejects.toBeInstanceOf(OfflineError)
    expect(enqueueMock).toHaveBeenCalledWith('POST', '/api/tasks/', { title: 'x' })
  })

  it('ne met PAS en file les GET hors-ligne', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network')))
    await expect(http.get('/api/tasks/')).rejects.toThrow()
    expect(enqueueMock).not.toHaveBeenCalled()
  })

  it('toast un message lisible quand une mutation échoue côté serveur', async () => {
    tokens.set('acc', 'ref')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(400, { title: ['Ce champ est requis.'] })))
    await expect(http.post('/api/tasks/', {})).rejects.toBeInstanceOf(ApiError)
    expect(toastMock).toHaveBeenCalledWith('Ce champ est requis.', 'error')
  })
})

describe('qs', () => {
  it('sérialise en ignorant undefined et chaînes vides', () => {
    expect(qs({ a: 1, b: undefined, c: '', d: 'x', e: false })).toBe('?a=1&d=x&e=false')
  })
  it('retourne une chaîne vide sans paramètre utile', () => {
    expect(qs({ a: undefined, b: '' })).toBe('')
  })
})
