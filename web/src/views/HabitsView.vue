<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { habitsApi } from '@/api'
import type { Habit, HabitCheckIn } from '@/types'
import Sidebar from '@/components/Sidebar.vue'

const habits = ref<Habit[]>([])
const loading = ref(false)
const checkIns = ref<Record<number, HabitCheckIn[]>>({})
const showCreate = ref(false)
const showPresets = ref(false)
const presets = ref<Partial<Habit>[]>([])

const today = new Date().toISOString().slice(0, 10)

const newHabit = ref({ name: '', icon: '⭐', color: '#4772fa', goal_type: 'binary' as 'binary' | 'numeric', goal_value: 1, goal_unit: '', frequency: 'daily' as Habit['frequency'] })

async function load() {
  loading.value = true
  try {
    habits.value = await habitsApi.list()
    await Promise.all(habits.value.map(async (h) => {
      checkIns.value[h.id] = await habitsApi.checkIns(h.id)
    }))
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  load()
  presets.value = await habitsApi.presets()
})

function todayCheckIn(habitId: number) {
  return checkIns.value[habitId]?.find(c => c.date === today) ?? null
}

function isDoneToday(habitId: number) {
  return todayCheckIn(habitId)?.completed ?? false
}

function todayQty(habitId: number) {
  return todayCheckIn(habitId)?.quantity ?? 0
}

async function checkInBinary(habit: Habit) {
  const ci = todayCheckIn(habit.id)
  if (ci?.completed) return // déjà fait
  const result = await habitsApi.checkIn(habit.id, { date: today })
  if (!checkIns.value[habit.id]) checkIns.value[habit.id] = []
  const idx = checkIns.value[habit.id].findIndex(c => c.date === today)
  if (idx >= 0) checkIns.value[habit.id][idx] = result
  else checkIns.value[habit.id].push(result)
}

const numericInputs = ref<Record<number, number>>({})

async function checkInNumeric(habit: Habit) {
  const qty = numericInputs.value[habit.id] ?? 1
  const result = await habitsApi.checkIn(habit.id, { date: today, quantity: qty })
  if (!checkIns.value[habit.id]) checkIns.value[habit.id] = []
  const idx = checkIns.value[habit.id].findIndex(c => c.date === today)
  if (idx >= 0) checkIns.value[habit.id][idx] = result
  else checkIns.value[habit.id].push(result)
}

async function create() {
  const h = await habitsApi.create({ ...newHabit.value })
  habits.value.push(h)
  checkIns.value[h.id] = []
  showCreate.value = false
  newHabit.value = { name: '', icon: '⭐', color: '#4772fa', goal_type: 'binary', goal_value: 1, goal_unit: '', frequency: 'daily' }
}

async function fromPreset(preset: Partial<Habit>) {
  const h = await habitsApi.create(preset)
  habits.value.push(h)
  checkIns.value[h.id] = []
  showPresets.value = false
}

async function archive(h: Habit) {
  await habitsApi.update(h.id, { archived: true })
  habits.value = habits.value.filter(x => x.id !== h.id)
}

const activeHabits = computed(() => habits.value.filter(h => !h.archived))

function streakLabel(n: number) {
  return n === 0 ? '' : `🔥 ${n}`
}

const ICONS = ['⭐', '💧', '🏃', '📚', '🧘', '😴', '🥗', '💊', '🎯', '💪', '🎵', '✏️', '🌿', '☕', '🚴']
const COLORS = ['#4772fa', '#34c6a0', '#e03131', '#f59f00', '#6741d9', '#c2255c', '#2f9e44', '#1098ad', '#e8590c', '#495057']

// ── Vue calendrier mensuel ────────────────────────────────────────────────────

type ViewTab = 'today' | 'calendar'
const viewTab = ref<ViewTab>('today')
const calYear = ref(new Date().getFullYear())
const calMonth = ref(new Date().getMonth()) // 0-indexed

const calDays = computed(() => {
  const y = calYear.value
  const m = calMonth.value
  const first = new Date(y, m, 1).getDay() // 0=dim
  const daysInMonth = new Date(y, m + 1, 0).getDate()
  const cells: Array<{ date: string; day: number } | null> = []
  const startOffset = (first + 6) % 7 // lundi = 0
  for (let i = 0; i < startOffset; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) {
    const iso = `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    cells.push({ date: iso, day: d })
  }
  return cells
})

const calMonthLabel = computed(() =>
  new Date(calYear.value, calMonth.value, 1).toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })
)

function prevMonth() {
  if (calMonth.value === 0) { calMonth.value = 11; calYear.value-- }
  else calMonth.value--
}
function nextMonth() {
  if (calMonth.value === 11) { calMonth.value = 0; calYear.value++ }
  else calMonth.value++
}

function checkInsForDay(habitId: number, date: string) {
  return checkIns.value[habitId]?.filter(c => c.date === date) ?? []
}

function isDoneOnDay(habit: Habit, date: string) {
  const cis = checkInsForDay(habit.id, date)
  if (!cis.length) return false
  if (habit.goal_type === 'binary') return cis.some(c => c.completed)
  const total = cis.reduce((s, c) => s + (c.quantity ?? 0), 0)
  return total >= (habit.goal_value ?? 1)
}
</script>

<template>
  <div class="app-layout">
    <Sidebar />

    <main class="habits-main">
      <div class="habits-header">
        <h1>Habitudes</h1>
        <div class="header-actions">
          <div class="view-tabs">
            <button class="view-tab" :class="{ active: viewTab === 'today' }" @click="viewTab = 'today'">Aujourd'hui</button>
            <button class="view-tab" :class="{ active: viewTab === 'calendar' }" @click="viewTab = 'calendar'">Calendrier</button>
          </div>
          <button class="btn btn-ghost" @click="showPresets = !showPresets">📋 Presets</button>
          <button class="btn btn-primary" @click="showCreate = !showCreate">＋ Nouvelle habitude</button>
        </div>
      </div>

      <!-- Formulaire création -->
      <div v-if="showCreate" class="create-form card">
        <div class="form-row">
          <div class="icon-picker">
            <button v-for="ic in ICONS" :key="ic" class="icon-opt" :class="{ sel: newHabit.icon === ic }" @click="newHabit.icon = ic">{{ ic }}</button>
          </div>
          <input v-model="newHabit.name" placeholder="Nom de l'habitude" class="field-input flex-1" />
        </div>
        <div class="form-row">
          <div class="color-row">
            <button v-for="c in COLORS" :key="c" class="color-dot" :class="{ sel: newHabit.color === c }" :style="`background:${c}`" @click="newHabit.color = c" />
          </div>
          <select v-model="newHabit.frequency" class="freq-select">
            <option value="daily">Quotidien</option>
            <option value="weekly">Hebdomadaire</option>
          </select>
        </div>
        <div class="form-row">
          <label class="rec-radio"><input type="radio" v-model="newHabit.goal_type" value="binary" /> Binaire (oui/non)</label>
          <label class="rec-radio"><input type="radio" v-model="newHabit.goal_type" value="numeric" /> Numérique</label>
          <template v-if="newHabit.goal_type === 'numeric'">
            <input v-model.number="newHabit.goal_value" type="number" min="1" class="num-input" />
            <input v-model="newHabit.goal_unit" placeholder="unité" class="unit-input" />
          </template>
        </div>
        <div class="form-actions">
          <button class="btn btn-ghost" @click="showCreate = false">Annuler</button>
          <button class="btn btn-primary" :disabled="!newHabit.name.trim()" @click="create">Créer</button>
        </div>
      </div>

      <!-- Presets -->
      <div v-if="showPresets" class="presets-row">
        <button v-for="p in presets" :key="p.name" class="preset-card" @click="fromPreset(p)">
          <span class="preset-icon">{{ p.icon ?? '⭐' }}</span>
          <span>{{ p.name }}</span>
        </button>
      </div>

      <div v-if="loading" class="loading-msg">Chargement…</div>

      <!-- ── Vue Aujourd'hui ── -->
      <div v-if="viewTab === 'today'" class="habits-grid">
        <div v-for="h in activeHabits" :key="h.id" class="habit-card" :style="`--hc: ${h.color}`">
          <div class="habit-top">
            <span class="habit-icon">{{ h.icon }}</span>
            <div class="habit-info">
              <div class="habit-name">{{ h.name }}</div>
              <div class="habit-meta">
                <span class="streak-label">{{ streakLabel(h.streak) }}</span>
                <span class="max-streak" v-if="h.max_streak > 0">max {{ h.max_streak }}</span>
              </div>
            </div>
            <button class="icon-btn habit-menu" @click="archive(h)" title="Archiver">⋯</button>
          </div>

          <!-- Check-in binaire -->
          <div v-if="h.goal_type === 'binary' || h.check_in_mode === 'binary'" class="checkin-area">
            <button
              class="checkin-btn"
              :class="{ done: isDoneToday(h.id) }"
              :style="`--hc: ${h.color}`"
              @click="checkInBinary(h)"
            >
              <span v-if="isDoneToday(h.id)">✓ Fait</span>
              <span v-else>Marquer fait</span>
            </button>
          </div>

          <!-- Check-in numérique -->
          <div v-else class="checkin-area numeric">
            <div class="numeric-progress">
              <span class="qty-done">{{ todayQty(h.id) }}</span>
              <span class="qty-sep">/</span>
              <span class="qty-goal">{{ h.goal_value }} {{ h.goal_unit }}</span>
            </div>
            <div class="numeric-input">
              <input v-model.number="numericInputs[h.id]" type="number" min="1" :placeholder="String(h.goal_value)" class="num-input-sm" />
              <button class="checkin-btn-sm" :style="`background:${h.color}`" @click="checkInNumeric(h)">+</button>
            </div>
          </div>

          <!-- Ministreak 7 derniers jours -->
          <div class="week-dots">
            <div v-for="d in 7" :key="d" class="day-dot"
              :class="{ filled: checkIns[h.id]?.some(c => c.date === new Date(Date.now() - (7-d)*86400000).toISOString().slice(0,10) && c.completed) }"
              :style="checkIns[h.id]?.some(c => c.date === new Date(Date.now() - (7-d)*86400000).toISOString().slice(0,10) && c.completed) ? `background:${h.color}` : ''"
              :title="new Date(Date.now() - (7-d)*86400000).toLocaleDateString('fr-FR', {weekday:'short'})"
            />
          </div>
        </div>

        <div v-if="!loading && activeHabits.length === 0" class="empty-habits">
          <div class="empty-icon">🌱</div>
          <p>Aucune habitude. Créez-en une ou choisissez un preset.</p>
        </div>
      </div>

      <!-- ── Vue Calendrier mensuel ── -->
      <div v-if="viewTab === 'calendar'" class="cal-view">
        <div class="cal-nav">
          <button class="icon-btn" @click="prevMonth">◀</button>
          <span class="cal-month-label">{{ calMonthLabel }}</span>
          <button class="icon-btn" @click="nextMonth">▶</button>
        </div>
        <div class="cal-habits-legend">
          <span v-for="h in activeHabits" :key="h.id" class="legend-item">
            <span class="legend-dot" :style="`background:${h.color}`" /> {{ h.icon }} {{ h.name }}
          </span>
        </div>
        <div class="cal-grid">
          <div v-for="dow in ['L','M','M','J','V','S','D']" :key="dow" class="cal-dow">{{ dow }}</div>
          <div
            v-for="(cell, i) in calDays" :key="i"
            class="cal-cell"
            :class="{ today: cell?.date === today, empty: !cell }"
          >
            <span v-if="cell" class="cal-day-num">{{ cell.day }}</span>
            <div v-if="cell" class="cal-dots">
              <span
                v-for="h in activeHabits" :key="h.id"
                class="cal-dot"
                :style="isDoneOnDay(h, cell.date) ? `background:${h.color}` : 'background:var(--border)'"
                :title="h.name"
              />
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.app-layout { display: flex; height: 100%; overflow: hidden; }

.habits-main {
  flex: 1;
  overflow-y: auto;
  padding: 28px 32px;
  max-width: 900px;
}

.habits-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}
.habits-header h1 { margin: 0; font-size: 24px; font-weight: 700; }
.header-actions { display: flex; gap: 10px; }

/* Formulaire */
.create-form {
  margin-bottom: 20px;
  padding: 16px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: var(--bg);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.form-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.form-actions { display: flex; justify-content: flex-end; gap: 8px; }
.flex-1 { flex: 1; }

.field-input {
  padding: 7px 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  background: var(--bg);
  color: var(--text);
  outline: none;
}
.field-input:focus { border-color: var(--primary); }

.icon-picker { display: flex; flex-wrap: wrap; gap: 4px; max-width: 200px; }
.icon-opt { width: 30px; height: 30px; border-radius: 6px; border: 2px solid transparent; cursor: pointer; font-size: 16px; background: var(--bg-hover); }
.icon-opt.sel { border-color: var(--primary); }

.color-row { display: flex; gap: 6px; }
.color-dot { width: 22px; height: 22px; border-radius: 50%; border: 3px solid transparent; cursor: pointer; }
.color-dot.sel { border-color: var(--text); }

.freq-select { padding: 6px 8px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); }
.rec-radio { display: flex; align-items: center; gap: 5px; font-size: 13px; cursor: pointer; }
.num-input { width: 56px; padding: 5px; border: 1px solid var(--border); border-radius: 6px; text-align: center; background: var(--bg); color: var(--text); }
.unit-input { width: 80px; padding: 5px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); }

/* Presets */
.presets-row { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }
.preset-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border: 1px solid var(--border);
  border-radius: 20px;
  cursor: pointer;
  font-size: 13px;
  background: var(--bg);
  color: var(--text);
}
.preset-card:hover { border-color: var(--primary); color: var(--primary); }
.preset-icon { font-size: 16px; }

/* Grille habitudes */
.habits-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.habit-card {
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px;
  background: var(--bg);
  border-top: 3px solid var(--hc, var(--primary));
}

.habit-top { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 12px; }
.habit-icon { font-size: 24px; line-height: 1; }
.habit-info { flex: 1; }
.habit-name { font-size: 15px; font-weight: 600; }
.habit-meta { display: flex; gap: 8px; margin-top: 2px; align-items: center; }
.streak-label { font-size: 12px; color: var(--text-secondary); }
.max-streak { font-size: 11px; color: var(--text-muted); }
.habit-menu { opacity: 0; color: var(--text-muted); }
.habit-card:hover .habit-menu { opacity: 1; }

.checkin-area { margin-bottom: 12px; }
.checkin-btn {
  width: 100%;
  padding: 8px;
  border-radius: 8px;
  border: 2px solid var(--hc, var(--primary));
  background: none;
  color: var(--hc, var(--primary));
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}
.checkin-btn:hover { background: var(--hc, var(--primary)); color: #fff; }
.checkin-btn.done { background: var(--hc, var(--primary)); color: #fff; }

.checkin-area.numeric { display: flex; align-items: center; justify-content: space-between; }
.numeric-progress { display: flex; align-items: baseline; gap: 2px; }
.qty-done { font-size: 20px; font-weight: 700; color: var(--hc, var(--primary)); }
.qty-sep { color: var(--text-muted); margin: 0 2px; }
.qty-goal { font-size: 13px; color: var(--text-secondary); }
.numeric-input { display: flex; gap: 6px; }
.num-input-sm { width: 52px; padding: 4px 6px; border: 1px solid var(--border); border-radius: 6px; text-align: center; background: var(--bg); color: var(--text); }
.checkin-btn-sm { width: 32px; height: 32px; border-radius: 8px; border: none; color: #fff; font-size: 18px; cursor: pointer; }

/* Mini-calendrier 7j */
.week-dots { display: flex; gap: 4px; justify-content: space-between; }
.day-dot {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: var(--border);
  transition: background 0.2s;
}
.day-dot.filled { /* background set inline */ }

.empty-habits { grid-column: 1/-1; text-align: center; padding: 60px 20px; color: var(--text-muted); }
.empty-icon { font-size: 40px; margin-bottom: 12px; }

.loading-msg { text-align: center; padding: 40px; color: var(--text-muted); }

.view-tabs { display: flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }
.view-tab { padding: 5px 12px; font-size: 13px; border: none; background: none; cursor: pointer; color: var(--text-muted); }
.view-tab.active { background: var(--accent); color: #fff; }
.view-tab:hover:not(.active) { background: var(--bg-hover); }

/* Calendrier mensuel */
.cal-view { margin-top: 8px; }
.cal-nav { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.cal-month-label { font-size: 16px; font-weight: 600; min-width: 180px; text-align: center; }

.cal-habits-legend { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.legend-item { display: flex; align-items: center; gap: 4px; font-size: 12px; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }

.cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}
.cal-dow { text-align: center; font-size: 11px; font-weight: 600; color: var(--text-muted); padding: 4px 0; }
.cal-cell {
  min-height: 56px;
  padding: 4px 6px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-card);
}
.cal-cell.empty { border: none; background: none; }
.cal-cell.today { border-color: var(--accent); }
.cal-day-num { font-size: 12px; font-weight: 500; color: var(--text-muted); display: block; margin-bottom: 3px; }
.cal-dots { display: flex; flex-wrap: wrap; gap: 2px; }
.cal-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
</style>
