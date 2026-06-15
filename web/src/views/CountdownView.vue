<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import Sidebar from '@/components/Sidebar.vue'
import { countdownApi } from '@/api'
import type { Countdown } from '@/types'
import { renderMarkdown } from '@/lib/markdown'

const countdowns = ref<Countdown[]>([])
const loading = ref(true)
const showCreate = ref(false)

const draft = ref({ title: '', target_date: '', description: '', pinned: false })

onMounted(async () => {
  try {
    countdowns.value = await countdownApi.list()
  } finally {
    loading.value = false
  }
})

async function create() {
  if (!draft.value.title.trim() || !draft.value.target_date) return
  const c = await countdownApi.create({ ...draft.value })
  countdowns.value.unshift(c)
  showCreate.value = false
  draft.value = { title: '', target_date: '', description: '', pinned: false }
}

async function togglePin(c: Countdown) {
  const updated = await countdownApi.update(c.id, { pinned: !c.pinned })
  const idx = countdowns.value.findIndex(x => x.id === c.id)
  if (idx >= 0) countdowns.value[idx] = updated
}

async function remove(c: Countdown) {
  if (!confirm(`Supprimer « ${c.title} » ?`)) return
  await countdownApi.remove(c.id)
  countdowns.value = countdowns.value.filter(x => x.id !== c.id)
}

function daysLabel(n: number) {
  if (n < 0) return `Il y a ${Math.abs(n)} j`
  if (n === 0) return "Aujourd'hui !"
  if (n === 1) return 'Demain'
  return `Dans ${n} j`
}

function daysTone(n: number) {
  if (n < 0) return 'past'
  if (n <= 7) return 'soon'
  if (n <= 30) return 'near'
  return 'future'
}

const sorted = computed(() => [
  ...countdowns.value.filter(c => c.pinned),
  ...countdowns.value.filter(c => !c.pinned),
])
</script>

<template>
  <div class="app-layout">
    <Sidebar />

    <main class="countdown-main">
      <div class="countdown-header">
        <h1>Compte à rebours</h1>
        <button class="btn btn-primary" @click="showCreate = !showCreate">＋ Nouveau</button>
      </div>

      <!-- Formulaire -->
      <div v-if="showCreate" class="create-form card">
        <input v-model="draft.title" placeholder="Titre (ex: Vacances, Anniversaire…)" class="field-input" @keydown.enter="create" />
        <div class="form-row">
          <div class="form-group">
            <label class="field-label">Date cible</label>
            <input v-model="draft.target_date" type="date" class="field-input" />
          </div>
          <label class="pin-toggle">
            <input type="checkbox" v-model="draft.pinned" />
            📌 Épingler
          </label>
        </div>
        <textarea v-model="draft.description" placeholder="Note (markdown supporté)…" class="desc-input" rows="3" />
        <div class="form-actions">
          <button class="btn btn-ghost" @click="showCreate = false">Annuler</button>
          <button class="btn btn-primary" :disabled="!draft.title.trim() || !draft.target_date" @click="create">Créer</button>
        </div>
      </div>

      <div v-if="loading" class="loading-msg">Chargement…</div>

      <!-- Grille des comptes à rebours -->
      <div v-else class="countdown-grid">
        <div
          v-for="c in sorted"
          :key="c.id"
          class="countdown-card"
          :class="`tone-${daysTone(c.days_remaining)}`"
        >
          <div class="card-top">
            <span v-if="c.pinned" class="pin-icon">📌</span>
            <span class="card-title">{{ c.title }}</span>
            <div class="card-actions">
              <button class="icon-btn" :title="c.pinned ? 'Désépingler' : 'Épingler'" @click="togglePin(c)">{{ c.pinned ? '📌' : '📍' }}</button>
              <button class="icon-btn" title="Supprimer" @click="remove(c)">🗑</button>
            </div>
          </div>

          <div class="days-display">
            <span class="days-num">{{ Math.abs(c.days_remaining) }}</span>
            <span class="days-unit">{{ c.days_remaining < 0 ? 'jours passés' : 'jours restants' }}</span>
          </div>

          <div class="days-label">{{ daysLabel(c.days_remaining) }}</div>
          <div class="target-date">📅 {{ new Date(c.target_date + 'T00:00:00').toLocaleDateString('fr-FR', { day: '2-digit', month: 'long', year: 'numeric' }) }}</div>

          <div v-if="c.description" class="card-desc md-body" v-html="renderMarkdown(c.description)" />
        </div>

        <div v-if="!loading && countdowns.length === 0" class="empty-countdown">
          <div class="empty-icon">⏳</div>
          <p>Aucun compte à rebours. Ajoutez une date importante !</p>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.app-layout { display: flex; height: 100%; overflow: hidden; }

.countdown-main { flex: 1; overflow-y: auto; padding: 28px 32px; }

.countdown-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}
.countdown-header h1 { margin: 0; font-size: 24px; font-weight: 700; }

.card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 20px;
  margin-bottom: 20px;
}

/* Formulaire */
.create-form { display: flex; flex-direction: column; gap: 12px; max-width: 500px; }
.form-row { display: flex; align-items: flex-end; gap: 16px; flex-wrap: wrap; }
.form-group { display: flex; flex-direction: column; gap: 6px; }
.field-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.4px; color: var(--text-muted); }
.field-input {
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  background: var(--bg);
  color: var(--text);
  outline: none;
}
.field-input:focus { border-color: var(--primary); }
.desc-input {
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 13px;
  background: var(--bg);
  color: var(--text);
  resize: vertical;
  outline: none;
  font-family: monospace;
}
.pin-toggle { display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer; }
.form-actions { display: flex; justify-content: flex-end; gap: 8px; }

/* Grille */
.countdown-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}

.countdown-card {
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 18px;
  background: var(--bg);
  position: relative;
}

.countdown-card.tone-soon { border-top: 3px solid var(--prio-high); }
.countdown-card.tone-near { border-top: 3px solid var(--prio-medium); }
.countdown-card.tone-future { border-top: 3px solid var(--primary); }
.countdown-card.tone-past { border-top: 3px solid var(--text-muted); opacity: 0.75; }

.card-top { display: flex; align-items: center; gap: 6px; margin-bottom: 12px; }
.pin-icon { font-size: 12px; }
.card-title { flex: 1; font-size: 15px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-actions { display: flex; gap: 2px; opacity: 0; }
.countdown-card:hover .card-actions { opacity: 1; }

.days-display { display: flex; align-items: baseline; gap: 6px; margin-bottom: 4px; }
.days-num { font-size: 48px; font-weight: 700; line-height: 1; }
.days-unit { font-size: 13px; color: var(--text-secondary); }

.days-label { font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: 6px; }
.target-date { font-size: 12px; color: var(--text-muted); margin-bottom: 10px; }

.card-desc { font-size: 13px; color: var(--text-secondary); margin-top: 8px; border-top: 1px solid var(--border); padding-top: 8px; }

.empty-countdown { grid-column: 1/-1; text-align: center; padding: 60px 20px; color: var(--text-muted); }
.empty-icon { font-size: 40px; margin-bottom: 12px; }
.loading-msg { text-align: center; padding: 60px; color: var(--text-muted); }
</style>
