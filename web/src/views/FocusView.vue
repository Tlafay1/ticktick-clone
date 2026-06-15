<script setup lang="ts">
import { ref, computed, onUnmounted, watch } from 'vue'
import Sidebar from '@/components/Sidebar.vue'
import { focusApi, tasksApi } from '@/api'
import type { Task } from '@/types'

// ── Configuration ────────────────────────────────────────────────────────────
const MODES = [
  { key: 'pomodoro',   label: 'Pomodoro',     defaultWork: 25, defaultBreak: 5 },
  { key: 'stopwatch',  label: 'Chronomètre',  defaultWork: 0,  defaultBreak: 0 },
]

const AMBIENT_SOUNDS = [
  { key: 'none',   label: 'Silence' },
  { key: 'rain',   label: '🌧 Pluie' },
  { key: 'forest', label: '🌿 Forêt' },
  { key: 'cafe',   label: '☕ Café' },
  { key: 'waves',  label: '🌊 Vagues' },
]

// ── State ─────────────────────────────────────────────────────────────────────
const mode = ref<'pomodoro' | 'stopwatch'>('pomodoro')
const sessionType = ref<'work' | 'short_break' | 'long_break'>('work')
const workMinutes = ref(25)
const shortBreakMinutes = ref(5)
const longBreakMinutes = ref(15)
const pomodorosBeforeLong = ref(4)
const pomoCount = ref(0)

const running = ref(false)
const elapsed = ref(0)          // secondes écoulées
const sessionStart = ref<Date | null>(null)
const currentSessionId = ref<number | null>(null)
const ambientSound = ref('none')
const linkedTask = ref<Task | null>(null)
const taskQuery = ref('')
const taskResults = ref<Task[]>([])
const showTaskPicker = ref(false)

// Timer
let ticker: ReturnType<typeof setInterval> | null = null

const totalSeconds = computed(() => {
  if (mode.value === 'stopwatch') return null
  const mins = sessionType.value === 'work' ? workMinutes.value
    : sessionType.value === 'short_break' ? shortBreakMinutes.value
    : longBreakMinutes.value
  return mins * 60
})

const remaining = computed(() => {
  if (totalSeconds.value === null) return elapsed.value  // chrono : montre le temps écoulé
  return Math.max(0, totalSeconds.value - elapsed.value)
})

const progress = computed(() => {
  if (!totalSeconds.value) return 0
  return elapsed.value / totalSeconds.value
})

function formatTime(s: number) {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

// Titre de l'onglet (M29)
watch(remaining, (s) => {
  if (running.value) {
    const label = sessionType.value === 'work' ? '🍅' : '☕'
    document.title = `${label} ${formatTime(s)} — Focus`
  }
})

watch(running, (r) => {
  if (!r) document.title = 'TickTick'
})

onUnmounted(() => {
  if (ticker) clearInterval(ticker)
  document.title = 'TickTick'
})

async function startTimer() {
  running.value = true
  elapsed.value = 0
  sessionStart.value = new Date()

  // Créer la session en base
  const session = await focusApi.create({
    mode: mode.value,
    session_type: sessionType.value,
    start_at: sessionStart.value.toISOString(),
    task: linkedTask.value?.id ?? null,
  })
  currentSessionId.value = session.id

  ticker = setInterval(() => {
    elapsed.value++
    if (totalSeconds.value !== null && elapsed.value >= totalSeconds.value) {
      finishTimer()
    }
  }, 1000)
}

async function finishTimer() {
  if (ticker) { clearInterval(ticker); ticker = null }
  running.value = false

  if (currentSessionId.value && sessionStart.value) {
    const durationSeconds = elapsed.value
    await focusApi.update(currentSessionId.value, {
      end_at: new Date().toISOString(),
      duration_seconds: durationSeconds,
    })
    currentSessionId.value = null
  }

  // Avancer le Pomodoro
  if (mode.value === 'pomodoro' && sessionType.value === 'work') {
    pomoCount.value++
    sessionType.value = pomoCount.value % pomodorosBeforeLong.value === 0
      ? 'long_break' : 'short_break'
  } else {
    sessionType.value = 'work'
  }

  elapsed.value = 0
}

function pauseTimer() {
  if (ticker) { clearInterval(ticker); ticker = null }
  running.value = false
}

function resetTimer() {
  pauseTimer()
  elapsed.value = 0
  pomoCount.value = 0
  sessionType.value = 'work'
  currentSessionId.value = null
}

// Recherche de tâche à lier
let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(taskQuery, (q) => {
  if (searchTimer) clearTimeout(searchTimer)
  if (!q.trim()) { taskResults.value = []; return }
  searchTimer = setTimeout(async () => {
    taskResults.value = await tasksApi.list({ q: q.trim(), status: 0 })
  }, 300)
})

function linkTask(t: Task) {
  linkedTask.value = t
  taskQuery.value = ''
  taskResults.value = []
  showTaskPicker.value = false
}

// Arc SVG du timer (cercle)
const RADIUS = 80
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

const strokeDashoffset = computed(() => {
  const p = totalSeconds.value ? Math.min(progress.value, 1) : 0
  return CIRCUMFERENCE * (1 - p)
})

const sessionColor = computed(() => sessionType.value === 'work' ? 'var(--prio-high)' : 'var(--primary)')
</script>

<template>
  <div class="app-layout">
    <Sidebar />

    <main class="focus-main">
      <div class="focus-container">
        <h1 class="focus-title">Focus</h1>

        <!-- Sélecteur de mode -->
        <div class="mode-tabs">
          <button v-for="m in MODES" :key="m.key" class="mode-tab" :class="{ active: mode === m.key }" @click="mode = m.key as 'pomodoro' | 'stopwatch'; resetTimer()">{{ m.label }}</button>
        </div>

        <!-- Types de session (pomodoro uniquement) -->
        <div v-if="mode === 'pomodoro'" class="session-tabs">
          <button class="session-tab" :class="{ active: sessionType === 'work' }" @click="sessionType = 'work'; resetTimer()">🍅 Travail</button>
          <button class="session-tab" :class="{ active: sessionType === 'short_break' }" @click="sessionType = 'short_break'; resetTimer()">☕ Pause courte</button>
          <button class="session-tab" :class="{ active: sessionType === 'long_break' }" @click="sessionType = 'long_break'; resetTimer()">🌴 Pause longue</button>
        </div>

        <!-- Timer circulaire -->
        <div class="timer-ring-wrap">
          <svg class="timer-ring" width="200" height="200" viewBox="0 0 200 200">
            <circle cx="100" cy="100" :r="RADIUS" fill="none" stroke="var(--border)" stroke-width="8" />
            <circle
              cx="100" cy="100" :r="RADIUS"
              fill="none"
              :stroke="sessionColor"
              stroke-width="8"
              stroke-linecap="round"
              :stroke-dasharray="CIRCUMFERENCE"
              :stroke-dashoffset="strokeDashoffset"
              transform="rotate(-90 100 100)"
              style="transition: stroke-dashoffset 1s linear"
            />
          </svg>
          <div class="timer-center">
            <div class="timer-display" :style="`color: ${sessionColor}`">
              {{ mode === 'stopwatch' ? formatTime(elapsed) : formatTime(remaining) }}
            </div>
            <div v-if="mode === 'pomodoro'" class="pomo-count">
              🍅 {{ pomoCount }}<span v-if="linkedTask?.estimated_pomos">/{{ linkedTask.estimated_pomos }}</span>
            </div>
          </div>
        </div>

        <!-- Contrôles -->
        <div class="controls">
          <button v-if="!running" class="ctrl-btn start" :style="`background: ${sessionColor}`" @click="startTimer">▶ Démarrer</button>
          <template v-else>
            <button class="ctrl-btn pause" @click="pauseTimer">⏸ Pause</button>
            <button class="ctrl-btn stop" @click="finishTimer">⏹ Terminer</button>
          </template>
          <button class="ctrl-btn reset" @click="resetTimer">↺</button>
        </div>

        <!-- Tâche liée -->
        <div class="linked-task">
          <div v-if="linkedTask" class="linked-display">
            <span class="linked-label">📌 {{ linkedTask.title }}</span>
            <span v-if="linkedTask.estimated_pomos && mode === 'pomodoro'" class="linked-est">
              🍅 × {{ linkedTask.estimated_pomos }} estimés
            </span>
            <button class="icon-btn" @click="linkedTask = null">✕</button>
          </div>
          <button v-else class="link-task-btn" @click="showTaskPicker = !showTaskPicker">
            ＋ Lier une tâche
          </button>
          <div v-if="showTaskPicker" class="task-picker">
            <input v-model="taskQuery" placeholder="Rechercher une tâche…" class="task-search" autofocus />
            <div class="task-results">
              <button v-for="t in taskResults" :key="t.id" class="task-result-item" @click="linkTask(t)">
                {{ t.title }}
              </button>
              <div v-if="taskQuery && !taskResults.length" class="no-results">Aucune tâche trouvée</div>
            </div>
          </div>
        </div>

        <!-- Durées personnalisées (Pomodoro) -->
        <div v-if="mode === 'pomodoro' && !running" class="durations">
          <div class="duration-row">
            <label>🍅 Travail</label>
            <input v-model.number="workMinutes" type="number" min="1" max="120" class="dur-input" /> min
          </div>
          <div class="duration-row">
            <label>☕ Pause courte</label>
            <input v-model.number="shortBreakMinutes" type="number" min="1" max="30" class="dur-input" /> min
          </div>
          <div class="duration-row">
            <label>🌴 Pause longue</label>
            <input v-model.number="longBreakMinutes" type="number" min="1" max="60" class="dur-input" /> min
          </div>
          <div class="duration-row">
            <label>🍅 Avant grande pause</label>
            <input v-model.number="pomodorosBeforeLong" type="number" min="1" max="10" class="dur-input" />
          </div>
        </div>

        <!-- Son d'ambiance -->
        <div class="ambient-row">
          <span class="ambient-label">Son d'ambiance :</span>
          <div class="ambient-options">
            <button
              v-for="s in AMBIENT_SOUNDS"
              :key="s.key"
              class="ambient-btn"
              :class="{ active: ambientSound === s.key }"
              @click="ambientSound = s.key"
            >{{ s.label }}</button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.app-layout { display: flex; height: 100%; overflow: hidden; }

.focus-main {
  flex: 1;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  overflow-y: auto;
  padding: 32px 20px;
}

.focus-container {
  width: 100%;
  max-width: 480px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.focus-title { margin: 0; font-size: 24px; font-weight: 700; }

.mode-tabs { display: flex; gap: 4px; background: var(--bg-hover); border-radius: 10px; padding: 4px; }
.mode-tab { padding: 6px 20px; border-radius: 7px; border: none; cursor: pointer; font-size: 14px; font-weight: 500; background: none; color: var(--text-secondary); }
.mode-tab.active { background: var(--bg); color: var(--text); box-shadow: 0 1px 4px rgba(0,0,0,0.1); }

.session-tabs { display: flex; gap: 6px; }
.session-tab { padding: 6px 14px; border-radius: 20px; border: 1px solid var(--border); cursor: pointer; font-size: 13px; background: none; color: var(--text-secondary); }
.session-tab.active { background: var(--primary); color: #fff; border-color: var(--primary); }

/* Timer ring */
.timer-ring-wrap { position: relative; width: 200px; height: 200px; }
.timer-ring { position: absolute; inset: 0; }
.timer-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.timer-display { font-size: 44px; font-weight: 700; font-variant-numeric: tabular-nums; }
.pomo-count { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }

/* Contrôles */
.controls { display: flex; gap: 10px; align-items: center; }
.ctrl-btn {
  padding: 10px 28px;
  border-radius: 24px;
  border: none;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}
.ctrl-btn.start { color: #fff; }
.ctrl-btn.pause { background: var(--bg-hover); color: var(--text); }
.ctrl-btn.stop { background: var(--danger); color: #fff; }
.ctrl-btn.reset { background: var(--bg-hover); color: var(--text-secondary); padding: 10px 14px; font-size: 18px; }

/* Tâche liée */
.linked-task { width: 100%; }
.linked-display { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: var(--bg-hover); border-radius: 8px; }
.linked-label { flex: 1; font-size: 13.5px; }
.linked-est { font-size: 12px; color: var(--text-secondary); flex-shrink: 0; }
.link-task-btn { font-size: 13px; color: var(--text-secondary); border: 1px dashed var(--border); border-radius: 8px; padding: 7px 14px; cursor: pointer; background: none; }
.link-task-btn:hover { border-color: var(--primary); color: var(--primary); }
.task-picker { margin-top: 8px; border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
.task-search { width: 100%; padding: 8px 12px; border: none; border-bottom: 1px solid var(--border); font-size: 14px; background: var(--bg); color: var(--text); outline: none; box-sizing: border-box; }
.task-results { max-height: 180px; overflow-y: auto; }
.task-result-item { display: block; width: 100%; padding: 8px 12px; text-align: left; border: none; background: none; cursor: pointer; font-size: 13.5px; color: var(--text); }
.task-result-item:hover { background: var(--bg-hover); }
.no-results { padding: 12px; text-align: center; color: var(--text-muted); font-size: 13px; }

/* Durées */
.durations { width: 100%; display: flex; flex-direction: column; gap: 8px; padding: 12px; background: var(--bg-hover); border-radius: 10px; }
.duration-row { display: flex; align-items: center; gap: 10px; font-size: 13.5px; }
.duration-row label { flex: 1; }
.dur-input { width: 52px; padding: 4px 6px; border: 1px solid var(--border); border-radius: 6px; text-align: center; background: var(--bg); color: var(--text); }

/* Ambiance */
.ambient-row { width: 100%; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.ambient-label { font-size: 13px; color: var(--text-secondary); flex-shrink: 0; }
.ambient-options { display: flex; gap: 6px; flex-wrap: wrap; }
.ambient-btn { padding: 4px 12px; border-radius: 14px; border: 1px solid var(--border); background: none; font-size: 12.5px; cursor: pointer; color: var(--text-secondary); }
.ambient-btn:hover { border-color: var(--primary); color: var(--primary); }
.ambient-btn.active { background: var(--primary-soft); color: var(--primary); border-color: var(--primary); }
</style>
