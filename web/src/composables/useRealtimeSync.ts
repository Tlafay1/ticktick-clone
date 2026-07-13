import { onUnmounted } from 'vue'
import { tokens, serverBase } from '@/api/client'
import { useTaskStore } from '@/stores/tasks'

type SyncMessage =
  | { type: 'task.created'; task: Record<string, unknown> }
  | { type: 'task.updated'; task: Record<string, unknown> }
  | { type: 'task.deleted'; id: number }

let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let reconnectCount = 0

export function useRealtimeSync() {
  const taskStore = useTaskStore()

  function connect() {
    if (ws && ws.readyState <= WebSocket.OPEN) return
    if (!tokens.access) return

    // Serveur configuré (app embarquée) sinon même origine (web).
    const base = serverBase.get()
    const host = base ? base.replace(/^https?:\/\//, '') : location.host
    const secure = base ? base.startsWith('https') : location.protocol === 'https:'
    const url = `${secure ? 'wss' : 'ws'}://${host}/ws/tasks/?token=${tokens.access}`

    ws = new WebSocket(url)

    // Reconnexion réussie : le backoff exponentiel repart de zéro.
    ws.onopen = () => { reconnectCount = 0 }

    ws.onmessage = (ev) => {
      try {
        const msg: SyncMessage = JSON.parse(ev.data)
        if (msg.type === 'task.created') {
          const exists = taskStore.tasks.some(t => t.id === (msg.task.id as number))
          if (!exists) taskStore.tasks.unshift(msg.task as never)
        } else if (msg.type === 'task.updated') {
          const idx = taskStore.tasks.findIndex(t => t.id === (msg.task.id as number))
          if (idx >= 0) taskStore.tasks[idx] = msg.task as never
        } else if (msg.type === 'task.deleted') {
          taskStore.tasks = taskStore.tasks.filter(t => t.id !== msg.id)
        }
      } catch {
        // ignore malformed messages
      }
    }

    ws.onclose = () => {
      const delay = Math.min(30_000, 1_000 * 2 ** (reconnectCount++))
      reconnectTimer = setTimeout(connect, delay)
    }

    ws.onerror = () => { ws?.close() }
  }

  function disconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    ws?.close()
    ws = null
  }

  onUnmounted(disconnect)

  return { connect, disconnect }
}

export function wsSend(type: SyncMessage['type'], payload: Record<string, unknown>) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type, ...payload }))
  }
}
