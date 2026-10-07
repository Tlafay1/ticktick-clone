<script setup lang="ts">
// Revue hebdo (M41) : le seul moment où l'on décide. Bilan → ce qui coince →
// niveau → semaine prochaine → valider. Le coach IA peut l'avoir préparée.
import { computed, onMounted, ref } from 'vue'
import Sidebar from '@/components/Sidebar.vue'
import { methodApi, occurrencesApi, tasksApi } from '@/api'
import { pushToast } from '@/composables/useToast'
import {
  BLOCKERS, DAY_COLORS, SUGGESTION_TEXT, localTime, occurrenceLabel, scorePercent,
} from '@/lib/method'
import { useProjectStore } from '@/stores/projects'
import type { Blocker, SlotOccurrence, Task, WeeklyReview } from '@/types'

const projectStore = useProjectStore()
const review = ref<WeeklyReview | null>(null)
const remedies = ref<Record<number, string>>({})
const level = ref(1)
const notes = ref('')
const nextWeek = ref<SlotOccurrence[]>([])
const candidates = ref<Task[]>([])
const saving = ref(false)

function addDays(iso: string, n: number) {
  const d = new Date(`${iso}T12:00:00`)
  d.setDate(d.getDate() + n)
  return d.toISOString().slice(0, 10)
}

async function load() {
  const r = await methodApi.review()
  review.value = r
  notes.value = r.notes
  level.value = r.suggestion === 'up' ? r.level + 1
    : r.suggestion === 'down' ? Math.max(1, r.level - 1) : r.level
  const nextStart = addDays(r.week_start, 7)
  nextWeek.value = await occurrencesApi.list(nextStart, addDays(nextStart, 6)).catch(() => [])
  // Tâches candidates : celles des objectifs actifs.
  if (!projectStore.projects.length) await projectStore.load()
  const objectives = projectStore.projects.filter(p => p.objective === 'active')
  const lists = await Promise.all(objectives.map(p => tasksApi.list({ project: p.id, status: 0 })))
  candidates.value = lists.flat()
}

onMounted(load)

const weekLabel = computed(() => {
  if (!review.value) return ''
  const fmt = (iso: string) => new Date(`${iso}T12:00:00`).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' })
  return `Semaine du ${fmt(review.value.week_start)} au ${fmt(review.value.week_end)}`
})

const done = computed(() => Boolean(review.value?.completed_at))

async function diagnose(task: { id: number }, reason: Blocker) {
  const res = await tasksApi.diagnose(task.id, reason)
  remedies.value = { ...remedies.value, [task.id]: res.remedy }
}

async function assign(occ: SlotOccurrence, value: string) {
  const updated = await occurrencesApi.assign(occ.id, value ? Number(value) : null)
  nextWeek.value = nextWeek.value.map(o => (o.id === updated.id ? updated : o))
}

function dayName(iso: string) {
  return new Date(`${iso}T12:00:00`).toLocaleDateString('fr-FR', { weekday: 'long' })
}

async function complete() {
  if (!review.value) return
  saving.value = true
  try {
    review.value = await methodApi.completeReview({
      week: review.value.week_start, level: level.value, notes: notes.value,
    })
    pushToast('Revue faite 🎉 La semaine est prête.', 'success')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="app-layout">
    <Sidebar />
    <main class="review-main">
      <div v-if="review" class="review">
        <header class="review-head">
          <h1>Revue de la semaine</h1>
          <p class="sub">{{ weekLabel }}</p>
          <p v-if="done" class="done-banner">
            ✓ Revue validée le {{ new Date(review.completed_at!).toLocaleString('fr-FR') }}
          </p>
        </header>

        <section class="step">
          <h2><span class="num">1</span> Ce que tu as fait</h2>
          <div class="score">
            <span class="score-value">{{ scorePercent(review.score.rate) }}</span>
            <span class="score-detail">
              {{ review.score.honored }} créneau{{ review.score.honored > 1 ? 'x' : '' }} honoré{{ review.score.honored > 1 ? 's' : '' }}
              sur {{ review.score.decided }} · {{ review.focus_minutes }} min de focus
            </span>
          </div>
          <p class="colors">
            <span v-for="c in DAY_COLORS" :key="c.key">{{ c.emoji }} {{ review.day_colors[c.key] }}</span>
          </p>
          <ul v-if="review.completed.length" class="plain">
            <li v-for="t in review.completed" :key="t.id">✓ {{ t.title }}</li>
          </ul>
          <p v-else class="muted">Aucune tâche terminée cette semaine — la revue sert justement à repartir.</p>
        </section>

        <section class="step">
          <h2><span class="num">2</span> Ce qui coince</h2>
          <p v-if="!review.blocked.length && !review.amnesty.length" class="muted">Rien ne coince. 👌</p>
          <div v-for="t in review.blocked" :key="t.id" class="blocked">
            <span class="blocked-title">{{ t.title }}</span>
            <p v-if="remedies[t.id]" class="remedy">{{ remedies[t.id] }}</p>
            <div v-else class="reasons">
              <span class="muted">Qu'est-ce qui coince ?</span>
              <button v-for="b in BLOCKERS" :key="b.key" class="chip" @click="diagnose(t, b.key)">
                {{ b.label }}
              </button>
            </div>
          </div>
          <div v-if="review.amnesty.length" class="amnesty">
            <p>
              <strong>Amnistie :</strong> ces retards de plus de 7 jours retrouvent leur liste,
              sans date. L'ardoise est propre.
            </p>
            <ul class="plain">
              <li v-for="t in review.amnesty" :key="t.id">{{ t.title }}</li>
            </ul>
          </div>
        </section>

        <section class="step">
          <h2><span class="num">3</span> À trier</h2>
          <p>
            <RouterLink to="/inbox">Inbox : {{ review.inbox_count }} élément{{ review.inbox_count > 1 ? 's' : '' }}</RouterLink>
            ·
            <RouterLink to="/proposals">{{ review.proposals_count }} proposition{{ review.proposals_count > 1 ? 's' : '' }}</RouterLink>
            · {{ review.jokers_remaining }} joker{{ review.jokers_remaining > 1 ? 's' : '' }} restant{{ review.jokers_remaining > 1 ? 's' : '' }}
          </p>
        </section>

        <section class="step">
          <h2><span class="num">4</span> Niveau</h2>
          <p>{{ SUGGESTION_TEXT[review.suggestion] }}</p>
          <div class="levels">
            <label v-for="l in [review.level - 1, review.level, review.level + 1].filter(n => n >= 1)" :key="l" class="level">
              <input v-model="level" type="radio" :value="l" :disabled="done" />
              Niveau {{ l }}<span v-if="l === review.level"> (actuel)</span>
            </label>
          </div>
          <p class="muted">Ajuste tes créneaux dans Réglages → Méthode si tu changes de niveau.</p>
        </section>

        <section class="step">
          <h2><span class="num">5</span> Semaine prochaine</h2>
          <p v-if="!nextWeek.length" class="muted">Aucun créneau : configure-les dans Réglages → Méthode.</p>
          <div v-for="occ in nextWeek" :key="occ.id" class="next-occ">
            <span class="next-when">{{ dayName(occ.date) }} {{ localTime(occ.start_at) }}</span>
            <span v-if="occ.kind === 'buffer'" class="muted">Tampon (rattrapages)</span>
            <select
              v-else
              :value="occ.task ?? ''"
              @change="assign(occ, ($event.target as HTMLSelectElement).value)"
            >
              <option value="">Auto : {{ occ.next_action?.title ?? 'prochaine action de l\'objectif' }}</option>
              <option v-for="t in candidates" :key="t.id" :value="t.id">{{ t.title }}</option>
            </select>
            <span class="muted">{{ occurrenceLabel(occ) }}</span>
          </div>
        </section>

        <section class="step">
          <h2><span class="num">6</span> Valider</h2>
          <textarea v-model="notes" rows="3" placeholder="Une note pour toi (facultatif)" :disabled="done" />
          <button v-if="!done" class="btn btn-primary" :disabled="saving" @click="complete">
            Valider la revue
          </button>
        </section>
      </div>
    </main>
  </div>
</template>

<style scoped>
.app-layout { display: flex; height: 100%; overflow: hidden; }
.review-main { flex: 1; min-width: 0; overflow-y: auto; }
.review { max-width: 720px; margin: 0 auto; padding: 24px 20px 60px; }
.review-head h1 { margin: 0; font-size: 22px; }
.sub { margin: 4px 0 0; color: var(--text-secondary); }
.done-banner {
  margin: 12px 0 0; padding: 8px 12px; border-radius: var(--radius);
  background: var(--primary-soft); color: var(--primary);
}
.step { margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--border); }
.step h2 { margin: 0 0 10px; font-size: 16px; display: flex; align-items: center; gap: 8px; }
.num {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; border-radius: 50%;
  background: var(--primary); color: #fff; font-size: 12px;
}
.score { display: flex; align-items: baseline; gap: 10px; }
.score-value { font-size: 28px; font-weight: 700; color: var(--primary); }
.score-detail { color: var(--text-secondary); }
.colors { display: flex; gap: 14px; color: var(--text-secondary); }
.plain { margin: 6px 0 0; padding-left: 18px; }
.muted { color: var(--text-muted); font-size: 13px; }
.blocked { padding: 8px 0; border-bottom: 1px solid var(--border); }
.blocked-title { font-weight: 600; }
.reasons { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 6px; }
.chip {
  padding: 3px 10px; border: 1px solid var(--border); border-radius: 999px;
  background: transparent; color: var(--text); cursor: pointer; font: inherit; font-size: 13px;
}
.chip:hover { background: var(--bg-hover); }
.remedy { margin: 6px 0 0; color: var(--primary); }
.amnesty { margin-top: 12px; }
.levels { display: flex; flex-wrap: wrap; gap: 16px; margin: 8px 0; }
.level { display: flex; align-items: center; gap: 6px; cursor: pointer; }
.next-occ { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; padding: 6px 0; }
.next-when { width: 130px; text-transform: capitalize; }
.next-occ select { flex: 1; min-width: 180px; padding: 4px 6px; background: var(--bg); color: var(--text); border: 1px solid var(--border); border-radius: 6px; }
textarea {
  width: 100%; box-sizing: border-box; padding: 8px; margin-bottom: 10px;
  border: 1px solid var(--border); border-radius: var(--radius);
  background: var(--bg); color: var(--text); font: inherit;
}
@media (max-width: 640px) {
  .review { padding: 56px 12px 40px; }
  .next-when { width: auto; }
}
</style>
