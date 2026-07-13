<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Sidebar from '@/components/Sidebar.vue'
import TaskDetail from '@/components/TaskDetail.vue'
import TaskContextMenu from '@/components/TaskContextMenu.vue'
import { tasksApi } from '@/api'
import { useTaskStore } from '@/stores/tasks'
import type { Task } from '@/types'

const tasks = ref<Task[]>([])
const loading = ref(true)
const draggingTask = ref<Task | null>(null)
const overQuadrant = ref<string | null>(null)
const taskStore = useTaskStore()

type CtxMenu = { task: Task; x: number; y: number } | null
const contextMenu = ref<CtxMenu>(null)

function onCardCtx(e: MouseEvent, t: Task) {
  e.preventDefault()
  contextMenu.value = { task: t, x: e.clientX, y: e.clientY }
}

async function onCtxClose() {
  contextMenu.value = null
  tasks.value = await tasksApi.list({ status: 0 })
  taskStore.tasks = tasks.value
}

// Quadrant = combinaison urgence (due soon) × importance (priority)
// Urgent = due aujourd'hui ou en retard
// Important = priorité medium (3) ou high (5)
function getQuadrant(t: Task): string {
  const urgent = isUrgent(t)
  const important = t.priority >= 3
  if (urgent && important) return 'ui'    // Urgent + Important
  if (!urgent && important) return 'ni'   // Non-urgent + Important
  if (urgent && !important) return 'un'   // Urgent + Non-important
  return 'nn'                             // Non-urgent + Non-important
}

function isUrgent(t: Task) {
  if (!t.due_date) return false
  const due = new Date(t.due_date)
  const today = new Date()
  today.setHours(23, 59, 59, 999)
  return due <= today
}

const quadrants = [
  { key: 'ui', label: 'À faire maintenant', sub: 'Urgent + Important', color: '#ef4444', emoji: '🔥' },
  { key: 'ni', label: 'Planifier',           sub: 'Non-urgent + Important', color: '#3b82f6', emoji: '📅' },
  { key: 'un', label: 'Déléguer',            sub: 'Urgent + Non-important', color: '#f59e0b', emoji: '📤' },
  { key: 'nn', label: 'Éliminer',            sub: 'Non-urgent + Non-important', color: '#6b7280', emoji: '🗑' },
]

function tasksFor(key: string) {
  return tasks.value.filter(t => getQuadrant(t) === key)
}

onMounted(async () => {
  try {
    tasks.value = await tasksApi.list({ status: 0 })
    taskStore.tasks = tasks.value
  } finally {
    loading.value = false
  }
})

function onDragStart(t: Task) { draggingTask.value = t }

async function onDrop(quadrantKey: string) {
  if (!draggingTask.value) return
  const t = draggingTask.value
  // Compute new priority + due based on quadrant
  let patch: Partial<Task> = {}
  const today = new Date().toISOString().split('T')[0]

  if (quadrantKey === 'ui') {
    patch = { priority: t.priority < 3 ? 3 : t.priority, due_date: t.due_date ?? today }
  } else if (quadrantKey === 'ni') {
    patch = { priority: t.priority < 3 ? 3 : t.priority, due_date: null }
  } else if (quadrantKey === 'un') {
    patch = { priority: t.priority >= 3 ? 1 : t.priority, due_date: t.due_date ?? today }
  } else {
    patch = { priority: 0, due_date: null }
  }

  const updated = await tasksApi.update(t.id, patch)
  const idx = tasks.value.findIndex(x => x.id === t.id)
  if (idx >= 0) tasks.value[idx] = updated
  draggingTask.value = null
  overQuadrant.value = null
}
</script>

<template>
  <div class="app-layout">
    <Sidebar />

    <div class="eisenhower-panel" @click.self="taskStore.select(null)">
      <div class="eis-header">
        <h1>Matrice d'Eisenhower</h1>
        <div class="eis-legend">
          <span>🔥 Urgent</span>
          <span style="color:var(--text-muted)">↔</span>
          <span>⭐ Important</span>
        </div>
      </div>

      <div v-if="loading" class="loading-msg">Chargement…</div>

      <div v-else class="eis-grid">
        <div
          v-for="q in quadrants"
          :key="q.key"
          class="eis-quadrant"
          :class="{ 'drag-over': overQuadrant === q.key }"
          :style="`--qcolor: ${q.color}`"
          @dragover.prevent="overQuadrant = q.key"
          @dragleave="overQuadrant = null"
          @drop="onDrop(q.key)"
        >
          <div class="q-header">
            <span class="q-emoji">{{ q.emoji }}</span>
            <div>
              <div class="q-label">{{ q.label }}</div>
              <div class="q-sub">{{ q.sub }}</div>
            </div>
            <span class="q-count">{{ tasksFor(q.key).length }}</span>
          </div>

          <div class="q-tasks">
            <div
              v-for="t in tasksFor(q.key)"
              :key="t.id"
              class="eis-card"
              :class="{ selected: taskStore.selectedId === t.id }"
              draggable="true"
              @dragstart="onDragStart(t)"
              @click="taskStore.select(t.id)"
              @contextmenu.prevent="onCardCtx($event, t)"
            >
              <div class="card-title">{{ t.title }}</div>
              <div v-if="t.due_date" class="card-due">
                📅 {{ new Date(t.due_date).toLocaleDateString('fr-FR', { day:'2-digit', month:'short' }) }}
              </div>
            </div>

            <div v-if="tasksFor(q.key).length === 0" class="q-empty">
              Glissez des tâches ici
            </div>
          </div>
        </div>
      </div>
    </div>
    <TaskDetail v-if="taskStore.selected()" class="eis-detail" />
    <TaskContextMenu
      v-if="contextMenu"
      :task="contextMenu.task"
      :x="contextMenu.x"
      :y="contextMenu.y"
      @close="onCtxClose"
    />
  </div>
</template>

<style scoped>
.app-layout { display: flex; height: 100%; overflow: hidden; }

.eisenhower-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.eis-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 28px 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.eis-header h1 { margin: 0; font-size: 20px; font-weight: 700; }
.eis-legend { display: flex; gap: 10px; font-size: 12.5px; color: var(--text-secondary); align-items: center; }

.eis-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 12px;
  padding: 14px;
  overflow: auto;
}

.eis-quadrant {
  border: 2px solid var(--border);
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: border-color 0.15s;
}
.eis-quadrant.drag-over { border-color: var(--qcolor); }

.q-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  background: color-mix(in srgb, var(--qcolor) 10%, var(--bg));
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.q-emoji { font-size: 20px; }
.q-label { font-size: 14px; font-weight: 700; }
.q-sub { font-size: 11px; color: var(--text-muted); }
.q-count {
  margin-left: auto;
  background: var(--border);
  border-radius: 10px;
  padding: 2px 8px;
  font-size: 12px;
  color: var(--text-muted);
}

.q-tasks {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.eis-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 9px 12px;
  cursor: pointer;
  border-left: 3px solid var(--qcolor);
  transition: box-shadow 0.12s;
}
.eis-card:hover { box-shadow: 0 2px 6px rgba(0,0,0,0.08); }
.eis-card.selected { box-shadow: 0 0 0 2px var(--qcolor); }

.card-title { font-size: 13.5px; font-weight: 500; }
.card-due { font-size: 11.5px; color: var(--text-muted); margin-top: 3px; }

.q-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 13px;
  font-style: italic;
  border: 2px dashed var(--border);
  border-radius: 10px;
  min-height: 60px;
}

.loading-msg { padding: 60px; text-align: center; color: var(--text-muted); }

.eis-detail {
  width: 340px;
  min-width: 340px;
  border-left: 1px solid var(--border);
  overflow-y: auto;
}
</style>
