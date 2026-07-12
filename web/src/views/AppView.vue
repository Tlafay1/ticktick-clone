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
import Icon from '@/components/Icon.vue'
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

// ----- Imbrication des sous-tâches (fidèle TickTick) -----
// Les enfants s'affichent indentés sous leur parent, repliables au chevron.
const collapsedParents = ref<Set<number>>(new Set())
function toggleCollapse(id: number) {
  const next = new Set(collapsedParents.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  collapsedParents.value = next
}

const childrenByParent = computed(() => {
  const m = new Map<number, Task[]>()
  for (const t of taskStore.tasks) {
    if (t.parent != null) {
      const arr = m.get(t.parent) ?? []
      arr.push(t)
      m.set(t.parent, arr)
    }
  }
  return m
})

const idsInList = computed(() => new Set(taskStore.tasks.map((t: Task) => t.id)))

// Premier niveau = sans parent, ou parent absent de la vue courante
// (ex. sous-tâche datée seule dans « Aujourd'hui », comme TickTick).
const topRegular = computed(() =>
  taskStore.tasks.filter((t: Task) =>
    (!t.is_pinned || t.status !== 0)
    && (t.parent == null || !idsInList.value.has(t.parent))
  )
)

// ── Tri de la vue (⇅, comme TickTick) ───────────────────────────────────────
type SortBy = 'manual' | 'due_date' | 'title' | 'priority'
const SORT_OPTIONS: Array<{ value: SortBy; label: string }> = [
  { value: 'manual', label: 'Tri manuel' },
  { value: 'due_date', label: 'Date' },
  { value: 'title', label: 'Titre' },
  { value: 'priority', label: 'Priorité' },
]
const sortBy = ref<SortBy>('manual')
const sortMenuOpen = ref(false)

const viewKey = computed(() => String(route.fullPath))

function loadSortPref() {
  try {
    sortBy.value = (localStorage.getItem(`tt-sort:${viewKey.value}`) as SortBy) || 'manual'
  } catch { sortBy.value = 'manual' }
}

function setSort(v: SortBy) {
  sortBy.value = v
  sortMenuOpen.value = false
  try { localStorage.setItem(`tt-sort:${viewKey.value}`, v) } catch { /* stockage indisponible */ }
}

const sortedTop = computed(() => {
  const tops = [...topRegular.value]
  switch (sortBy.value) {
    case 'due_date':
      return tops.sort((a, b) => {
        if (!a.due_date && !b.due_date) return 0
        if (!a.due_date) return 1
        if (!b.due_date) return -1
        return a.due_date.localeCompare(b.due_date)
      })
    case 'title':
      return tops.sort((a, b) => a.title.localeCompare(b.title, 'fr'))
    case 'priority':
      return tops.sort((a, b) => b.priority - a.priority)
    default:
      return tops
  }
})

interface TaskRowView { task: Task; depth: number; hasChildren: boolean; topIdx: number }

const regularRows = computed<TaskRowView[]>(() => {
  const rows: TaskRowView[] = []
  const seen = new Set<number>(pinnedTasks.value.map((t: Task) => t.id))
  const add = (t: Task, depth: number, topIdx: number) => {
    if (seen.has(t.id)) return
    seen.add(t.id)
    const kids = childrenByParent.value.get(t.id) ?? []
    rows.push({ task: t, depth, hasChildren: kids.length > 0, topIdx })
    if (!collapsedParents.value.has(t.id)) {
      for (const k of kids) add(k, depth + 1, topIdx)
    }
  }
  sortedTop.value.forEach((t: Task, i: number) => add(t, 0, i))
  return rows
})

// ── Multi-sélection (Ctrl/Maj+clic) + actions groupées ──────────────────────
const multiSel = ref<Set<number>>(new Set())
const lastMultiId = ref<number | null>(null)
const batchMoveOpen = ref(false)
const batchPrioOpen = ref(false)

function clearMulti() {
  multiSel.value = new Set()
  lastMultiId.value = null
  batchMoveOpen.value = false
  batchPrioOpen.value = false
}

function onMulti(t: Task, e: MouseEvent) {
  const next = new Set(multiSel.value)
  if (e.shiftKey && lastMultiId.value !== null) {
    // Étend la sélection entre le dernier clic et celui-ci (ordre affiché).
    const flat = regularRows.value.map(r => r.task.id)
    const a = flat.indexOf(lastMultiId.value)
    const b = flat.indexOf(t.id)
    if (a >= 0 && b >= 0) {
      for (let i = Math.min(a, b); i <= Math.max(a, b); i++) next.add(flat[i])
    } else {
      next.add(t.id)
    }
  } else if (next.has(t.id)) {
    next.delete(t.id)
  } else {
    next.add(t.id)
  }
  lastMultiId.value = t.id
  multiSel.value = next
  taskStore.select(null)
}

async function batchUpdate(patch: Partial<Task>) {
  const ids = [...multiSel.value]
  await Promise.all(ids.map(id => tasksApi.update(id, patch)))
  clearMulti()
  await loadView()
}

function batchSetDay(offset: number) {
  const d = new Date()
  d.setDate(d.getDate() + offset)
  d.setHours(0, 0, 0, 0)
  return batchUpdate({ due_date: d.toISOString(), is_all_day: true })
}

async function batchComplete() {
  const ids = [...multiSel.value]
  await Promise.all(ids.map(id => tasksApi.complete(id)))
  clearMulti()
  await loadView()
}

async function batchDelete() {
  if (!confirm(`Supprimer ${multiSel.value.size} tâche(s) ? (corbeille)`)) return
  const ids = [...multiSel.value]
  await Promise.all(ids.map(id => tasksApi.remove(id)))
  clearMulti()
  await loadView()
}

const BATCH_PRIORITIES = [
  { value: 5, label: 'Haute' },
  { value: 3, label: 'Moyenne' },
  { value: 1, label: 'Basse' },
  { value: 0, label: 'Aucune' },
]

function onEscapeMulti(e: KeyboardEvent) {
  if (e.key === 'Escape' && multiSel.value.size) clearMulti()
}

async function loadView() {
  clearMulti()
  loadSortPref()
  if (route.name === 'task') {
    // Deep link : charge la tâche dans le contexte de sa liste puis la sélectionne.
    const tid = Number(route.params.id)
    const task = await tasksApi.get(tid).catch(() => null)
    if (task) {
      await taskStore.loadProject(task.project)
      if (!taskStore.tasks.some((t: Task) => t.id === tid)) taskStore.tasks.unshift(task)
      taskStore.select(tid)
    } else {
      taskStore.tasks = []
    }
    return
  }
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
    await loadDoneSection(pid)
  } else if (route.name === 'smart-list') {
    const sl = route.params.smartList as string
    if (sl === 'inbox' && projectStore.inbox) {
      await taskStore.loadProject(projectStore.inbox.id)
      await loadDoneSection(projectStore.inbox.id)
    } else {
      doneTasks.value = []
      await taskStore.loadSmartList(sl)
    }
  }
}

// ── Section « Terminées & abandonnées » (façon TickTick, vues liste) ────────
const doneTasks = ref<Task[]>([])
const doneCollapsed = ref(false)
const doneShowAll = ref(false)

async function loadDoneSection(projectId: number) {
  doneShowAll.value = false
  const [completed, wontdo] = await Promise.all([
    tasksApi.list({ project: projectId, status: 2 }),
    tasksApi.list({ project: projectId, status: -1 }),
  ])
  doneTasks.value = [...completed, ...wontdo].sort((a, b) =>
    (b.completed_at ?? '').localeCompare(a.completed_at ?? '')
  )
}

const visibleDoneTasks = computed(() =>
  doneShowAll.value ? doneTasks.value : doneTasks.value.slice(0, 5)
)

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
    // from/to = index parmi les tâches de PREMIER NIVEAU (les enfants suivent
    // leur parent). Corrige aussi l'ancien décalage d'index avec les épinglées.
    const tops = [...topRegular.value]
    if (from < 0 || to < 0 || from >= tops.length || to >= tops.length) return
    const [moved] = tops.splice(from, 1)
    tops.splice(to, 0, moved)

    // Réaplatit : épinglées d'abord, puis chaque premier niveau suivi de ses
    // descendants ; le reliquat (ex. enfants d'épinglées) conserve sa place.
    const flat: Task[] = []
    const seen = new Set<number>()
    const push = (t: Task) => {
      if (seen.has(t.id)) return
      seen.add(t.id)
      flat.push(t)
      for (const k of childrenByParent.value.get(t.id) ?? []) push(k)
    }
    for (const p of pinnedTasks.value) push(p)
    for (const t of tops) push(t)
    for (const t of taskStore.tasks) push(t)

    const updates = flat.map((t, i) => ({ id: t.id, sort_order: (i + 1) * SORT_STEP }))
    taskStore.tasks = flat.map((t, i) => ({ ...t, sort_order: (i + 1) * SORT_STEP }))
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
  if (!userStore.user) await userStore.load()
  await projectStore.load()
  await tagStore.load()
  await loadView()
  connectWs()
  startNotifications()
  window.addEventListener('online', onOnline)
  window.addEventListener('offline', onOffline)
  window.addEventListener('keydown', onEscapeMulti)
})

onUnmounted(() => {
  window.removeEventListener('online', onOnline)
  window.removeEventListener('offline', onOffline)
  window.removeEventListener('keydown', onEscapeMulti)
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
          <div v-if="!isTrash && !isCompleted" class="header-menu-wrap">
            <button class="icon-btn" title="Trier" @click="sortMenuOpen = !sortMenuOpen"><Icon name="sort" :size="15" /></button>
            <div v-if="sortMenuOpen" class="header-dropdown" @mouseleave="sortMenuOpen = false">
              <button
                v-for="opt in SORT_OPTIONS" :key="opt.value"
                class="menu-item" :class="{ 'sort-active': sortBy === opt.value }"
                @click="setSort(opt.value)"
              >{{ opt.label }}<span v-if="sortBy === opt.value" class="sort-check">✓</span></button>
            </div>
          </div>
          <div v-if="!isTrash" class="header-menu-wrap">
            <button class="icon-btn" title="Plus d'options" @click="toggleHeaderMenu">⋯</button>
            <div v-if="headerMenuOpen" class="header-dropdown" @mouseleave="closeHeaderMenu">
              <button class="menu-item" @click="importFile(); closeHeaderMenu()">↑ Importer CSV/JSON</button>
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

      <SearchBar v-if="!isTrash" @reset="loadView" />

      <!-- Barre d'ajout en tête de liste, comme TickTick -->
      <QuickAdd v-if="!isCompleted && !isTrash" :project-id="currentProjectId" />

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

          <div v-if="pinnedTasks.length && regularRows.length" class="group-label">Tâches</div>
          <div
            v-for="row in regularRows"
            :key="row.task.id"
            class="drag-wrapper"
            :class="{ 'drag-over': row.depth === 0 && overIdx === row.topIdx }"
            :draggable="row.depth === 0 && sortBy === 'manual'"
            @dragstart="(e) => { if (row.depth === 0 && sortBy === 'manual') { onDragStart(row.topIdx); e.dataTransfer?.setData('task-id', String(row.task.id)) } }"
            @dragover="row.depth === 0 && sortBy === 'manual' && onDragOver($event, row.topIdx)"
            @drop="row.depth === 0 && sortBy === 'manual' && onDrop(row.topIdx)"
            @dragend="onDragEnd"
          >
            <TaskItem
              :task="row.task"
              :selected="taskStore.selectedId === row.task.id"
              :multi-selected="multiSel.has(row.task.id)"
              :depth="row.depth"
              :has-children="row.hasChildren"
              :collapsed="collapsedParents.has(row.task.id)"
              @toggle-collapse="toggleCollapse(row.task.id)"
              @multi="onMulti(row.task, $event)"
            />
          </div>

          <!-- Terminées & abandonnées (façon TickTick, en bas de liste) -->
          <template v-if="doneTasks.length && !isCompleted">
            <button class="done-section-toggle" @click="doneCollapsed = !doneCollapsed">
              <span class="done-chevron" :class="{ open: !doneCollapsed }">›</span>
              Terminées &amp; abandonnées
              <span class="done-count">{{ doneTasks.length }}</span>
            </button>
            <template v-if="!doneCollapsed">
              <TaskItem
                v-for="task in visibleDoneTasks"
                :key="`done-${task.id}`"
                :task="task"
                :selected="taskStore.selectedId === task.id"
              />
              <button
                v-if="!doneShowAll && doneTasks.length > 5"
                class="done-more"
                @click="doneShowAll = true"
              >Afficher plus</button>
            </template>
          </template>

          <div v-if="!taskStore.loading && taskStore.tasks.length === 0 && doneTasks.length === 0" class="empty-state">
            <div class="empty-icon">{{ isCompleted ? '🏆' : '✨' }}</div>
            <p>{{ isCompleted ? 'Aucune tâche terminée' : 'Aucune tâche' }}</p>
          </div>
        </template>

        <div v-if="taskStore.loading" class="loading">Chargement…</div>
      </div>

      <!-- Barre d'actions groupées (multi-sélection) -->
      <div v-if="multiSel.size" class="batch-bar">
        <span class="batch-count">{{ multiSel.size }} sélectionnée{{ multiSel.size > 1 ? 's' : '' }}</span>
        <button class="batch-btn" @click="batchSetDay(0)">Aujourd'hui</button>
        <button class="batch-btn" @click="batchSetDay(1)">Demain</button>
        <div class="batch-menu-wrap">
          <button class="batch-btn" @click="batchPrioOpen = !batchPrioOpen; batchMoveOpen = false">Priorité ▾</button>
          <div v-if="batchPrioOpen" class="batch-pop">
            <button v-for="p in BATCH_PRIORITIES" :key="p.value" class="menu-item" @click="batchUpdate({ priority: p.value })">{{ p.label }}</button>
          </div>
        </div>
        <div class="batch-menu-wrap">
          <button class="batch-btn" @click="batchMoveOpen = !batchMoveOpen; batchPrioOpen = false">Déplacer ▾</button>
          <div v-if="batchMoveOpen" class="batch-pop">
            <button
              v-for="p in projectStore.projects.filter(p => !p.archived && !p.is_smart)"
              :key="p.id" class="menu-item"
              @click="batchUpdate({ project: p.id })"
            >{{ p.icon ? p.icon + ' ' : '' }}{{ p.name }}</button>
          </div>
        </div>
        <button class="batch-btn" @click="batchComplete">Terminer</button>
        <button class="batch-btn danger-text" @click="batchDelete">Supprimer</button>
        <button class="icon-btn batch-close" title="Annuler la sélection (Échap)" @click="clearMulti">✕</button>
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
.header-dropdown .menu-item.sort-active { color: var(--primary); }
.sort-check { float: right; margin-left: 12px; }

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

/* Section « Terminées & abandonnées » */
.done-section-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  margin-top: 14px;
  padding: 6px 16px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text-secondary);
  text-align: left;
}
.done-chevron {
  display: inline-block;
  transition: transform 0.15s;
  color: var(--text-muted);
}
.done-chevron.open { transform: rotate(90deg); }
.done-count { font-size: 11px; color: var(--text-muted); }
.done-more {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 12px;
  padding: 6px 16px 10px;
  text-align: left;
}
.done-more:hover { color: var(--primary); }

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

/* Barre d'actions groupées */
.batch-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  padding: 8px 14px;
  border-top: 1px solid var(--border);
  background: var(--bg);
  flex-shrink: 0;
}
.batch-count { font-size: 12.5px; color: var(--text-secondary); margin-right: 4px; }
.batch-btn {
  padding: 5px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: none;
  color: var(--text);
  font-size: 12.5px;
  cursor: pointer;
}
.batch-btn:hover { border-color: var(--primary); color: var(--primary); }
.batch-btn.danger-text:hover { border-color: var(--danger); }
.batch-close { margin-left: auto; }
.batch-menu-wrap { position: relative; }
.batch-pop {
  position: absolute;
  bottom: 34px;
  left: 0;
  z-index: 50;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  min-width: 150px;
  max-height: 220px;
  overflow-y: auto;
}
.batch-pop .menu-item {
  display: block;
  width: 100%;
  padding: 7px 12px;
  border: none;
  background: none;
  color: var(--text);
  text-align: left;
  font-size: 13px;
  cursor: pointer;
}
.batch-pop .menu-item:hover { background: var(--bg-hover); }

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
