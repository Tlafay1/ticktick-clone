/** File de notifications éphémères (toasts) — évite les échecs silencieux. */
import { ref } from 'vue'

export interface Toast {
  id: number
  message: string
  type: 'error' | 'success' | 'info'
}

const toasts = ref<Toast[]>([])
let nextId = 1

export function pushToast(message: string, type: Toast['type'] = 'info', timeout = 4000) {
  const id = nextId++
  toasts.value.push({ id, message, type })
  if (timeout > 0) setTimeout(() => removeToast(id), timeout)
  return id
}

export function removeToast(id: number) {
  toasts.value = toasts.value.filter((t) => t.id !== id)
}

export function useToast() {
  return { toasts, pushToast, removeToast }
}
