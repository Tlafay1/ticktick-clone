<template>
  <div class="tl-wrap">
  <div class="timeline-root">
    <header class="tl-header">
      <button class="tl-back-btn" @click="router.back()" title="Retour">←</button>
      <button @click="prev">‹</button>
      <h2>{{ label }}</h2>
      <button @click="next">›</button>
      <div class="tl-zoom">
        <button :class="{ active: zoom === 'week' }"  @click="zoom = 'week'">Semaine</button>
        <button :class="{ active: zoom === 'month' }" @click="zoom = 'month'">Mois</button>
        <button :class="{ active: zoom === 'quarter' }" @click="zoom = 'quarter'">Trimestre</button>
      </div>
    </header>

    <div class="tl-scroll" ref="scroll">
      <!-- En-tête des jours -->
      <div class="tl-day-header" :style="gridStyle">
        <div v-for="d in days" :key="d.toISOString()" class="tl-day-cell"
             :class="{ today: isToday(d), weekend: isWeekend(d) }">
          <span class="tl-day-num">{{ d.getDate() }}</span>
          <span class="tl-day-name">{{ dayName(d) }}</span>
        </div>
      </div>

      <!-- Grille des tâches -->
      <div class="tl-body">
        <!-- Colonnes de fond -->
        <div class="tl-grid" :style="gridStyle">
          <div v-for="d in days" :key="d.toISOString()" class="tl-col"
               :class="{ today: isToday(d), weekend: isWeekend(d) }" />
        </div>

        <!-- Barres de tâches -->
        <div class="tl-rows">
          <div v-for="t in tasksWithDates" :key="t.id" class="tl-row">
            <div class="tl-row-label" :title="t.title">{{ t.title }}</div>
            <div class="tl-row-bar-area" :style="gridStyle">
              <div
                class="tl-bar"
                :class="[priorityClass(t.priority), { completed: t.status === 2 }]"
                :style="barStyle(t)"
                :title="barLabel(t)"
                @click="select(t)"
                @mousedown.stop="startDrag($event, t)"
              >
                <span class="tl-bar-left"  @mousedown.stop="startResize($event, t, 'start')" />
                <span class="tl-bar-label">{{ t.title }}</span>
                <span class="tl-bar-right" @mousedown.stop="startResize($event, t, 'end')" />
              </div>
            </div>
          </div>
          <div v-if="!tasksWithDates.length" class="tl-empty">
            Aucune tâche avec date dans cette période.
          </div>
        </div>
      </div>
    </div>
  </div>
  <TaskDetail v-if="taskStore.selectedId" class="tl-detail" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useTaskStore } from '@/stores/tasks'
import { useRouter } from 'vue-router'
import TaskDetail from '@/components/TaskDetail.vue'
import type { Task } from '@/types'
import {
  startOfWeek, startOfMonth, startOfQuarter,
  addDays, addWeeks, addMonths, addQuarters,
  eachDayOfInterval, endOfWeek, endOfMonth, endOfQuarter,
  isToday as fnsIsToday, isWeekend as fnsIsWeekend,
  format, differenceInDays, parseISO,
} from 'date-fns'
import { fr } from 'date-fns/locale'

const taskStore = useTaskStore()
const router = useRouter()

const zoom = ref<'week' | 'month' | 'quarter'>('month')
const pivot = ref(new Date())
// --- Plage de dates visible ---
const range = computed(() => {
  const d = pivot.value
  if (zoom.value === 'week')    return { start: startOfWeek(d, { locale: fr }), end: endOfWeek(d, { locale: fr }) }
  if (zoom.value === 'quarter') return { start: startOfQuarter(d), end: endOfQuarter(d) }
  return { start: startOfMonth(d), end: endOfMonth(d) }
})

const days = computed(() => eachDayOfInterval(range.value))

const label = computed(() => {
  if (zoom.value === 'week')
    return `Semaine du ${format(range.value.start, 'd MMM yyyy', { locale: fr })}`
  if (zoom.value === 'quarter')
    return `T${Math.ceil((range.value.start.getMonth() + 1) / 3)} ${range.value.start.getFullYear()}`
  return format(range.value.start, 'MMMM yyyy', { locale: fr })
})

function prev() {
  if (zoom.value === 'week')    pivot.value = addWeeks(pivot.value, -1)
  else if (zoom.value === 'month')   pivot.value = addMonths(pivot.value, -1)
  else                               pivot.value = addQuarters(pivot.value, -1)
}
function next() {
  if (zoom.value === 'week')    pivot.value = addWeeks(pivot.value, 1)
  else if (zoom.value === 'month')   pivot.value = addMonths(pivot.value, 1)
  else                               pivot.value = addQuarters(pivot.value, 1)
}

// --- Style grille CSS ---
const COL_W = computed(() => zoom.value === 'quarter' ? 28 : zoom.value === 'month' ? 36 : 80)

const gridStyle = computed(() => ({
  display: 'grid',
  gridTemplateColumns: `repeat(${days.value.length}, ${COL_W.value}px)`,
  width: `${days.value.length * COL_W.value}px`,
}))

// --- Helpers ---
const isToday   = (d: Date) => fnsIsToday(d)
const isWeekend = (d: Date) => fnsIsWeekend(d)
const dayName   = (d: Date) => format(d, zoom.value === 'quarter' ? 'E' : 'EEE', { locale: fr })

function priorityClass(p: number) {
  if (p >= 5) return 'pri-high'
  if (p >= 3) return 'pri-med'
  if (p >= 1) return 'pri-low'
  return 'pri-none'
}

// --- Tâches avec dates ---
const tasksWithDates = computed(() => {
  const { start, end } = range.value
  return taskStore.tasks.filter(t => {
    if (t.status === -1 || t.trashed_at) return false
    const due = t.due_date ? parseISO(t.due_date) : null
    if (!due) return false
    const s = t.start_date ? parseISO(t.start_date) : due
    return s <= end && due >= start
  })
})

function barStyle(t: Task) {
  const { start, end } = range.value
  const due = parseISO(t.due_date!)
  const taskStart = t.start_date ? parseISO(t.start_date) : due
  const clampedStart = taskStart < start ? start : taskStart
  const clampedEnd   = due > end ? end : due
  const startIdx = differenceInDays(clampedStart, start)
  const spanDays = Math.max(1, differenceInDays(clampedEnd, clampedStart) + 1)
  const w = COL_W.value
  return {
    left: `${startIdx * w}px`,
    width: `${spanDays * w - 4}px`,
  }
}

function barLabel(t: Task) {
  const due = t.due_date ? format(parseISO(t.due_date), 'd MMM', { locale: fr }) : ''
  const start = t.start_date ? format(parseISO(t.start_date), 'd MMM', { locale: fr }) + ' → ' : ''
  return `${t.title} (${start}${due})`
}

// --- Sélection ---
function select(t: Task) {
  taskStore.select(taskStore.selectedId === t.id ? null : t.id)
}

// --- Drag pour déplacer la barre ---
let _dragTask: Task | null = null
let _dragStartX = 0
let _dragOrigStart: string | null = null
let _dragOrigDue: string | null = null

function startDrag(e: MouseEvent, t: Task) {
  _dragTask = t
  _dragStartX = e.clientX
  _dragOrigStart = t.start_date ?? null
  _dragOrigDue = t.due_date ?? null
  window.addEventListener('mousemove', onDrag)
  window.addEventListener('mouseup', stopDrag)
}

function onDrag(e: MouseEvent) {
  if (!_dragTask || !_dragOrigDue) return
  const dx = e.clientX - _dragStartX
  const deltaDays = Math.round(dx / COL_W.value)
  const baseDue = parseISO(_dragOrigDue)
  const newDue = addDays(baseDue, deltaDays)
  _dragTask.due_date = format(newDue, 'yyyy-MM-dd')
  if (_dragOrigStart) {
    const baseStart = parseISO(_dragOrigStart)
    _dragTask.start_date = format(addDays(baseStart, deltaDays), 'yyyy-MM-dd')
  }
}

async function stopDrag() {
  window.removeEventListener('mousemove', onDrag)
  window.removeEventListener('mouseup', stopDrag)
  if (!_dragTask) return
  const { tasksApi } = await import('@/api')
  await tasksApi.update(_dragTask.id, {
    due_date: _dragTask.due_date,
    start_date: _dragTask.start_date,
  }).catch(() => {})
  _dragTask = null
}

// --- Resize des bords ---
type Edge = 'start' | 'end'
let _resizeTask: Task | null = null
let _resizeEdge: Edge = 'end'
let _resizeStartX = 0
let _resizeOrigDate: string | null = null

function startResize(e: MouseEvent, t: Task, edge: Edge) {
  e.preventDefault()
  _resizeTask = t
  _resizeEdge = edge
  _resizeStartX = e.clientX
  _resizeOrigDate = edge === 'end' ? (t.due_date ?? null) : (t.start_date ?? t.due_date ?? null)
  window.addEventListener('mousemove', onResize)
  window.addEventListener('mouseup', stopResize)
}

function onResize(e: MouseEvent) {
  if (!_resizeTask || !_resizeOrigDate) return
  const dx = e.clientX - _resizeStartX
  const deltaDays = Math.round(dx / COL_W.value)
  const base = parseISO(_resizeOrigDate)
  const newDate = format(addDays(base, deltaDays), 'yyyy-MM-dd')
  if (_resizeEdge === 'end')   _resizeTask.due_date   = newDate
  else                         _resizeTask.start_date = newDate
}

async function stopResize() {
  window.removeEventListener('mousemove', onResize)
  window.removeEventListener('mouseup', stopResize)
  if (!_resizeTask) return
  const { tasksApi } = await import('@/api')
  await tasksApi.update(_resizeTask.id, {
    due_date:   _resizeTask.due_date,
    start_date: _resizeTask.start_date,
  }).catch(() => {})
  _resizeTask = null
}

onMounted(async () => {
  if (!taskStore.tasks.length) await taskStore.loadSmartList('all')
})
</script>

<style scoped>
.tl-wrap {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.tl-detail {
  width: var(--detail-width);
  min-width: var(--detail-width);
  border-left: 1px solid var(--border);
  overflow-y: auto;
}

.timeline-root {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
  font-size: 13px;
}

.tl-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.tl-header h2 { margin: 0; font-size: 15px; text-transform: capitalize; }
.tl-back-btn { font-size: 16px; font-weight: bold; }
.tl-header button {
  padding: 4px 10px;
  border: 1px solid var(--border);
  background: var(--bg-card);
  border-radius: 4px;
  cursor: pointer;
  color: var(--text);
}
.tl-header button.active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}
.tl-zoom { display: flex; gap: 4px; margin-left: auto; }

.tl-scroll {
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: column;
}

.tl-day-header {
  position: sticky;
  top: 0;
  z-index: 2;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
}
.tl-day-cell {
  padding: 4px 0;
  text-align: center;
  font-size: 11px;
  color: var(--text-muted);
}
.tl-day-cell.today { color: var(--accent); font-weight: 600; }
.tl-day-cell.weekend { background: var(--bg-hover); }
.tl-day-num { display: block; font-size: 14px; font-weight: 500; }
.tl-day-name { display: block; font-size: 10px; }

.tl-body {
  flex: 1;
  position: relative;
}

.tl-grid {
  position: absolute;
  top: 0; left: 200px; bottom: 0;
  pointer-events: none;
}
.tl-col {
  border-right: 1px solid var(--border);
  height: 100%;
}
.tl-col.today { background: color-mix(in srgb, var(--accent) 6%, transparent); }
.tl-col.weekend { background: var(--bg-hover); }

.tl-rows { position: relative; }

.tl-empty {
  padding: 24px;
  text-align: center;
  color: var(--text-muted);
}

.tl-row {
  display: flex;
  height: 36px;
  align-items: center;
  border-bottom: 1px solid var(--border);
}

.tl-row-label {
  width: 200px;
  flex-shrink: 0;
  padding: 0 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 12px;
  color: var(--text);
  border-right: 1px solid var(--border);
}

.tl-row-bar-area {
  position: relative;
  height: 100%;
}

.tl-bar {
  position: absolute;
  top: 4px;
  height: 28px;
  border-radius: 4px;
  cursor: grab;
  display: flex;
  align-items: center;
  overflow: hidden;
  min-width: 8px;
  transition: opacity 0.15s;
}
.tl-bar:hover { opacity: 0.85; }
.tl-bar.completed { opacity: 0.4; text-decoration: line-through; }

.tl-bar.pri-high { background: #f55; color: #fff; }
.tl-bar.pri-med  { background: #fa0; color: #fff; }
.tl-bar.pri-low  { background: #4af; color: #fff; }
.tl-bar.pri-none { background: var(--accent); color: #fff; }

.tl-bar-left, .tl-bar-right {
  flex-shrink: 0;
  width: 6px;
  height: 100%;
  cursor: col-resize;
  background: rgba(0,0,0,0.15);
}

.tl-bar-label {
  flex: 1;
  padding: 0 6px;
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  pointer-events: none;
}
</style>
