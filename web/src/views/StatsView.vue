<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import Sidebar from '@/components/Sidebar.vue'
import { statsApi } from '@/api'
import type { StatsSummary, ProductivityScore } from '@/types'

const summary = ref<StatsSummary | null>(null)
const score = ref<ProductivityScore | null>(null)
const heatmap = ref<Array<{ date: string; count: number }>>([])
const monthly = ref<Array<{ month: string; count: number }>>([])
const loading = ref(true)

onMounted(async () => {
  try {
    ;[summary.value, score.value, heatmap.value, monthly.value] = await Promise.all([
      statsApi.summary(),
      statsApi.score(),
      statsApi.heatmap(),
      statsApi.monthly(),
    ])
  } finally {
    loading.value = false
  }
})

// Heatmap — 52 semaines × 7 jours
const heatmapMap = computed(() => {
  const m: Record<string, number> = {}
  heatmap.value.forEach(d => { m[d.date] = d.count })
  return m
})

function heatmapCells() {
  const cells: Array<{ date: string; count: number }> = []
  const end = new Date()
  const start = new Date(end)
  start.setDate(start.getDate() - 364)
  for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    const iso = d.toISOString().slice(0, 10)
    cells.push({ date: iso, count: heatmapMap.value[iso] ?? 0 })
  }
  return cells
}

function heatColor(n: number) {
  if (n === 0) return 'var(--border)'
  if (n <= 2) return '#c6e8b3'
  if (n <= 5) return '#7bc96f'
  if (n <= 9) return '#239a3b'
  return '#196127'
}

const maxMonthly = computed(() => Math.max(...monthly.value.map(m => m.count), 1))

// Popover heatmap
const heatPopover = ref<{ date: string; count: number; x: number; y: number } | null>(null)

function showHeatPopover(e: MouseEvent, cell: { date: string; count: number }) {
  const rect = (e.target as HTMLElement).getBoundingClientRect()
  heatPopover.value = { ...cell, x: rect.left + rect.width / 2, y: rect.top - 8 }
}
function hideHeatPopover() { heatPopover.value = null }

const LEVEL_COLORS: Record<string, string> = {
  Débutant: '#a3a7ad',
  Régulier: '#4772fa',
  Avancé: '#f59f00',
  Expert: '#e0383e',
}

const bestHour = computed(() => {
  if (!summary.value?.best_hours?.length) return null
  const top = summary.value.best_hours[0]
  return top ? `${top.hour}h–${top.hour + 1}h` : null
})
</script>

<template>
  <div class="app-layout">
    <Sidebar />

    <main class="stats-main">
      <h1 class="stats-title">Statistiques</h1>

      <div v-if="loading" class="loading-msg">Chargement…</div>

      <template v-else>
        <!-- Score de productivité -->
        <div v-if="score" class="card score-card">
          <div class="score-circle" :style="`--sc: ${LEVEL_COLORS[score.level] ?? 'var(--primary)'}`">
            <svg width="120" height="120" viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="50" fill="none" stroke="var(--border)" stroke-width="10" />
              <circle cx="60" cy="60" r="50" fill="none" :stroke="LEVEL_COLORS[score.level] ?? 'var(--primary)'"
                stroke-width="10" stroke-linecap="round"
                :stroke-dasharray="`${2*Math.PI*50}`"
                :stroke-dashoffset="`${2*Math.PI*50 * (1 - score.score / 100)}`"
                transform="rotate(-90 60 60)" />
            </svg>
            <div class="score-num">{{ score.score }}</div>
          </div>
          <div class="score-info">
            <div class="score-level" :style="`color: ${LEVEL_COLORS[score.level] ?? 'var(--primary)'}`">{{ score.level }}</div>
            <div class="score-detail">✅ {{ score.on_time }} à temps · ⚠️ {{ score.late }} en retard</div>
          </div>
        </div>

        <!-- Résumé du jour -->
        <div v-if="summary" class="cards-row">
          <div class="stat-card">
            <div class="stat-num">{{ summary.completed_today }}</div>
            <div class="stat-label">Terminées aujourd'hui</div>
          </div>
          <div class="stat-card danger">
            <div class="stat-num">{{ summary.overdue }}</div>
            <div class="stat-label">En retard</div>
          </div>
          <div v-if="bestHour" class="stat-card accent">
            <div class="stat-num">{{ bestHour }}</div>
            <div class="stat-label">Meilleure heure</div>
          </div>
        </div>

        <!-- Heatmap annuelle -->
        <div class="card">
          <h2 class="section-title">Activité — 12 derniers mois</h2>
          <div class="heatmap">
            <div
              v-for="cell in heatmapCells()"
              :key="cell.date"
              class="heat-cell"
              :style="`background: ${heatColor(cell.count)}`"
              :title="`${cell.date} : ${cell.count} tâche(s)`"
              @mouseenter="showHeatPopover($event, cell)"
              @mouseleave="hideHeatPopover"
            />
          </div>
          <div
            v-if="heatPopover"
            class="heat-popover"
            :style="`left:${heatPopover.x}px; top:${heatPopover.y}px`"
          >
            <div class="heat-pop-date">{{ heatPopover.date }}</div>
            <div class="heat-pop-count">{{ heatPopover.count }} tâche{{ heatPopover.count !== 1 ? 's' : '' }}</div>
          </div>
          <div class="heatmap-legend">
            <span>Moins</span>
            <div class="heat-cell" style="background:#c6e8b3" />
            <div class="heat-cell" style="background:#7bc96f" />
            <div class="heat-cell" style="background:#239a3b" />
            <div class="heat-cell" style="background:#196127" />
            <span>Plus</span>
          </div>
        </div>

        <!-- Historique mensuel -->
        <div class="card">
          <h2 class="section-title">Historique mensuel</h2>
          <div class="monthly-chart">
            <div v-for="m in monthly" :key="m.month" class="month-bar-wrap">
              <div class="month-bar" :style="`height: ${Math.round((m.count / maxMonthly) * 120)}px`" :title="`${m.month}: ${m.count}`" />
              <div class="month-label">{{ m.month?.slice(5) }}</div>
            </div>
          </div>
        </div>

        <!-- Par liste -->
        <div v-if="summary?.by_list?.length" class="card">
          <h2 class="section-title">Par liste</h2>
          <div class="by-list">
            <div v-for="item in summary.by_list" :key="item.project__name" class="list-row">
              <span class="list-name">{{ item.project__name }}</span>
              <div class="list-bar-wrap">
                <div class="list-bar" :style="`width: ${Math.round(item.count / Math.max(...summary!.by_list.map(x => x.count)) * 100)}%`" />
              </div>
              <span class="list-count">{{ item.count }}</span>
            </div>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>

<style scoped>
.app-layout { display: flex; height: 100%; overflow: hidden; }

.stats-main {
  flex: 1;
  overflow-y: auto;
  padding: 28px 32px;
  max-width: 800px;
}

.stats-title { margin: 0 0 24px; font-size: 24px; font-weight: 700; }

.card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 20px;
  margin-bottom: 16px;
}

.section-title { margin: 0 0 16px; font-size: 15px; font-weight: 600; color: var(--text); }

/* Score */
.score-card { display: flex; align-items: center; gap: 24px; }
.score-circle { position: relative; flex-shrink: 0; }
.score-num {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  font-weight: 700;
  color: var(--sc, var(--primary));
}
.score-info { flex: 1; }
.score-level { font-size: 22px; font-weight: 700; }
.score-detail { font-size: 13px; color: var(--text-secondary); margin-top: 6px; }

/* Cartes résumé */
.cards-row { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.stat-card {
  flex: 1;
  min-width: 120px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  text-align: center;
}
.stat-card.danger .stat-num { color: var(--danger); }
.stat-card.accent .stat-num { color: var(--prio-medium); }
.stat-num { font-size: 32px; font-weight: 700; }
.stat-label { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }

/* Heatmap */
.heatmap {
  display: grid;
  grid-template-columns: repeat(53, 1fr);
  grid-template-rows: repeat(7, 1fr);
  grid-auto-flow: column;
  gap: 2px;
}
.heat-cell { width: 100%; aspect-ratio: 1; border-radius: 2px; min-width: 10px; }
.heatmap-legend { display: flex; align-items: center; gap: 4px; margin-top: 8px; font-size: 11px; color: var(--text-muted); }

/* Mensuel */
.monthly-chart { display: flex; align-items: flex-end; gap: 4px; height: 140px; }
.month-bar-wrap { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; gap: 4px; }
.month-bar { width: 100%; background: var(--primary); border-radius: 4px 4px 0 0; min-height: 2px; transition: height 0.3s; }
.month-label { font-size: 10px; color: var(--text-muted); }

/* Par liste */
.by-list { display: flex; flex-direction: column; gap: 8px; }
.list-row { display: flex; align-items: center; gap: 10px; }
.list-name { width: 120px; font-size: 13px; flex-shrink: 0; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.list-bar-wrap { flex: 1; height: 8px; background: var(--border); border-radius: 4px; overflow: hidden; }
.list-bar { height: 100%; background: var(--primary); border-radius: 4px; }
.list-count { font-size: 13px; font-weight: 600; color: var(--text); width: 30px; text-align: right; }

.loading-msg { text-align: center; padding: 60px; color: var(--text-muted); }

.heat-popover {
  position: fixed;
  transform: translateX(-50%) translateY(-100%);
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 12px;
  pointer-events: none;
  z-index: 100;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  white-space: nowrap;
}
.heat-pop-date { font-weight: 600; color: var(--text); }
.heat-pop-count { color: var(--text-muted); margin-top: 2px; }
</style>
