<script setup lang="ts">
// Méthode — en tête d'« Aujourd'hui » : couleur du jour, créneaux avec leur
// prochaine action (démarrer en un geste), compteur limité, rappels de revue.
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { methodApi, occurrencesApi } from '@/api'
import { pushToast } from '@/composables/useToast'
import { DAY_COLORS, canStart, localTime, occurrenceLabel, todayLimitState } from '@/lib/method'
import { useTaskStore } from '@/stores/tasks'
import type { DayColor, MethodToday, SlotOccurrence } from '@/types'

const router = useRouter()
const taskStore = useTaskStore()
const data = ref<MethodToday | null>(null)
const editingColor = ref(false)
const busy = ref(false)

async function load() {
  data.value = await methodApi.today().catch(() => null)
}

onMounted(load)
// Le compteur suit les ajouts / complétions de la liste affichée.
watch(() => taskStore.tasks.length, load)

const colorInfo = computed(() => DAY_COLORS.find(c => c.key === data.value?.color))
const limitState = computed(() =>
  data.value ? todayLimitState(data.value.today_count, data.value.today_limit) : 'ok')

async function setColor(color: DayColor) {
  await methodApi.setDay(color)
  editingColor.value = false
  await load()
}

function isFreeBuffer(occ: SlotOccurrence) {
  return occ.kind === 'buffer' && occ.recovers === null
}

async function start(occ: SlotOccurrence) {
  if (busy.value) return
  busy.value = true
  try {
    await occurrencesApi.start(occ.id)
    router.push('/focus')
  } finally {
    busy.value = false
  }
}

async function joker(occ: SlotOccurrence) {
  if (!data.value) return
  // Renoncer reste un choix explicite (la friction est voulue).
  const left = data.value.jokers_remaining
  if (!confirm(`Utiliser un joker pour ce créneau ? (${left} restant${left > 1 ? 's' : ''} ce mois-ci)`)) return
  await occurrencesApi.joker(occ.id)
  pushToast('Joker utilisé — sans rattrapage, sans culpabilité.', 'success')
  await load()
}
</script>

<template>
  <section v-if="data" class="method-panel">
    <p v-if="data.paused" class="pause-banner">
      ⏸ Pause{{ data.pause_until ? ` jusqu'au ${new Date(data.pause_until).toLocaleDateString('fr-FR')}` : '' }}
      — rien ne compte, repose-toi.
    </p>

    <div class="day-row">
      <template v-if="!data.color || editingColor">
        <span class="day-question">Comment est ta journée ?</span>
        <button
          v-for="c in DAY_COLORS"
          :key="c.key"
          class="color-btn"
          :class="{ active: data.color === c.key }"
          :title="c.hint"
          @click="setColor(c.key)"
        >{{ c.emoji }} {{ c.label }}</button>
      </template>
      <template v-else-if="colorInfo">
        <span class="day-chip">{{ colorInfo.emoji }} {{ colorInfo.hint }}</span>
        <button class="link-btn" @click="editingColor = true">changer</button>
      </template>
      <span class="today-count" :class="limitState">
        {{ data.today_count }} / {{ data.today_limit }} aujourd'hui
      </span>
    </div>
    <p v-if="limitState === 'over'" class="over-hint">
      Plus de {{ data.today_limit }} tâches : choisis les {{ data.today_limit }} qui comptent, le reste attend.
    </p>

    <ul v-if="data.occurrences.length" class="occ-list">
      <li v-for="occ in data.occurrences" :key="occ.id" class="occ" :class="occ.status">
        <span class="occ-time">{{ localTime(occ.start_at) }}</span>
        <span class="occ-body">
          <span v-if="isFreeBuffer(occ)" class="occ-action">Temps libre — tu es à jour 🎉</span>
          <template v-else>
            <span v-if="occ.kind === 'buffer'" class="occ-tag">Rattrapage</span>
            <span class="occ-action">
              {{ occ.next_action?.title ?? 'Aucune action prête : ajoute-en une à ton objectif' }}
            </span>
          </template>
        </span>
        <span class="occ-status">{{ occurrenceLabel(occ) }}</span>
        <button
          v-if="!isFreeBuffer(occ) && canStart(occ)"
          class="btn btn-primary occ-start"
          :disabled="busy"
          @click="start(occ)"
        >▶ 10 min</button>
        <button
          v-else-if="occ.kind === 'work' && occ.status === 'planned' && data.jokers_remaining > 0"
          class="btn btn-ghost"
          @click="joker(occ)"
        >Joker</button>
      </li>
    </ul>

    <div v-if="data.proposals_count || data.review_pending" class="method-links">
      <RouterLink v-if="data.review_pending" to="/review" class="method-link">
        🗓️ Ta revue de la semaine t'attend
      </RouterLink>
      <RouterLink v-if="data.proposals_count" to="/proposals" class="method-link">
        ✨ {{ data.proposals_count }} proposition{{ data.proposals_count > 1 ? 's' : '' }} à valider
      </RouterLink>
    </div>
  </section>
</template>

<style scoped>
.method-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0 20px 8px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg);
}
.pause-banner, .over-hint { margin: 0; font-size: 13px; color: var(--text-secondary); }
.day-row { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.day-question { font-weight: 600; margin-right: 4px; }
.color-btn {
  padding: 4px 10px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: transparent;
  color: var(--text);
  cursor: pointer;
  font: inherit;
  font-size: 13px;
}
.color-btn:hover, .color-btn.active { background: var(--bg-hover); }
.day-chip { font-size: 13px; }
.link-btn {
  border: none;
  background: none;
  color: var(--primary);
  cursor: pointer;
  font: inherit;
  font-size: 13px;
}
.today-count { margin-left: auto; font-size: 13px; color: var(--text-secondary); }
.today-count.full { color: var(--text); font-weight: 600; }
.today-count.over { color: var(--prio-medium); font-weight: 600; }
.occ-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.occ {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 36px;
  font-size: 14px;
}
.occ-time { font-variant-numeric: tabular-nums; color: var(--text-secondary); width: 44px; }
.occ-body { flex: 1; min-width: 0; display: flex; align-items: center; gap: 6px; }
.occ-action { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.occ-tag {
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--primary-soft);
  color: var(--primary);
  font-size: 11px;
}
.occ-status { font-size: 12px; color: var(--text-muted); }
.occ.honored .occ-action, .occ.recovered .occ-action { color: var(--text-muted); text-decoration: line-through; }
.occ-start { flex-shrink: 0; }
.method-links { display: flex; flex-wrap: wrap; gap: 12px; }
.method-link { font-size: 13px; color: var(--primary); text-decoration: none; }
.method-link:hover { text-decoration: underline; }

@media (max-width: 640px) {
  .method-panel { margin: 0 12px 8px; }
  .today-count { margin-left: 0; width: 100%; }
}
</style>
