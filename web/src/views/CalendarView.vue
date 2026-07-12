<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import Sidebar from '@/components/Sidebar.vue'
import TaskDetail from '@/components/TaskDetail.vue'
import TaskContextMenu from '@/components/TaskContextMenu.vue'
import { tasksApi, calendarsApi, type CalendarEvent } from '@/api'
import { useTaskStore } from '@/stores/tasks'
import { useProjectStore } from '@/stores/projects'
import { useTagStore } from '@/stores/tags'
import { useUserStore } from '@/stores/user'
import type { Task } from '@/types'
import {
  startOfWeek, endOfWeek, startOfMonth, endOfMonth,
  eachDayOfInterval, addWeeks, subWeeks, addMonths, subMonths,
  format, isSameDay, isToday, parseISO, startOfDay, addDays,
} from 'date-fns'
import { fr } from 'date-fns/locale'

type ViewMode = 'week' | 'month' | 'agenda'

const viewMode = ref<ViewMode>('week')
const pivot = ref(new Date())   // semaine ou mois courant
const allTasks = ref<Task[]>([])
const loading = ref(false)
const taskStore = useTaskStore()
const projectStore = useProjectStore()
const tagStore = useTagStore()
const userStore = useUserStore()

// Premier jour de semaine des réglages (0=dim, 1=lun, 6=sam) — comme TickTick.
const weekStartsOn = computed<0 | 1 | 6>(() => {
  const v = userStore.user?.settings?.week_start ?? 1
  return (v === 0 || v === 6 ? v : 1)
})

// ── Chargement ──────────────────────────────────────────────────────────────
async function loadTasks() {
  loading.value = true
  // L'agenda affiche 30 jours glissants depuis aujourd'hui : charger cette
  // plage (et non le mois du pivot, qui tronquait la fin de mois).
  const start = viewMode.value === 'agenda'
    ? startOfDay(new Date())
    : viewMode.value === 'week'
      ? startOfWeek(pivot.value, { weekStartsOn: weekStartsOn.value })
      : startOfMonth(pivot.value)
  const end = viewMode.value === 'agenda'
    ? addDays(startOfDay(new Date()), 30)
    : viewMode.value === 'week'
      ? endOfWeek(pivot.value, { weekStartsOn: weekStartsOn.value })
      : endOfMonth(pivot.value)

  const rangeStart = startOfDay(addDays(start, -1)).toISOString()
  const rangeEnd = endOfWeek(end, { weekStartsOn: weekStartsOn.value }).toISOString()
  ;[allTasks.value, icsEvents.value] = await Promise.all([
    tasksApi.list({ due_after: rangeStart, due_before: rangeEnd, status: 0 }),
    calendarsApi.events({ start: rangeStart, end: rangeEnd }).catch(() => []),
  ])
  taskStore.tasks = allTasks.value
  loading.value = false
}

// ── Événements ICS (lecture seule) ──────────────────────────────────────────
const icsEvents = ref<CalendarEvent[]>([])

function icsOnDay(day: Date, allDay: boolean) {
  return icsEvents.value.filter(
    (e) => e.is_all_day === allDay && isSameDay(parseISO(e.start), day)
  )
}

function icsEventHour(e: CalendarEvent) {
  return new Date(e.start).getHours()
}

onMounted(async () => {
  await loadTasks()
  if (!projectStore.projects.length) await projectStore.load()
  if (!tagStore.tags.length) await tagStore.load()
  await loadSideTasks()
})
watch([viewMode, pivot], loadTasks)

// Rafraîchir quand l'utilisateur ferme le panneau de détail (tâche possiblement modifiée)
watch(() => taskStore.selectedId, (newId, oldId) => {
  if (oldId !== null && newId === null) loadTasks()
})

// ── Navigation ───────────────────────────────────────────────────────────────
function prev() {
  pivot.value = viewMode.value === 'week' ? subWeeks(pivot.value, 1) : subMonths(pivot.value, 1)
}
function next() {
  pivot.value = viewMode.value === 'week' ? addWeeks(pivot.value, 1) : addMonths(pivot.value, 1)
}
function goToday() { pivot.value = new Date() }

// ── Vue semaine ──────────────────────────────────────────────────────────────
const weekDays = computed(() =>
  eachDayOfInterval({
    start: startOfWeek(pivot.value, { weekStartsOn: weekStartsOn.value }),
    end: endOfWeek(pivot.value, { weekStartsOn: weekStartsOn.value }),
  })
)

// M19 — bascule moderne / classique
const calMode = ref<'modern' | 'classic'>('modern')

// M30 — masquage de plages horaires
const maskStart = ref(0)   // première heure visible (0-23)
const maskEnd = ref(24)    // dernière heure exclusive (1-24)
const showTimeMask = ref(false)

const HOURS = computed(() =>
  Array.from({ length: 24 }, (_, i) => i).filter(h => h >= maskStart.value && h < maskEnd.value)
)

function tasksOnDay(day: Date) {
  return allTasks.value.filter(t => {
    if (t.start_date && isSameDay(parseISO(t.start_date), day)) return true
    // Fallback : deadline sur ce jour si pas de date planifiée
    if (!t.start_date && t.due_date && isSameDay(parseISO(t.due_date), day)) return true
    return false
  })
}

// M16 — blocs avec durée : tâches ayant start_date + due_date + !is_all_day
const HOUR_PX = computed(() => calMode.value === 'classic' ? 64 : 40)

function timedEventsOnDay(day: Date) {
  return allTasks.value.filter(t =>
    t.start_date && t.due_date && !t.is_all_day &&
    isSameDay(parseISO(t.start_date), day)
  )
}

function timedEventHour(t: { start_date: string | null }) {
  return t.start_date ? new Date(t.start_date).getHours() : 0
}

function blockStyle(t: { start_date: string | null; due_date: string | null }) {
  if (!t.start_date || !t.due_date) return {}
  const px = HOUR_PX.value
  const startH = new Date(t.start_date).getHours() + new Date(t.start_date).getMinutes() / 60
  const endH = new Date(t.due_date).getHours() + new Date(t.due_date).getMinutes() / 60
  const topOffset = (startH - Math.floor(startH)) * px
  const height = Math.max(20, (endH - startH) * px)
  return { position: 'absolute' as const, top: `${topOffset}px`, left: '2px', right: '2px', height: `${height}px`, zIndex: 2 }
}

// Tâches ponctuelles positionnées à l'heure h (non-blocs)
function timedPointsOnDay(day: Date, h: number) {
  return allTasks.value.filter(t => {
    if (t.is_all_day) return false
    // Primaire : start_date positionné à l'heure h (non-bloc = due_date absent ou autre jour)
    if (t.start_date && isSameDay(parseISO(t.start_date), day) && new Date(t.start_date).getHours() === h) {
      // Exclure les blocs (start_date + due_date même jour)
      if (t.due_date && isSameDay(parseISO(t.start_date), parseISO(t.due_date))) return false
      return true
    }
    // Fallback : deadline à une heure précise, sans date planifiée
    if (!t.start_date && t.due_date && isSameDay(parseISO(t.due_date), day) && new Date(t.due_date).getHours() === h) return true
    return false
  })
}

// ── M4 Tâches multi-jours ────────────────────────────────────────────────────
function multiDayTasksInWeek() {
  const ws = weekDays.value[0]
  const we = weekDays.value[6]
  return allTasks.value.filter(t => {
    if (!t.start_date || !t.due_date) return false
    const s = parseISO(t.start_date)
    const e = parseISO(t.due_date)
    return !isSameDay(s, e) && s <= we && e >= ws
  })
}

function multiDayBarStyle(t: Task) {
  if (!t.start_date || !t.due_date) return {}
  const ws = weekDays.value[0]
  const we = weekDays.value[6]
  const s = parseISO(t.start_date)
  const e = parseISO(t.due_date)
  // Clamper aux bornes de la semaine
  const clampedStart = s < ws ? ws : s
  const clampedEnd   = e > we ? we : e
  const startIdx = weekDays.value.findIndex(d => isSameDay(d, clampedStart))
  const endIdx   = weekDays.value.findIndex(d => isSameDay(d, clampedEnd))
  // grid-column: (startIdx+2) / (endIdx+3) car col 1 = gutter
  return { gridColumn: `${startIdx + 2} / ${endIdx + 3}` }
}

// ── Vue mois ─────────────────────────────────────────────────────────────────
const monthGrid = computed(() => {
  const start = startOfWeek(startOfMonth(pivot.value), { weekStartsOn: weekStartsOn.value })
  const end = endOfWeek(endOfMonth(pivot.value), { weekStartsOn: weekStartsOn.value })
  return eachDayOfInterval({ start, end })
})

function isCurrentMonth(day: Date) {
  return day.getMonth() === pivot.value.getMonth()
}

// ── Vue agenda ───────────────────────────────────────────────────────────────
const agendaDays = computed(() => {
  const days: Array<{ date: Date; tasks: Task[] }> = []
  for (let i = 0; i < 30; i++) {
    const d = addDays(new Date(), i)
    const tasks = allTasks.value.filter(t => {
      if (t.start_date && isSameDay(parseISO(t.start_date), d)) return true
      if (!t.start_date && t.due_date && isSameDay(parseISO(t.due_date), d)) return true
      return false
    })
    if (tasks.length > 0 || i === 0) days.push({ date: d, tasks })
  }
  return days
})

// ── Création rapide depuis calendrier ────────────────────────────────────────
const newTaskDay = ref<Date | null>(null)
const newTaskHour = ref<number | null>(null)
const newTaskTitle = ref('')
const newTaskDesc = ref('')
const newTaskProjectId = ref<number | null>(null)

function startCreate(day: Date, hour: number | null = null) {
  newTaskDay.value = day
  newTaskHour.value = hour
  newTaskTitle.value = ''
  newTaskDesc.value = ''
  newTaskProjectId.value = projectStore.inbox?.id ?? null
}

async function createOnDay() {
  if (!newTaskTitle.value.trim() || !newTaskDay.value) return
  const projectId = newTaskProjectId.value ?? projectStore.inbox?.id
  if (!projectId) return

  let dueDate: string
  let isAllDay: boolean
  if (newTaskHour !== null && newTaskHour.value !== null) {
    const d = new Date(newTaskDay.value)
    d.setHours(newTaskHour.value, 0, 0, 0)
    dueDate = d.toISOString()
    isAllDay = false
  } else {
    dueDate = newTaskDay.value.toISOString()
    isAllDay = true
  }

  const t = await taskStore.create({
    title: newTaskTitle.value.trim(),
    description: newTaskDesc.value.trim() || undefined,
    project: projectId,
    start_date: dueDate,
    is_all_day: isAllDay,
  })
  allTasks.value.push(t)
  newTaskDay.value = null
  newTaskHour.value = null
  newTaskTitle.value = ''
  newTaskDesc.value = ''
}

// ── Label titre ──────────────────────────────────────────────────────────────
const headerLabel = computed(() => {
  if (viewMode.value === 'week') {
    const ws = weekDays.value[0]
    const we = weekDays.value[6]
    return `${format(ws, 'd MMM', { locale: fr })} – ${format(we, 'd MMM yyyy', { locale: fr })}`
  }
  return format(pivot.value, 'MMMM yyyy', { locale: fr })
})

const priorityColor = (p: number) =>
  p === 5 ? 'var(--prio-high)' : p === 3 ? 'var(--prio-medium)' : p === 1 ? 'var(--prio-low)' : 'var(--primary)'

function openTask(t: Task) {
  taskStore.select(t.id)
}

// ── Drag pour replanifier ─────────────────────────────────────────────────────
const draggingTask = ref<Task | null>(null)
const overDayKey = ref<string | null>(null)

function onTaskDragStart(e: DragEvent, t: Task) {
  draggingTask.value = t
  e.dataTransfer?.setData('text/plain', String(t.id))
}

async function dropOnDay(day: Date, hour?: number) {
  if (!draggingTask.value) return
  const t = draggingTask.value
  const dt = new Date(day)
  if (hour !== undefined) dt.setHours(hour, 0, 0, 0)
  else dt.setHours(0, 0, 0, 0)
  const updated = await tasksApi.update(t.id, {
    start_date: dt.toISOString(),
    is_all_day: hour === undefined,
  })
  // Mise à jour dans le calendrier (ou ajout si la tâche vient du panneau latéral)
  const idx = allTasks.value.findIndex(x => x.id === t.id)
  if (idx >= 0) allTasks.value[idx] = updated
  else allTasks.value.push(updated)
  taskStore.tasks = [...allTasks.value]
  // Mise à jour dans le panneau latéral
  const sideIdx = sideTasks.value.findIndex(x => x.id === t.id)
  if (sideIdx >= 0) sideTasks.value[sideIdx] = updated
  draggingTask.value = null
  overDayKey.value = null
}

// ── M16 Resize de durée ──────────────────────────────────────────────────────
const resizingTask = ref<Task | null>(null)
const resizeStartY = ref(0)
const resizeOrigDue = ref<Date | null>(null)

function startResize(e: MouseEvent, t: Task) {
  e.preventDefault()
  e.stopPropagation()
  resizingTask.value = t
  resizeStartY.value = e.clientY
  resizeOrigDue.value = t.due_date ? new Date(t.due_date) : null
}

function onGridMouseMove(e: MouseEvent) {
  if (!resizingTask.value || !resizeOrigDue.value) return
  const deltaY = e.clientY - resizeStartY.value
  const deltaMs = (deltaY / HOUR_PX.value) * 3_600_000
  const newDue = new Date(resizeOrigDue.value.getTime() + deltaMs)
  // Minimum 15 minutes de durée
  const minDue = resizingTask.value.start_date
    ? new Date(new Date(resizingTask.value.start_date).getTime() + 15 * 60_000)
    : new Date(resizeOrigDue.value.getTime() - 55 * 60_000)
  if (newDue < minDue) return
  const idx = allTasks.value.findIndex(x => x.id === resizingTask.value!.id)
  if (idx >= 0) allTasks.value[idx] = { ...allTasks.value[idx], due_date: newDue.toISOString() }
}

async function onGridMouseUp() {
  if (!resizingTask.value) return
  const t = allTasks.value.find(x => x.id === resizingTask.value!.id)
  if (t?.due_date) await tasksApi.update(t.id, { due_date: t.due_date })
  resizingTask.value = null
  resizeOrigDue.value = null
}

// ── Panneau "Organiser les tâches" ───────────────────────────────────────────
const showOrganizer = ref(true)
const organizerTab = ref<'list' | 'tag' | 'priority'>('list')
const organizerListId = ref<number | null>(null)
const organizerTagId = ref<number | null>(null)
const organizerPriority = ref<number | null>(null)
const sideTasks = ref<Task[]>([])

async function loadSideTasks() {
  sideTasks.value = await tasksApi.list({ status: 0 })
}

const panelTasks = computed(() => {
  // Seulement les tâches non encore planifiées (sans start_date)
  let tasks = sideTasks.value.filter(t => !t.start_date)
  if (organizerTab.value === 'list' && organizerListId.value !== null)
    tasks = tasks.filter(t => t.project === organizerListId.value)
  else if (organizerTab.value === 'tag' && organizerTagId.value !== null)
    tasks = tasks.filter(t => (t.tags as number[])?.includes(organizerTagId.value!))
  else if (organizerTab.value === 'priority' && organizerPriority.value !== null)
    tasks = tasks.filter(t => t.priority === organizerPriority.value)
  return [...tasks].sort((a, b) => {
    // Trier par deadline croissante (les plus urgentes en premier)
    if (a.due_date && b.due_date) return a.due_date.localeCompare(b.due_date)
    if (a.due_date) return -1
    if (b.due_date) return 1
    return 0
  })
})

watch(organizerTab, () => {
  organizerListId.value = null
  organizerTagId.value = null
  organizerPriority.value = null
})

const PRIORITIES = [
  { label: 'Haute',   value: 5, color: 'var(--prio-high)' },
  { label: 'Moyenne', value: 3, color: 'var(--prio-medium)' },
  { label: 'Faible',  value: 1, color: 'var(--prio-low)' },
  { label: 'Aucune',  value: 0, color: 'var(--text-muted)' },
]

// ── Clic droit ───────────────────────────────────────────────────────────────
type CtxMenu = { task: Task; x: number; y: number } | null
const contextMenu = ref<CtxMenu>(null)

function onTaskCtx(e: MouseEvent, t: Task) {
  e.preventDefault()
  e.stopPropagation()
  contextMenu.value = { task: t, x: e.clientX, y: e.clientY }
}

async function onCtxClose() {
  contextMenu.value = null
  await loadTasks()
}
</script>

<template>
  <div class="app-layout">
    <Sidebar />

    <div class="calendar-panel">
      <!-- Barre de contrôle -->
      <div class="cal-toolbar">
        <div class="cal-nav">
          <button class="icon-btn" @click="prev">‹</button>
          <button class="today-btn" @click="goToday">Aujourd'hui</button>
          <button class="icon-btn" @click="next">›</button>
          <span class="cal-label">{{ headerLabel }}</span>
        </div>
        <div class="view-tabs">
          <button v-for="v in ['week','month','agenda']" :key="v" class="view-tab" :class="{ active: viewMode === v }" @click="viewMode = v as ViewMode">
            {{ v === 'week' ? 'Semaine' : v === 'month' ? 'Mois' : 'Agenda' }}
          </button>
          <button v-if="viewMode === 'week'" class="view-tab" :class="{ active: showTimeMask }" @click="showTimeMask = !showTimeMask" title="Masquer les plages horaires">⏱</button>
          <button class="view-tab" :class="{ active: calMode === 'classic' }" @click="calMode = calMode === 'modern' ? 'classic' : 'modern'" title="Calendrier classique / moderne">
            {{ calMode === 'classic' ? 'Classique' : 'Moderne' }}
          </button>
          <button class="view-tab organizer-toggle" :class="{ active: showOrganizer }" @click="showOrganizer = !showOrganizer" title="Organiser les tâches">
            ⊞ Organiser
          </button>
        </div>
      </div>

      <!-- M30 — slider de masquage des plages horaires -->
      <div v-if="showTimeMask && viewMode === 'week'" class="time-mask-bar">
        <span class="time-mask-label">Début : {{ String(maskStart).padStart(2,'0') }}:00</span>
        <input type="range" min="0" max="23" step="1" v-model.number="maskStart" class="time-mask-slider" />
        <input type="range" min="1" max="24" step="1" v-model.number="maskEnd"   class="time-mask-slider" />
        <span class="time-mask-label">Fin : {{ String(maskEnd).padStart(2,'0') }}:00</span>
        <button @click="maskStart = 0; maskEnd = 24" class="time-mask-reset">Réinitialiser</button>
      </div>

      <!-- Vue SEMAINE ─────────────────────────────────────────────────── -->
      <div v-if="viewMode === 'week'" class="week-view" :class="`cal-${calMode}`" :style="`--hour-px: ${HOUR_PX}px`">
        <!-- En-tête des jours -->
        <div class="week-header">
          <div class="time-gutter" />
          <div
            v-for="day in weekDays"
            :key="day.toISOString()"
            class="week-day-head"
            :class="{ today: isToday(day) }"
          >
            <span class="day-name">{{ format(day, 'EEE', { locale: fr }) }}</span>
            <span class="day-num" :class="{ today: isToday(day) }">{{ format(day, 'd') }}</span>
          </div>
        </div>

        <!-- Ligne multi-jours (M4) -->
        <div v-if="multiDayTasksInWeek().length" class="multiday-row">
          <div class="time-gutter multiday-label">Multi-jours</div>
          <div
            v-for="t in multiDayTasksInWeek()"
            :key="t.id"
            class="cal-task multiday-bar"
            :style="[multiDayBarStyle(t), { borderLeftColor: priorityColor(t.priority) }]"
            @click.stop="openTask(t)"
            @contextmenu.stop.prevent="onTaskCtx($event, t)"
          >{{ t.title }}</div>
        </div>

        <!-- Ligne all-day -->
        <div class="allday-row">
          <div class="time-gutter allday-label">Toute la journée</div>
          <div
            v-for="day in weekDays"
            :key="day.toISOString()"
            class="allday-cell"
            :class="{ 'drag-over': overDayKey === day.toISOString() }"
            @click="startCreate(day)"
            @dragover.prevent="overDayKey = day.toISOString()"
            @dragleave="overDayKey = null"
            @drop.prevent="dropOnDay(day)"
          >
            <div
              v-for="t in tasksOnDay(day).filter(t => t.is_all_day)"
              :key="t.id"
              class="cal-task all-day"
              :style="`border-left-color: ${priorityColor(t.priority)}`"
              draggable="true"
              @dragstart.stop="onTaskDragStart($event, t)"
              @click.stop="openTask(t)"
              @contextmenu.stop.prevent="onTaskCtx($event, t)"
            >{{ t.title }}</div>
            <!-- Événements ICS journée entière (lecture seule) -->
            <div
              v-for="e in icsOnDay(day, true)"
              :key="`ics-${e.id}`"
              class="cal-task all-day ics-event"
              :style="e.color ? `border-left-color: ${e.color}` : ''"
              :title="`${e.calendar_name}${e.location ? ' · ' + e.location : ''}`"
              @click.stop
            >{{ e.title }}</div>
          </div>
        </div>

        <!-- Grille horaire (scroll) -->
        <div
          class="week-grid-scroll"
          :class="{ 'resizing': resizingTask }"
          @mousemove="onGridMouseMove"
          @mouseup="onGridMouseUp"
          @mouseleave="onGridMouseUp"
        >
          <div class="week-grid">
            <div v-for="h in HOURS" :key="h" class="hour-row">
              <div class="time-gutter">{{ h === 0 ? '' : `${String(h).padStart(2,'0')}:00` }}</div>
              <div
                v-for="day in weekDays"
                :key="day.toISOString()"
                class="hour-cell"
                :class="{ today: isToday(day), 'drag-over': overDayKey === `${day.toISOString()}-${h}` }"
                @click="startCreate(day, h)"
                @dragover.prevent="overDayKey = `${day.toISOString()}-${h}`"
                @dragleave="overDayKey = null"
                @drop.prevent="dropOnDay(day, h)"
              >
                <!-- Blocs M16 : durée start_date → due_date -->
                <template v-for="t in timedEventsOnDay(day).filter(t => timedEventHour(t) === h)" :key="`ev-${t.id}`">
                  <div
                    class="cal-task cal-block"
                    :style="[blockStyle(t), { borderLeftColor: priorityColor(t.priority) }]"
                    :draggable="!resizingTask"
                    @dragstart.stop="onTaskDragStart($event, t)"
                    @click.stop="openTask(t)"
                    @contextmenu.stop.prevent="onTaskCtx($event, t)"
                  >
                    <span class="block-title">{{ t.title }}</span>
                    <span v-if="t.start_date && t.due_date" class="block-time">
                      {{ format(parseISO(t.start_date), 'HH:mm') }}–{{ format(parseISO(t.due_date), 'HH:mm') }}
                    </span>
                    <div class="resize-handle" @mousedown.stop.prevent="startResize($event, t)" />
                  </div>
                </template>
                <!-- Tâches ponctuelles (due_date seule) -->
                <div
                  v-for="t in timedPointsOnDay(day, h)"
                  :key="t.id"
                  class="cal-task timed"
                  :style="`border-left-color: ${priorityColor(t.priority)}`"
                  draggable="true"
                  @dragstart.stop="onTaskDragStart($event, t)"
                  @click.stop="openTask(t)"
                  @contextmenu.stop.prevent="onTaskCtx($event, t)"
                >{{ t.title }}</div>
                <!-- Événements ICS horaires (lecture seule) -->
                <div
                  v-for="e in icsOnDay(day, false).filter(e => icsEventHour(e) === h)"
                  :key="`ics-${e.id}`"
                  class="cal-task timed ics-event"
                  :style="e.color ? `border-left-color: ${e.color}` : ''"
                  :title="`${e.calendar_name}${e.location ? ' · ' + e.location : ''}`"
                  @click.stop
                >{{ format(parseISO(e.start), 'HH:mm') }} {{ e.title }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Vue MOIS ─────────────────────────────────────────────────────── -->
      <div v-else-if="viewMode === 'month'" class="month-view">
        <div class="month-header">
          <div v-for="name in ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim']" :key="name" class="month-head-cell">{{ name }}</div>
        </div>
        <div class="month-grid">
          <div
            v-for="day in monthGrid"
            :key="day.toISOString()"
            class="month-cell"
            :class="{ 'other-month': !isCurrentMonth(day), today: isToday(day), 'drag-over': overDayKey === day.toISOString() }"
            @click="startCreate(day)"
            @dragover.prevent="overDayKey = day.toISOString()"
            @dragleave="overDayKey = null"
            @drop.prevent="dropOnDay(day)"
          >
            <span class="month-day-num" :class="{ today: isToday(day) }">{{ format(day, 'd') }}</span>
            <div class="month-tasks">
              <div
                v-for="t in tasksOnDay(day).slice(0, 3)"
                :key="t.id"
                class="month-task"
                :style="`background: ${priorityColor(t.priority)}22; color: ${priorityColor(t.priority)}`"
                draggable="true"
                @dragstart.stop="onTaskDragStart($event, t)"
                @click.stop="openTask(t)"
                @contextmenu.stop.prevent="onTaskCtx($event, t)"
              >{{ t.title }}</div>
              <div
                v-for="e in [...icsOnDay(day, true), ...icsOnDay(day, false)].slice(0, 2)"
                :key="`ics-${e.id}`"
                class="month-task ics-event"
                :style="e.color ? `background: ${e.color}22; color: ${e.color}` : ''"
                :title="e.calendar_name"
                @click.stop
              >{{ e.title }}</div>
              <div v-if="tasksOnDay(day).length > 3" class="month-more">+{{ tasksOnDay(day).length - 3 }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Vue AGENDA ────────────────────────────────────────────────────── -->
      <div v-else class="agenda-view">
        <div v-for="{ date, tasks } in agendaDays" :key="date.toISOString()" class="agenda-day">
          <div class="agenda-date" :class="{ today: isToday(date) }">
            <span class="agenda-weekday">{{ format(date, 'EEE', { locale: fr }) }}</span>
            <span class="agenda-daynum" :class="{ today: isToday(date) }">{{ format(date, 'd MMM', { locale: fr }) }}</span>
          </div>
          <div class="agenda-tasks">
            <div
              v-for="t in tasks"
              :key="t.id"
              class="agenda-task"
              :style="`border-left-color: ${priorityColor(t.priority)}`"
              draggable="true"
              @dragstart="onTaskDragStart($event, t)"
              @click="openTask(t)"
              @contextmenu.prevent="onTaskCtx($event, t)"
            >
              <span class="agenda-time" v-if="!t.is_all_day && t.due_date">{{ format(parseISO(t.due_date), 'HH:mm') }}</span>
              <span class="agenda-title">{{ t.title }}</span>
            </div>
            <div
              v-for="e in [...icsOnDay(date, true), ...icsOnDay(date, false)]"
              :key="`ics-${e.id}`"
              class="agenda-task ics-event"
              :style="e.color ? `border-left-color: ${e.color}` : ''"
              :title="e.calendar_name"
            >
              <span class="agenda-time" v-if="!e.is_all_day">{{ format(parseISO(e.start), 'HH:mm') }}</span>
              <span class="agenda-title">{{ e.title }}</span>
            </div>
            <button class="agenda-add" @click="startCreate(date)">＋ Ajouter</button>
          </div>
        </div>
      </div>

      <!-- Modal création rapide -->
      <div v-if="newTaskDay" class="quick-create-backdrop" @click.self="newTaskDay = null">
        <div class="quick-create-modal">
          <div class="qc-date">
            📅 {{ format(newTaskDay, 'EEEE d MMMM', { locale: fr }) }}
            <span v-if="newTaskHour !== null">, {{ String(newTaskHour).padStart(2,'0') }}:00</span>
          </div>
          <input
            v-model="newTaskTitle"
            placeholder="Que souhaitez-vous faire ?"
            class="qc-input"
            autofocus
            @keydown.enter="createOnDay"
            @keydown.escape="newTaskDay = null"
          />
          <textarea
            v-model="newTaskDesc"
            placeholder="Description (optionnel)"
            class="qc-desc"
            rows="2"
            @keydown.escape="newTaskDay = null"
          />
          <div class="qc-footer">
            <select v-model="newTaskProjectId" class="qc-project-select">
              <option v-for="p in projectStore.projects" :key="p.id" :value="p.id">
                {{ p.name }}
              </option>
            </select>
            <div class="qc-actions">
              <button class="btn btn-ghost" @click="newTaskDay = null">Annuler</button>
              <button class="btn btn-primary" @click="createOnDay">Créer</button>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- Panneau "Organiser les tâches" -->
    <div v-if="showOrganizer" class="organizer-panel">
      <div class="org-header">
        <span class="org-title">Organiser les tâches</span>
      </div>
      <div class="org-tabs">
        <button :class="{ active: organizerTab === 'list' }" @click="organizerTab = 'list'">Listes</button>
        <button :class="{ active: organizerTab === 'tag' }" @click="organizerTab = 'tag'">Étiquette</button>
        <button :class="{ active: organizerTab === 'priority' }" @click="organizerTab = 'priority'">Priorité</button>
      </div>

      <!-- Filtres selon l'onglet -->
      <div class="org-filters">
        <template v-if="organizerTab === 'list'">
          <button
            v-for="p in projectStore.projects"
            :key="p.id"
            class="org-chip"
            :class="{ active: organizerListId === p.id }"
            @click="organizerListId = organizerListId === p.id ? null : p.id"
          >{{ p.name }}</button>
        </template>
        <template v-else-if="organizerTab === 'tag'">
          <button
            v-for="tag in tagStore.rootTags"
            :key="tag.id"
            class="org-chip"
            :class="{ active: organizerTagId === tag.id }"
            :style="tag.color ? `border-color: ${tag.color}` : ''"
            @click="organizerTagId = organizerTagId === tag.id ? null : tag.id"
          >{{ tag.name }}</button>
        </template>
        <template v-else>
          <button
            v-for="p in PRIORITIES"
            :key="p.value"
            class="org-chip org-prio-chip"
            :class="{ active: organizerPriority === p.value }"
            :style="`border-left: 3px solid ${p.color}`"
            @click="organizerPriority = organizerPriority === p.value ? null : p.value"
          >{{ p.label }}</button>
        </template>
      </div>

      <!-- Liste des tâches -->
      <div class="org-task-list">
        <div v-if="!panelTasks.length" class="org-empty">
          {{ organizerListId === null && organizerTagId === null && organizerPriority === null
            ? 'Sélectionnez un filtre ci-dessus'
            : 'Aucune tâche' }}
        </div>
        <div
          v-for="t in panelTasks"
          :key="t.id"
          class="org-task"
          draggable="true"
          :style="`border-left: 3px solid ${priorityColor(t.priority)}`"
          @dragstart="onTaskDragStart($event, t)"
          @click="openTask(t)"
        >
          <span class="org-task-title">{{ t.title }}</span>
          <span v-if="t.due_date" class="org-task-date">{{ format(parseISO(t.due_date), 'd MMM', { locale: fr }) }}</span>
        </div>
      </div>
    </div>

    <TaskDetail v-if="taskStore.selectedId" class="cal-detail" />
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

.calendar-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

/* Toolbar */
.cal-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.cal-nav { display: flex; align-items: center; gap: 8px; }
.today-btn {
  padding: 5px 14px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: none;
  cursor: pointer;
  font-size: 13px;
  color: var(--text);
}
.today-btn:hover { background: var(--bg-hover); }
.cal-label { font-size: 16px; font-weight: 600; margin-left: 8px; }

.view-tabs { display: flex; gap: 4px; background: var(--bg-hover); border-radius: 8px; padding: 3px; }
.view-tab { padding: 5px 14px; border-radius: 5px; border: none; cursor: pointer; font-size: 13px; background: none; color: var(--text-secondary); }
.view-tab.active { background: var(--bg); color: var(--text); font-weight: 500; box-shadow: 0 1px 3px rgba(0,0,0,.1); }

/* ── Semaine ─────────────────────────────────────────────── */
.week-view { display: flex; flex-direction: column; flex: 1; overflow: hidden; }

.time-gutter { width: 52px; min-width: 52px; font-size: 11px; color: var(--text-muted); text-align: right; padding-right: 8px; }

.week-header {
  display: grid;
  grid-template-columns: 52px repeat(7, 1fr);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.week-day-head {
  padding: 8px 6px;
  text-align: center;
  border-left: 1px solid var(--border);
}
.week-day-head.today { color: var(--primary); }
.day-name { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); }
.day-num { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 50%; font-size: 16px; font-weight: 600; margin-top: 2px; }
.day-num.today { background: var(--primary); color: #fff; }

.allday-row {
  display: grid;
  grid-template-columns: 52px repeat(7, 1fr);
  border-bottom: 2px solid var(--border);
  flex-shrink: 0;
  min-height: 28px;
}
.allday-label { font-size: 10px; padding-top: 6px; }
.allday-cell { border-left: 1px solid var(--border); padding: 3px 4px; cursor: pointer; }
.allday-cell:hover { background: var(--bg-hover); }

.week-grid-scroll { flex: 1; overflow-y: auto; }
.week-grid { position: relative; }

.hour-row {
  display: grid;
  grid-template-columns: 52px repeat(7, 1fr);
  min-height: var(--hour-px, 40px);
}

/* Mode classique : plus d'espace, police plus grande */
.cal-classic .cal-task { font-size: 12.5px; padding: 3px 6px; }

/* Événements ICS : lecture seule, teinte douce distincte des tâches */
.ics-event {
  cursor: default;
  opacity: 0.85;
  font-style: italic;
}
.cal-classic .time-gutter { font-size: 11px; }
/* Mode moderne : compact */
.cal-modern .cal-task { font-size: 11px; }
.cal-modern .time-gutter { font-size: 10px; }
.hour-cell {
  border-left: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  padding: 2px 3px;
  cursor: pointer;
  position: relative;
  overflow: visible;
}
.hour-cell:hover { background: var(--bg-hover); }
.hour-cell.today { background: #f0f4ff; }
[data-theme='dark'] .hour-cell.today { background: #1a2040; }

.cal-task {
  font-size: 11.5px;
  padding: 2px 5px;
  border-radius: 4px;
  border-left: 3px solid;
  background: var(--primary-soft);
  margin-bottom: 2px;
  cursor: pointer;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.cal-task:hover { filter: brightness(0.95); }
.cal-task.timed { background: var(--bg-active); }
.cal-task.cal-block {
  background: var(--primary-soft);
  display: flex;
  flex-direction: column;
  gap: 1px;
  overflow: hidden;
}
.block-title { font-weight: 500; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.block-time { font-size: 10px; opacity: 0.7; }
.resize-handle {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 8px;
  cursor: ns-resize;
  border-radius: 0 0 4px 4px;
  background: rgba(0,0,0,0.15);
  opacity: 0;
}
.cal-block:hover .resize-handle { opacity: 1; }
.week-grid-scroll.resizing { cursor: ns-resize; user-select: none; }

/* ── Multi-jours ───────────────────────────────────────── */
.multiday-row {
  display: grid;
  grid-template-columns: 52px repeat(7, 1fr);
  border-bottom: 1px solid var(--border);
  min-height: 26px;
  align-items: center;
  background: var(--bg-sidebar);
}
.multiday-label { font-size: 9px; color: var(--text-muted); text-align: right; padding-right: 4px; }
.multiday-bar {
  margin: 2px 1px;
  padding: 2px 6px;
  border-radius: 3px;
  background: var(--primary-soft);
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
}
.multiday-bar:hover { filter: brightness(0.95); }

/* ── Mois ───────────────────────────────────────────────── */
.month-view { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.month-header {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.month-head-cell { padding: 8px; text-align: center; font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; }
.month-grid { display: grid; grid-template-columns: repeat(7, 1fr); flex: 1; overflow-y: auto; }
.month-cell {
  min-height: 90px;
  border-right: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  padding: 4px 6px;
  cursor: pointer;
}
.month-cell:hover { background: var(--bg-hover); }
.month-cell.other-month { opacity: 0.4; }
.month-cell.today { background: var(--primary-soft); }
.month-day-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 4px;
}
.month-day-num.today { background: var(--primary); color: #fff; }
.month-tasks { display: flex; flex-direction: column; gap: 2px; }
.month-task {
  font-size: 11px;
  padding: 1px 5px;
  border-radius: 3px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  cursor: pointer;
}
.month-more { font-size: 10px; color: var(--text-muted); padding-left: 4px; }

/* ── Agenda ─────────────────────────────────────────────── */
.agenda-view { flex: 1; overflow-y: auto; padding: 16px 24px; }
.agenda-day { display: flex; gap: 16px; margin-bottom: 20px; }
.agenda-date { width: 64px; flex-shrink: 0; text-align: center; padding-top: 4px; }
.agenda-weekday { display: block; font-size: 11px; text-transform: uppercase; color: var(--text-muted); }
.agenda-daynum { display: inline-flex; align-items: center; justify-content: center; width: 36px; height: 36px; border-radius: 50%; font-size: 15px; font-weight: 600; margin-top: 2px; }
.agenda-daynum.today { background: var(--primary); color: #fff; }
.agenda-tasks { flex: 1; display: flex; flex-direction: column; gap: 4px; }
.agenda-task {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 8px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-left: 3px solid;
  cursor: pointer;
}
.agenda-task:hover { background: var(--bg-hover); }
.agenda-time { font-size: 12px; color: var(--text-muted); width: 40px; }
.agenda-title { font-size: 13.5px; }
.agenda-add { background: none; border: none; font-size: 12.5px; color: var(--text-muted); cursor: pointer; padding: 4px; text-align: left; }
.agenda-add:hover { color: var(--primary); }

/* Quick create modal */
.quick-create-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.3);
  z-index: 4000;
  display: flex;
  align-items: center;
  justify-content: center;
}
.quick-create-modal {
  background: var(--bg);
  border-radius: 14px;
  padding: 20px;
  width: 340px;
  box-shadow: 0 16px 48px rgba(0,0,0,0.2);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.qc-date { font-size: 13px; color: var(--text-secondary); }
.qc-input {
  padding: 10px 12px;
  border: 1px solid var(--primary);
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  background: var(--bg);
  color: var(--text);
}
.qc-desc {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 13px;
  outline: none;
  background: var(--bg);
  color: var(--text);
  resize: none;
  font-family: inherit;
}
.qc-desc:focus { border-color: var(--primary); }
.qc-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.qc-project-select {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
  color: var(--text);
  font-size: 13px;
  cursor: pointer;
}
.qc-actions { display: flex; gap: 8px; }

.time-mask-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 16px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
  font-size: 12px;
}
.time-mask-slider { flex: 1; }
.time-mask-label { min-width: 70px; color: var(--text-muted); }
.time-mask-reset {
  padding: 2px 8px;
  border: 1px solid var(--border);
  border-radius: 4px;
  cursor: pointer;
  background: var(--bg);
  color: var(--text);
  font-size: 11px;
}

.organizer-panel {
  width: 240px;
  min-width: 240px;
  border-left: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-sidebar);
}

.org-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 14px 8px;
}
.org-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.org-tabs {
  display: flex;
  border-bottom: 1px solid var(--border);
  padding: 0 8px;
  gap: 2px;
}
.org-tabs button {
  padding: 6px 10px;
  font-size: 12px;
  border: none;
  background: none;
  cursor: pointer;
  color: var(--text-muted);
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  border-radius: 0;
}
.org-tabs button.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
  font-weight: 600;
}

.org-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
}
.org-chip {
  padding: 3px 10px;
  font-size: 11.5px;
  border: 1px solid var(--border);
  border-radius: 20px;
  background: none;
  cursor: pointer;
  color: var(--text);
  white-space: nowrap;
  transition: background 0.1s;
}
.org-chip:hover { background: var(--bg-hover); }
.org-chip.active {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
}
.org-prio-chip { border-radius: 4px; }

.org-task-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}
.org-empty {
  padding: 20px 14px;
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
  line-height: 1.5;
}
.org-task {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 7px 12px 7px 10px;
  margin: 0 8px 2px;
  border-radius: 6px;
  border-left: 3px solid transparent;
  cursor: grab;
  background: var(--bg);
  border: 1px solid var(--border);
  border-left-width: 3px;
  font-size: 12.5px;
  transition: box-shadow 0.1s;
}
.org-task:hover { box-shadow: 0 2px 6px rgba(0,0,0,0.08); }
.org-task-title {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text);
}
.org-task-date {
  font-size: 11px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.cal-detail {
  width: 340px;
  min-width: 340px;
  border-left: 1px solid var(--border);
  overflow-y: auto;
}

.allday-cell.drag-over,
.hour-cell.drag-over,
.month-cell.drag-over { background: var(--primary-soft) !important; }
</style>
