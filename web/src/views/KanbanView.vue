<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Sidebar from '@/components/Sidebar.vue'
import TaskDetail from '@/components/TaskDetail.vue'
import TaskContextMenu from '@/components/TaskContextMenu.vue'
import { tasksApi, projectsApi } from '@/api'
import type { Task, Section } from '@/types'
import { useProjectStore } from '@/stores/projects'
import { useTaskStore } from '@/stores/tasks'
import { useTagStore } from '@/stores/tags'

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const taskStore = useTaskStore()
const tagStore = useTagStore()

const sections = ref<Section[]>([])
const loading = ref(true)
const newSectionName = ref('')
const showNewSection = ref(false)
const newTaskTitles = ref<Record<number, string>>({})
const showNewTask = ref<Record<number, boolean>>({})
const UNSECTIONED_ID = 0

const projectId = computed(() => Number(route.params.id))
const project = computed(() => projectStore.projects.find(p => p.id === projectId.value))

const doneSection = computed(() => sections.value.find(s => s.is_done) ?? null)

async function load() {
  loading.value = true
  const all = await tasksApi.list({ project: projectId.value })
  taskStore.tasks = all
  const proj = projectStore.projects.find(x => x.id === projectId.value)
  sections.value = proj?.sections ?? []
  loading.value = false
}

onMounted(async () => {
  if (!projectStore.projects.length) await projectStore.load()
  if (!tagStore.tags.length) await tagStore.load()
  await load()
})

function tasksForSection(sectionId: number | null, isDone: boolean) {
  if (isDone) return taskStore.tasks.filter(t => t.status === 2)
  return taskStore.tasks.filter(t =>
    t.status === 0 && (sectionId === UNSECTIONED_ID ? !t.section : t.section === sectionId)
  )
}

// DnD colonnes
const draggingTask = ref<Task | null>(null)
const overSection = ref<number | null>(null)

function onDragTaskStart(e: DragEvent, t: Task) {
  e.dataTransfer?.setData('text/plain', String(t.id))
  draggingTask.value = t
}

async function onDropSection(sectionId: number, isDone: boolean) {
  if (!draggingTask.value) return
  const t = draggingTask.value

  if (isDone) {
    await taskStore.complete(t.id)
  } else {
    // Changement de colonne ; sortir de la colonne Done réouvre (status 0).
    const updated = await tasksApi.update(t.id, {
      section: sectionId === UNSECTIONED_ID ? null : sectionId,
      status: 0,
    })
    const idx = taskStore.tasks.findIndex(x => x.id === t.id)
    if (idx >= 0) taskStore.tasks[idx] = updated
  }
  draggingTask.value = null
  overSection.value = null
}

// Sections CRUD
async function addSection() {
  const name = newSectionName.value.trim()
  if (!name) return
  const s = await projectsApi.createSection({ project: projectId.value, name })
  sections.value.push(s)
  newSectionName.value = ''
  showNewSection.value = false
  projectStore.projects = projectStore.projects.map(p =>
    p.id === projectId.value ? { ...p, sections: [...(p.sections ?? []), s] } : p
  )
}

async function markAsDone(sectionId: number) {
  // Démarquer toutes les sections done, puis marquer celle-ci
  for (const s of sections.value) {
    if (s.is_done && s.id !== sectionId) {
      const updated = await projectsApi.updateSection(s.id, { is_done: false })
      const idx = sections.value.findIndex(x => x.id === s.id)
      if (idx >= 0) sections.value[idx] = updated
    }
  }
  const updated = await projectsApi.updateSection(sectionId, { is_done: true })
  const idx = sections.value.findIndex(x => x.id === sectionId)
  if (idx >= 0) sections.value[idx] = updated
  // Sync dans le projectStore
  projectStore.projects = projectStore.projects.map(p =>
    p.id === projectId.value ? { ...p, sections: sections.value } : p
  )
}

async function unmarkAsDone(sectionId: number) {
  const updated = await projectsApi.updateSection(sectionId, { is_done: false })
  const idx = sections.value.findIndex(x => x.id === sectionId)
  if (idx >= 0) sections.value[idx] = updated
  projectStore.projects = projectStore.projects.map(p =>
    p.id === projectId.value ? { ...p, sections: sections.value } : p
  )
}

// Tâches
async function addTask(sectionId: number) {
  const title = (newTaskTitles.value[sectionId] ?? '').trim()
  if (!title) return
  await taskStore.create({
    title,
    project: projectId.value,
    section: sectionId === UNSECTIONED_ID ? undefined : sectionId,
  })
  newTaskTitles.value[sectionId] = ''
  showNewTask.value[sectionId] = false
  const fresh = await tasksApi.list({ project: projectId.value })
  taskStore.tasks = fresh
}

const priorityColor = (p: number) =>
  p === 5 ? 'var(--prio-high)' : p === 3 ? 'var(--prio-medium)' : p === 1 ? 'var(--prio-low)' : 'var(--prio-none)'

const collapsed = ref<Record<number, boolean>>({})
function toggleCollapse(id: number) { collapsed.value[id] = !collapsed.value[id] }

type KanbanCol = { id: number; name: string; isDone: boolean }

const allColumns = computed((): KanbanCol[] => {
  const cols: KanbanCol[] = [
    ...sections.value.map(s => ({ id: s.id, name: s.name, isDone: s.is_done })),
  ]
  // Colonne "Sans section" uniquement si des tâches non assignées existent
  const hasUnsectioned = taskStore.tasks.some(t => t.status === 0 && !t.section)
  if (hasUnsectioned) {
    cols.unshift({ id: UNSECTIONED_ID, name: 'Sans section', isDone: false })
  }
  // Si aucune section n'est marquée Done, ajouter une colonne virtuelle
  if (!doneSection.value) {
    cols.push({ id: -1, name: '✓ Terminées', isDone: true })
  }
  return cols
})

// Clic droit sur une carte
type CtxMenu = { task: Task; x: number; y: number } | null
const contextMenu = ref<CtxMenu>(null)

function onCardContextMenu(e: MouseEvent, t: Task) {
  e.preventDefault()
  contextMenu.value = { task: t, x: e.clientX, y: e.clientY }
}

// Menu colonne
type ColMenu = { col: KanbanCol; x: number; y: number } | null
const colMenu = ref<ColMenu>(null)

function onColHeaderContextMenu(e: MouseEvent, col: KanbanCol) {
  if (col.id < 0) return // virtuelle, pas de menu
  e.preventDefault()
  colMenu.value = { col, x: e.clientX, y: e.clientY }
}

function closeColMenu() { colMenu.value = null }
</script>

<template>
  <div class="app-layout" @click="closeColMenu">
    <Sidebar />

    <div class="kanban-panel">
      <div class="kanban-header">
        <h1>{{ project?.name ?? 'Kanban' }}</h1>
        <div style="display:flex;gap:8px">
          <button class="btn btn-ghost" @click="router.push(`/project/${projectId}`)">☰ Liste</button>
          <button class="btn btn-ghost" @click="showNewSection = true">＋ Colonne</button>
        </div>
      </div>

      <div v-if="loading" class="loading-msg">Chargement…</div>

      <div v-else class="kanban-content">
        <div class="kanban-board">
          <!-- Colonnes -->
          <div
            v-for="col in allColumns"
            :key="col.id"
            class="kanban-col"
            :class="{ 'drag-over': overSection === col.id, 'done-col': col.isDone }"
            @dragover.prevent="overSection = col.id"
            @drop.prevent="onDropSection(col.id, col.isDone)"
            @dragleave.self="overSection = null"
          >
            <div
              class="col-header"
              @click="toggleCollapse(col.id)"
              @contextmenu="onColHeaderContextMenu($event, col)"
            >
              <span class="col-chevron">{{ collapsed[col.id] ? '▶' : '▼' }}</span>
              <span class="col-name">
                {{ col.name }}
                <span v-if="col.isDone && col.id > 0" class="done-badge">✓ Terminées</span>
              </span>
              <span class="col-count">{{ tasksForSection(col.id, col.isDone).length }}</span>
              <button
                v-if="col.id > 0"
                class="col-menu-btn icon-btn"
                @click.stop="colMenu = { col, x: $event.clientX, y: $event.clientY }"
              >⋯</button>
            </div>

            <div v-show="!collapsed[col.id]" class="col-tasks" @dragover.prevent>
              <div
                v-for="t in tasksForSection(col.id, col.isDone)"
                :key="t.id"
                class="kanban-card"
                :class="{ selected: taskStore.selectedId === t.id }"
                draggable="true"
                @dragstart="onDragTaskStart($event, t)"
                @click="taskStore.select(t.id)"
                @contextmenu="onCardContextMenu($event, t)"
              >
                <div class="card-prio" :style="`background:${priorityColor(t.priority)}`" />
                <div class="card-body">
                  <div class="card-title" :class="{ 'done-title': t.status === 2 }">{{ t.title }}</div>
                  <div v-if="t.due_date" class="card-due">
                    📅 {{ new Date(t.due_date).toLocaleDateString('fr-FR', { day:'2-digit', month:'short' }) }}
                  </div>
                  <div v-if="t.check_items?.length" class="card-checks">
                    ☑ {{ t.check_items.filter(c => c.is_done).length }}/{{ t.check_items.length }}
                  </div>
                </div>
              </div>

              <!-- Ajout tâche (sauf colonne Done) -->
              <template v-if="!col.isDone">
                <div v-if="showNewTask[col.id]" class="new-task-form">
                  <input
                    v-model="newTaskTitles[col.id]"
                    placeholder="Titre…"
                    class="new-task-input"
                    autofocus
                    @keydown.enter="addTask(col.id)"
                    @keydown.escape="showNewTask[col.id] = false"
                  />
                  <div class="new-task-actions">
                    <button class="btn btn-primary" @click="addTask(col.id)">Ajouter</button>
                    <button class="btn btn-ghost" @click="showNewTask[col.id] = false">✕</button>
                  </div>
                </div>
                <button v-else class="add-task-btn" @click="showNewTask[col.id] = true">＋ Tâche</button>
              </template>
            </div>
          </div>

          <!-- Nouvelle colonne -->
          <div v-if="showNewSection" class="kanban-col new-col">
            <input
              v-model="newSectionName"
              placeholder="Nom de la colonne"
              class="new-col-input"
              autofocus
              @keydown.enter="addSection"
              @keydown.escape="showNewSection = false"
            />
            <div style="display:flex;gap:6px;margin-top:8px">
              <button class="btn btn-primary" @click="addSection">Créer</button>
              <button class="btn btn-ghost" @click="showNewSection = false">Annuler</button>
            </div>
          </div>
          <button v-else class="add-col-btn" @click="showNewSection = true">＋ Colonne</button>
        </div>

        <!-- Panneau de détail -->
        <TaskDetail v-if="taskStore.selected()" class="kanban-detail" />
      </div>
    </div>

    <!-- Clic droit carte -->
    <TaskContextMenu
      v-if="contextMenu"
      :task="contextMenu.task"
      :x="contextMenu.x"
      :y="contextMenu.y"
      @close="contextMenu = null; load()"
    />

    <!-- Menu colonne -->
    <div
      v-if="colMenu"
      class="menu col-context-menu"
      :style="`top:${colMenu.y}px;left:${colMenu.x}px`"
      @click.stop
    >
      <template v-if="sections.find(s => s.id === colMenu!.col.id)?.is_done">
        <button class="menu-item" @click="unmarkAsDone(colMenu!.col.id); closeColMenu()">
          ✕ Retirer le statut « Terminées »
        </button>
      </template>
      <template v-else>
        <button class="menu-item" @click="markAsDone(colMenu!.col.id); closeColMenu()">
          ✓ Définir comme colonne « Terminées »
        </button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.app-layout { display: flex; height: 100%; overflow: hidden; }

.kanban-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.kanban-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 12px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.kanban-header h1 { margin: 0; font-size: 20px; font-weight: 700; }

.kanban-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.kanban-board {
  display: flex;
  gap: 14px;
  padding: 16px 20px;
  overflow-x: auto;
  flex: 1;
  align-items: flex-start;
}

.kanban-detail {
  width: 340px;
  min-width: 340px;
  border-left: 1px solid var(--border);
  overflow-y: auto;
}

.kanban-col {
  width: 270px;
  min-width: 270px;
  background: var(--bg-sidebar);
  border-radius: 12px;
  padding: 10px;
  border: 2px solid transparent;
  transition: border-color 0.15s;
}
.kanban-col.drag-over { border-color: var(--primary); }
.kanban-col.done-col { background: color-mix(in srgb, var(--bg-sidebar) 80%, #4caf50 20%); }

.col-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 4px 8px;
  cursor: pointer;
  user-select: none;
  position: relative;
}
.col-chevron { font-size: 10px; color: var(--text-muted); }
.col-name { flex: 1; font-size: 13.5px; font-weight: 600; display: flex; align-items: center; gap: 6px; }
.done-badge {
  font-size: 10px;
  font-weight: 500;
  background: #4caf5030;
  color: #4caf50;
  border-radius: 8px;
  padding: 1px 6px;
}
.col-count {
  font-size: 11px;
  background: var(--border);
  color: var(--text-muted);
  border-radius: 10px;
  padding: 1px 7px;
}
.col-menu-btn { opacity: 0; }
.col-header:hover .col-menu-btn { opacity: 1; }

.col-tasks { display: flex; flex-direction: column; gap: 8px; }

.kanban-card {
  background: var(--bg);
  border-radius: 10px;
  padding: 10px 10px 10px 14px;
  border: 1px solid var(--border);
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: box-shadow 0.15s;
}
.kanban-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.kanban-card.selected { border-color: var(--primary); }

.card-prio {
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 4px;
  border-radius: 10px 0 0 10px;
}
.card-body { display: flex; flex-direction: column; gap: 4px; }
.card-title { font-size: 13.5px; font-weight: 500; line-height: 1.3; }
.card-title.done-title { text-decoration: line-through; color: var(--text-muted); }
.card-due { font-size: 11.5px; color: var(--text-secondary); }
.card-checks { font-size: 11px; color: var(--text-muted); }

.new-task-form { background: var(--bg); border-radius: 8px; padding: 8px; border: 1px solid var(--primary); }
.new-task-input {
  width: 100%; border: none; outline: none;
  font-size: 13.5px; background: none; color: var(--text); margin-bottom: 8px;
}
.new-task-actions { display: flex; gap: 6px; }

.add-task-btn {
  width: 100%; padding: 7px; border-radius: 8px;
  border: 1px dashed var(--border); background: none;
  color: var(--text-muted); cursor: pointer; font-size: 13px; text-align: left;
}
.add-task-btn:hover { border-color: var(--primary); color: var(--primary); }

.new-col { background: var(--bg); border: 2px dashed var(--border); padding: 14px; }
.new-col-input {
  width: 100%; padding: 8px; border: 1px solid var(--primary);
  border-radius: 8px; font-size: 13.5px; outline: none;
  background: var(--bg); color: var(--text);
}

.add-col-btn {
  width: 200px; min-width: 200px; padding: 10px 14px;
  border-radius: 12px; border: 2px dashed var(--border);
  background: none; color: var(--text-muted);
  cursor: pointer; font-size: 13.5px; align-self: flex-start;
}
.add-col-btn:hover { border-color: var(--primary); color: var(--primary); }

.loading-msg { padding: 40px; text-align: center; color: var(--text-muted); }

.col-context-menu { position: fixed; z-index: 1000; }
</style>
