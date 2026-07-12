import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// Mock onUnmounted pour exécuter le composable hors composant Vue
vi.mock('vue', async (orig) => {
  const actual = await orig<typeof import('vue')>()
  return { ...actual, onUnmounted: vi.fn() }
})

// `location` est déjà défini par test-setup.ts (http://localhost)
// Mock des tokens (access token requis pour l'URL WS)
vi.mock('@/api/client', () => ({
  tokens: { access: 'test-token' },
  serverBase: { get: () => '' },
}))

// Classe mock WebSocket constructible avec `new`
class MockWebSocket {
  static OPEN = 1
  readyState = 1
  onmessage: ((ev: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  close = vi.fn()
  static last: MockWebSocket | null = null
  constructor() { MockWebSocket.last = this }
}

describe('useRealtimeSync — gestion des messages WebSocket', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    MockWebSocket.last = null
    vi.stubGlobal('WebSocket', MockWebSocket)
    vi.resetModules()
  })

  it('task.updated met à jour la tâche dans le store', async () => {
    const { useTaskStore } = await import('@/stores/tasks')
    const { useRealtimeSync } = await import('@/composables/useRealtimeSync')
    const taskStore = useTaskStore()
    taskStore.tasks = [{ id: 1, title: 'Ancienne' }] as never[]

    const { connect } = useRealtimeSync()
    connect()

    MockWebSocket.last!.onmessage?.({ data: JSON.stringify({ type: 'task.updated', task: { id: 1, title: 'Nouvelle' } }) })

    expect(taskStore.tasks[0]).toMatchObject({ id: 1, title: 'Nouvelle' })
  })

  it('task.created ajoute la tâche au store si absente', async () => {
    const { useTaskStore } = await import('@/stores/tasks')
    const { useRealtimeSync } = await import('@/composables/useRealtimeSync')
    const taskStore = useTaskStore()
    taskStore.tasks = []

    const { connect } = useRealtimeSync()
    connect()

    MockWebSocket.last!.onmessage?.({ data: JSON.stringify({ type: 'task.created', task: { id: 42, title: 'Nouvelle tâche' } }) })

    expect(taskStore.tasks).toHaveLength(1)
    expect(taskStore.tasks[0]).toMatchObject({ id: 42 })
  })

  it('task.created ne duplique pas si la tâche existe déjà', async () => {
    const { useTaskStore } = await import('@/stores/tasks')
    const { useRealtimeSync } = await import('@/composables/useRealtimeSync')
    const taskStore = useTaskStore()
    taskStore.tasks = [{ id: 42, title: 'Existante' }] as never[]

    const { connect } = useRealtimeSync()
    connect()

    MockWebSocket.last!.onmessage?.({ data: JSON.stringify({ type: 'task.created', task: { id: 42, title: 'Existante' } }) })

    expect(taskStore.tasks).toHaveLength(1)
  })

  it('task.deleted supprime la tâche du store', async () => {
    const { useTaskStore } = await import('@/stores/tasks')
    const { useRealtimeSync } = await import('@/composables/useRealtimeSync')
    const taskStore = useTaskStore()
    taskStore.tasks = [{ id: 5 }, { id: 6 }] as never[]

    const { connect } = useRealtimeSync()
    connect()

    MockWebSocket.last!.onmessage?.({ data: JSON.stringify({ type: 'task.deleted', id: 5 }) })

    expect(taskStore.tasks).toHaveLength(1)
    expect(taskStore.tasks[0]).toMatchObject({ id: 6 })
  })

  it('message malformé est ignoré sans erreur', async () => {
    const { useRealtimeSync } = await import('@/composables/useRealtimeSync')
    const { connect } = useRealtimeSync()
    connect()

    expect(() => {
      MockWebSocket.last!.onmessage?.({ data: 'pas du json' })
    }).not.toThrow()
  })
})
