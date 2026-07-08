import { defineStore } from 'pinia'
import { ref } from 'vue'
import { tasksApi } from '@/api'
import type { TaskQuery } from '@/api'
import type { Task } from '@/types'
import { addDays, startOfDay } from 'date-fns'
import { wsSend } from '@/composables/useRealtimeSync'
import { playCompletionSound } from '@/lib/sound'
import { useUserStore } from '@/stores/user'
import { useProjectStore } from '@/stores/projects'

export const useTaskStore = defineStore('tasks', () => {
  const tasks = ref<Task[]>([])
  const loading = ref(false)
  const selectedId = ref<number | null>(null)

  function smartParams(smartList: string): TaskQuery {
    const now = new Date()
    const todayStart = startOfDay(now).toISOString()
    const todayEnd = addDays(startOfDay(now), 1).toISOString()
    const next7 = addDays(startOfDay(now), 7).toISOString()

    switch (smartList) {
      case 'today':
        return { smart: 1, status: 0, scheduled_after: todayStart, scheduled_before: todayEnd }
      case 'tomorrow': {
        const tmStart = addDays(startOfDay(now), 1).toISOString()
        const tmEnd = addDays(startOfDay(now), 2).toISOString()
        return { smart: 1, status: 0, scheduled_after: tmStart, scheduled_before: tmEnd }
      }
      case 'next7':
        return { smart: 1, status: 0, scheduled_before: next7 }
      case 'completed':
        return { status: 2 }
      case 'all':
        return { smart: 1, status: 0 }
      case 'trash':
        return { trashed: 1 }
      default:
        return {}
    }
  }

  async function loadSmartList(smartList: string) {
    loading.value = true
    try {
      tasks.value = await tasksApi.list(smartParams(smartList))
    } finally {
      loading.value = false
    }
  }

  async function loadProject(projectId: number) {
    loading.value = true
    try {
      // Une smart list custom pilote son statut via ses filter_rules :
      // ne pas forcer status=0 (sinon une liste « terminées » serait vide).
      const project = useProjectStore().projects.find((p) => p.id === projectId)
      tasks.value = project?.is_smart
        ? await tasksApi.list({ project: projectId })
        : await tasksApi.list({ project: projectId, status: 0 })
    } finally {
      loading.value = false
    }
  }

  async function create(data: Partial<Task>) {
    const t = await tasksApi.create(data)
    tasks.value.unshift(t)
    wsSend('task.created', { task: t as unknown as Record<string, unknown> })
    return t
  }

  async function update(id: number, data: Partial<Task>) {
    const t = await tasksApi.update(id, data)
    const idx = tasks.value.findIndex((x: Task) => x.id === id)
    if (idx >= 0) tasks.value[idx] = t
    wsSend('task.updated', { task: t as unknown as Record<string, unknown> })
    return t
  }

  async function complete(id: number) {
    const t = await tasksApi.complete(id)
    const idx = tasks.value.findIndex((x: Task) => x.id === id)
    if (idx >= 0) tasks.value[idx] = t
    wsSend('task.updated', { task: t as unknown as Record<string, unknown> })
    const userStore = useUserStore()
    playCompletionSound(userStore.user?.settings?.reminder_sound ?? 'default')
    setTimeout(() => {
      tasks.value = tasks.value.filter((x: Task) => x.id !== id || x.status === 2)
    }, 800)
    return t
  }

  async function reopen(id: number) {
    const t = await tasksApi.reopen(id)
    const idx = tasks.value.findIndex((x: Task) => x.id === id)
    if (idx >= 0) tasks.value[idx] = t
    wsSend('task.updated', { task: t as unknown as Record<string, unknown> })
    return t
  }

  async function wontDo(id: number) {
    const t = await tasksApi.wontDo(id)
    const idx = tasks.value.findIndex((x: Task) => x.id === id)
    if (idx >= 0) tasks.value[idx] = t
    wsSend('task.updated', { task: t as unknown as Record<string, unknown> })
    setTimeout(() => { tasks.value = tasks.value.filter((x: Task) => x.id !== id || x.status === -1) }, 800)
    return t
  }

  async function duplicate(id: number) {
    const t = await tasksApi.duplicate(id)
    const idx = tasks.value.findIndex((x: Task) => x.id === id)
    tasks.value.splice(idx + 1, 0, t)
    wsSend('task.created', { task: t as unknown as Record<string, unknown> })
    return t
  }

  async function remove(id: number) {
    await tasksApi.remove(id)
    tasks.value = tasks.value.filter((t: Task) => t.id !== id)
    if (selectedId.value === id) selectedId.value = null
    wsSend('task.deleted', { id })
  }

  async function pin(id: number) {
    const t = tasks.value.find((x: Task) => x.id === id)
    if (!t) return
    return update(id, { is_pinned: !t.is_pinned })
  }

  async function moveTo(id: number, projectId: number) {
    return update(id, { project: projectId })
  }

  function select(id: number | null) {
    selectedId.value = id
  }

  const selected = () => tasks.value.find((t: Task) => t.id === selectedId.value) ?? null

  return { tasks, loading, selectedId, selected, smartParams, loadSmartList, loadProject, create, update, complete, wontDo, reopen, remove, duplicate, pin, moveTo, select }
})
