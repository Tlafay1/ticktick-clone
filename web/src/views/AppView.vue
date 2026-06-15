<script setup lang="ts">
import { onMounted, onUnmounted, watch, computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Task } from '@/types'
import { useProjectStore } from '@/stores/projects'
import { useTaskStore } from '@/stores/tasks'
import { useTagStore } from '@/stores/tags'
import { useUserStore } from '@/stores/user'
import Sidebar from '@/components/Sidebar.vue'
import TaskItem from '@/components/TaskItem.vue'
import QuickAdd from '@/components/QuickAdd.vue'
import TaskDetail from '@/components/TaskDetail.vue'
import SearchBar from '@/components/SearchBar.vue'
import { tasksApi } from '@/api'
import { useDragSort } from '@/composables/useDragSort'
import { tasksToCSV, tasksToJSON, downloadFile, parseJSON } from '@/lib/exportImport'
import { pushToast } from '@/composables/useToast'
import { useRealtimeSync } from '@/composables/useRealtimeSync'
import { useReminderNotifications } from '@/composables/useReminderNotifications'
import { flush } from '@/lib/offlineQueue'
import { request } from '@/api/client'

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const taskStore = useTaskStore()
const tagStore = useTagStore()
const userStore = useUserStore()

const smartListLabels: Record<string, string> = {
  today: 'Aujourd\'hui',
  tomorrow: 'Demain',
  next7: '7 prochains jours',
  all: 'Toutes les tâches',
  inbox: 'Boîte de réception',
  completed: 'Terminées',
  trash: 'Corbeille',
}

const viewTitle = computed(() => {
  if (route.name === 'smart-list') {
    return smartListLabels[route.params.smartList as string] ?? 'Tâches'
  }
  if (route.name === 'project') {
    return projectStore.projects.find((p) => p.id === Number(route.params.id))?.name ?? 'Liste'
  }
  if (route.name === 'tag') {
    return `#${tagStore.byId(Number(route.params.id))?.name ?? route.params.id}`
  }
  return 'Tâches'
})

const isCompleted = computed(() => route.params.smartList === 'completed')
const isTrash = computed(() => route.params.smartList === 'trash')

const currentProjectId = computed(() => {
  if (route.name === 'project') return Number(route.params.id)
  if (route.name === 'smart-list' && route.params.smartList === 'inbox') {
    return projectStore.inbox?.id ?? undefined
  }
  return undefined
})

const currentProject = computed(() =>
  currentProjectId.value != null
    ? projectStore.projects.find(p => p.id === currentProjectId.value)
    : undefined
)

const listBgStyle = computed(() => {
  const p = currentProject.value
  if (!p) return {}
  if (p.bg_image_url) return { backgroundImage: `url(${p.bg_image_url})`, backgroundSize: 'cover', backgroundPosition: 'center' }
  if (p.bg_color) return { background: p.bg_color }
  return {}
})

const pinnedTasks = computed(() =>
  taskStore.tasks.filter((t: Task) => t.is_pinned && t.status === 0)
)
const regularTasks = computed(() =>
  taskStore.tasks.filter((t: Task) => !t.is_pinned || t.status !== 0)
)

async function loadView() {
  if (route.name === 'tag') {
    const tagId = Number(route.params.id)
    const tagName = tagStore.byId(tagId)?.name
    if (tagName) {
      taskStore.tasks = await tasksApi.list({ tag: tagName, status: 0 })
    } else {
      taskStore.tasks = []
    }
    return
  }
  if (route.name === 'project') {
    const pid = Number(route.params.id)
    const proj = projectStore.projects.find(p => p.id === pid)
    if (proj?.view_mode === 'kanban') {
      router.replace(`/project/${pid}/kanban`)
      return
    }
    if (proj?.view_mode === 'timeline') {
      router.replace('/timeline')
      return
    }
    await taskStore.loadProject(pid)
  } else if (route.name === 'smart-list') {
    const sl = route.params.smartList as string
    if (sl === 'inbox' && projectStore.inbox) {
      await taskStore.loadProject(projectStore.inbox.id)
    } else {
      await taskStore.loadSmartList(sl)
    }
  }
}

async function restoreTask(id: number) {
  await tasksApi.restore(id)
  taskStore.tasks = taskStore.tasks.filter((t: Task) => t.id !== id)
}

async function deleteForever(id: number) {
  await tasksApi.remove(id, true)
  taskStore.tasks = taskStore.tasks.filter((t: Task) => t.id !== id)
}

const SORT_STEP = 1000

const { overIdx, onDragStart, onDragOver, onDrop, onDragEnd } = useDragSort(
  async (from, to) => {
    const list = taskStore.tasks
    if (from < 0 || to < 0 || from >= list.length || to >= list.length) return

    // Calcul du nouveau sort_order : se glisse entre les voisins
    const sorted = [...list]
    const [moved] = sorted.splice(from, 1)
    sorted.splice(to, 0, moved)

    // Assigner sort_order espacés
    const updates = sorted.map((t, i) => ({ id: t.id, sort_order: (i + 1) * SORT_STEP }))
    taskStore.tasks = sorted.map((t, i) => ({ ...t, sort_order: (i + 1) * SORT_STEP }))
    await Promise.all(updates.map(({ id, sort_order }) => tasksApi.update(id, { sort_order })))
  }
)

function exportCSV() {
  const date = new Date().toISOString().split('T')[0]
  downloadFile(tasksToCSV(taskStore.tasks), `taches-${date}.csv`, 'text/csv')
}

function exportJSON() {
  const date = new Date().toISOString().split('T')[0]
  downloadFile(tasksToJSON(taskStore.tasks), `taches-${date}.json`, 'application/json')
}

function printView() {
  if (typeof window !== 'undefined') window.print()
}

async function importFile() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.csv,.json'
  input.onchange = async () => {
    const file = input.files?.[0]
    if (!file) return
    if (file.name.endsWith('.csv')) {
      try {
        const stats = await tasksApi.importFile(file)
        await Promise.all([projectStore.load(), tagStore.load()])
        await loadView()
        const n = stats.imported
        pushToast(`Import terminé : ${n} tâche${n !== 1 ? 's' : ''} importée${n !== 1 ? 's' : ''}`, 'success')
      } catch {
        pushToast("Échec de l'import CSV", 'error')
      }
    } else {
      const text = await file.text()
      const parsed = parseJSON(text)
      for (const t of parsed) {
        const created = await tasksApi.create({
          title: t.title,
          description: t.description,
          status: t.status ?? 0,
          priority: t.priority ?? 0,
          due_date: t.due_date ?? null,
          project: currentProjectId.value ?? projectStore.inbox?.id,
        })
        taskStore.tasks.unshift(created)
      }
    }
  }
  input.click()
}

async function emptyTrash() {
  if (!confirm('Vider la corbeille définitivement ?')) return
  await tasksApi.emptyTrash()
  taskStore.tasks = []
}

const headerMenuOpen = ref(false)
function toggleHeaderMenu() { headerMenuOpen.value = !headerMenuOpen.value }
function closeHeaderMenu() { headerMenuOpen.value = false }

const { connect: connectWs } = useRealtimeSync()
const { start: startNotifications } = useReminderNotifications()
const isOffline = ref(!navigator.onLine)

async function onOnline() {
  isOffline.value = false
  // Rejoue les mutations mises en file pendant la déconnexion
  await flush(async (m) => { await request(m.method, m.url, m.body) })
  await loadView()
}

function onOffline() { isOffline.value = true }

onMounted(async () => {
  await userStore.load()
  await projectStore.load()
  await tagStore.load()
  await loadView()
  connectWs()
  startNotifications()
  window.addEventListener('online', onOnline)
  window.addEventListener('offline', onOffline)
})

onUnmounted(() => {
  window.removeEventListener('online', onOnline)
  window.removeEventListener('offline', onOffline)
})

watch(() => route.fullPath, loadView)
</script>

<template>
  <div class="app-layout">
    <div v-if="isOffline" class="offline-banner">📡 Hors ligne — les modifications seront synchronisées à la reconnexion</div>
    <Sidebar />

    <main class="main-panel" :style="listBgStyle">
      <div class="list-header">
        <h1 class="list-title">{{ viewTitle }}</h1>
        <div class="header-right">
          <span class="task-count">{{ taskStore.tasks.length }} tâche{{ taskStore.tasks.length !== 1 ? 's' : '' }}</span>
          <button
            v-if="route.name === 'project'"
            class="btn btn-ghost view-toggle"
            title="Vue Kanban"
            @click="router.push(`/project/${route.params.id}/kanban`)"
          >⊞ Kanban</button>
          <button v-if="!isTrash" class="btn btn-ghost" title="Importer" @click="importFile">↑ Importer</button>
          <div v-if="!isTrash" class="header-menu-wrap">
            <button class="icon-btn" title="Plus d'options" @click="toggleHeaderMenu">⋯</button>
            <div v-if="headerMenuOpen" class="header-dropdown" @mouseleave="closeHeaderMenu">
              <button class="menu-item" @click="exportCSV(); closeHeaderMenu()">↓ Exporter CSV</button>
              <button class="menu-item" @click="exportJSON(); closeHeaderMenu()">↓ Exporter JSON</button>
              <button class="menu-item" @click="printView(); closeHeaderMenu()">🖨 Imprimer / PDF</button>
            </div>
          </div>
          <button v-if="isTrash && taskStore.tasks.length" class="btn btn-ghost danger-text" @click="emptyTrash">
            Vider la corbeille
          </button>
        </div>
      </div>

      <SearchBar v-if="!isTrash" />

      <div class="task-list-scroll">
        <!-- Corbeille -->
        <template v-if="isTrash">
          <div
            v-for="task in taskStore.tasks"
            :key="task.id"
            class="trash-row"
          >
            <span class="trash-title">{{ task.title }}</span>
            <div class="trash-actions">
              <button class="btn btn-ghost" @click="restoreTask(task.id)">Restaurer</button>
              <button class="btn btn-ghost danger-text" @click="deleteForever(task.id)">Supprimer</button>
            </div>
          </div>
          <div v-if="!taskStore.loading && taskStore.tasks.length === 0" class="empty-state">
            <div class="empty-icon">🗑</div>
            <p>La corbeille est vide</p>
          </div>
        </template>

        <!-- Vue normale -->
        <template v-else>
          <div v-if="pinnedTasks.length" class="group-label">📌 Épinglées</div>
          <TaskItem
            v-for="task in pinnedTasks"
            :key="task.id"
            :task="task"
            :selected="taskStore.selectedId === task.id"
          />

          <div v-if="pinnedTasks.length && regularTasks.length" class="group-label">Tâches</div>
          <div
            v-for="(task, idx) in regularTasks"
            :key="task.id"
            class="drag-wrapper"
            :class="{ 'drag-over': overIdx === (pinnedTasks.length + idx) }"
            draggable="true"
            @dragstart="(e) => { onDragStart(pinnedTasks.length + idx); e.dataTransfer?.setData('task-id', String(task.id)) }"
            @dragover="onDragOver($event, pinnedTasks.length + idx)"
            @drop="onDrop(pinnedTasks.length + idx)"
            @dragend="onDragEnd"
          >
            <TaskItem
              :task="task"
              :selected="taskStore.selectedId === task.id"
            />
          </div>

          <div v-if="!taskStore.loading && taskStore.tasks.length === 0" class="empty-state">
            <div class="empty-icon">{{ isCompleted ? '🏆' : '✨' }}</div>
            <p>{{ isCompleted ? 'Aucune tâche terminée' : 'Aucune tâche' }}</p>
          </div>
        </template>

        <div v-if="taskStore.loading" class="loading">Chargement…</div>

        <QuickAdd v-if="!isCompleted && !isTrash" :project-id="currentProjectId" />
      </div>
    </main>

    <TaskDetail v-if="!isTrash" />
  </div>
</template>

<style scoped>
.offline-banner {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: #f59e0b;
  color: #fff;
  text-align: center;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 500;
}

.app-layout {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.main-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.list-header {
  padding: 24px 24px 12px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.list-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.task-count {
  font-size: 13px;
  color: var(--text-muted);
}

.danger-text { color: var(--danger); }

.header-menu-wrap { position: relative; }
.header-dropdown {
  position: absolute;
  right: 0;
  top: calc(100% + 4px);
  min-width: 170px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.18);
  padding: 4px;
  z-index: 200;
}
.header-dropdown .menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 10px;
  border-radius: 5px;
  font-size: 13px;
  text-align: left;
  color: var(--text);
  background: none;
  border: none;
  cursor: pointer;
}
.header-dropdown .menu-item:hover { background: var(--bg-hover); }

.task-list-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 8px 8px 80px;
}

.group-label {
  padding: 12px 16px 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--text-muted);
}
.empty-icon { font-size: 40px; margin-bottom: 12px; }

.loading {
  padding: 20px;
  text-align: center;
  color: var(--text-muted);
}

/* Drag & drop */
.drag-wrapper { transition: opacity 0.15s; }
.drag-wrapper.drag-over { border-top: 2px solid var(--primary); }

/* Corbeille */
.trash-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-radius: 8px;
  margin: 1px 0;
}
.trash-row:hover { background: var(--bg-hover); }
.trash-title {
  flex: 1;
  font-size: 14px;
  text-decoration: line-through;
  color: var(--text-muted);
}
.trash-actions { display: flex; gap: 6px; }
</style>
