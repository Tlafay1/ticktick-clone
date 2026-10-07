<script setup lang="ts">
// Réglages de la méthode : créneaux (rendez-vous fixes), revue, jokers, pause.
// Le reste (contrat de 10 min, relance à 15 min…) est volontairement fixe.
import { computed, onMounted, ref } from 'vue'
import { methodApi, slotsApi } from '@/api'
import { WEEKDAYS, hhmm } from '@/lib/method'
import { useProjectStore } from '@/stores/projects'
import type { MethodConfig, Slot } from '@/types'

const projectStore = useProjectStore()
const config = ref<MethodConfig | null>(null)
const slots = ref<Slot[]>([])
const draft = ref<Partial<Slot>>({ weekday: 0, start_time: '20:30', duration_minutes: 25, project: null, kind: 'work' })

onMounted(async () => {
  ;[config.value, slots.value] = await Promise.all([methodApi.config(), slotsApi.list()])
})

const projects = computed(() =>
  projectStore.projects.filter(p => !p.archived && !p.is_smart)
    .sort((a, b) => Number(b.objective === 'active') - Number(a.objective === 'active')))

async function saveConfig(patch: Partial<MethodConfig>) {
  config.value = await methodApi.updateConfig(patch)
}

async function addSlot() {
  const slot = await slotsApi.create(draft.value)
  slots.value = [...slots.value, slot].sort((a, b) =>
    a.weekday - b.weekday || a.start_time.localeCompare(b.start_time))
}

async function updateSlot(slot: Slot, patch: Partial<Slot>) {
  const updated = await slotsApi.update(slot.id, patch)
  slots.value = slots.value.map(s => (s.id === updated.id ? updated : s))
}

async function removeSlot(slot: Slot) {
  if (!confirm(`Supprimer le créneau du ${WEEKDAYS[slot.weekday].toLowerCase()} ${hhmm(slot.start_time)} ? L'historique est conservé.`)) return
  await slotsApi.remove(slot.id)
  slots.value = slots.value.filter(s => s.id !== slot.id)
}

function value(e: Event) {
  return (e.target as HTMLInputElement | HTMLSelectElement).value
}
</script>

<template>
  <section class="settings-section">
    <h2 class="section-title">Méthode</h2>
    <p class="section-hint">
      Des rendez-vous fixes, peu nombreux : à l'heure dite, la prochaine action est prête
      et 10 minutes suffisent. Les créneaux « tampon » accueillent automatiquement les ratés.
    </p>

    <div class="slot-list">
      <div v-for="slot in slots" :key="slot.id" class="slot-row">
        <select :value="slot.weekday" @change="updateSlot(slot, { weekday: Number(value($event)) })">
          <option v-for="(d, i) in WEEKDAYS" :key="i" :value="i">{{ d }}</option>
        </select>
        <input type="time" :value="hhmm(slot.start_time)" @change="updateSlot(slot, { start_time: value($event) })" />
        <input
          type="number" min="5" max="240" class="duration" :value="slot.duration_minutes"
          @change="updateSlot(slot, { duration_minutes: Number(value($event)) })"
        /> min
        <select :value="slot.kind" @change="updateSlot(slot, { kind: value($event) as Slot['kind'] })">
          <option value="work">Travail</option>
          <option value="buffer">Tampon</option>
        </select>
        <select
          v-if="slot.kind === 'work'" :value="slot.project ?? ''"
          @change="updateSlot(slot, { project: value($event) ? Number(value($event)) : null })"
        >
          <option value="">Objectif auto</option>
          <option v-for="p in projects" :key="p.id" :value="p.id">
            {{ p.objective === 'active' ? '🎯 ' : '' }}{{ p.name }}
          </option>
        </select>
        <button class="icon-btn" title="Supprimer" @click="removeSlot(slot)">✕</button>
      </div>
      <p v-if="!slots.length" class="section-hint">Aucun créneau pour l'instant.</p>
    </div>

    <div class="slot-row add-row">
      <select v-model.number="draft.weekday">
        <option v-for="(d, i) in WEEKDAYS" :key="i" :value="i">{{ d }}</option>
      </select>
      <input v-model="draft.start_time" type="time" />
      <input v-model.number="draft.duration_minutes" type="number" min="5" max="240" class="duration" /> min
      <select v-model="draft.kind">
        <option value="work">Travail</option>
        <option value="buffer">Tampon</option>
      </select>
      <button class="btn btn-primary" @click="addSlot">Ajouter</button>
    </div>

    <template v-if="config">
      <div class="setting-row">
        <label class="setting-label">🗓️ Revue de la semaine</label>
        <span>
          <select :value="config.review_weekday" @change="saveConfig({ review_weekday: Number(value($event)) })">
            <option v-for="(d, i) in WEEKDAYS" :key="i" :value="i">{{ d }}</option>
          </select>
          <input type="time" :value="hhmm(config.review_time)" @change="saveConfig({ review_time: value($event) })" />
        </span>
      </div>
      <div class="setting-row">
        <label class="setting-label">🃏 Jokers par mois</label>
        <input type="number" min="0" max="10" class="duration" :value="config.jokers_per_month"
               @change="saveConfig({ jokers_per_month: Number(value($event)) })" />
      </div>
      <div class="setting-row">
        <label class="setting-label">📋 Tâches max « Aujourd'hui »</label>
        <input type="number" min="1" max="10" class="duration" :value="config.today_limit"
               @change="saveConfig({ today_limit: Number(value($event)) })" />
      </div>
      <div class="setting-row">
        <label class="setting-label">⏸ Pause jusqu'au (maladie, gros événement)</label>
        <span>
          <input type="date" :value="config.pause_until ?? ''"
                 @change="saveConfig({ pause_until: value($event) || null })" />
          <button v-if="config.pause_until" class="btn btn-ghost" @click="saveConfig({ pause_until: null })">Reprendre</button>
        </span>
      </div>
      <div class="setting-row">
        <label class="setting-label">📈 Niveau actuel</label>
        <span>{{ config.level }} <span class="section-hint">(se change en revue)</span></span>
      </div>
    </template>
  </section>
</template>

<style scoped>
.settings-section { margin-bottom: 36px; }
.section-title {
  font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;
  color: var(--text-muted); margin: 0 0 16px;
}
.section-hint { font-size: 13px; color: var(--text-secondary); margin: -8px 0 12px; }
.slot-list { display: flex; flex-direction: column; }
.slot-row {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
  padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 14px;
}
.add-row { border-bottom: none; }
.setting-row {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px;
  padding: 12px 0; border-bottom: 1px solid var(--border);
}
.setting-label { font-size: 14px; color: var(--text); }
select, input {
  padding: 5px 8px; border: 1px solid var(--border); border-radius: 6px;
  background: var(--bg); color: var(--text); font: inherit; font-size: 13px;
}
.duration { width: 64px; }
</style>
