<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Reminder } from '@/types'
import { remindersApi } from '@/api'

const props = defineProps<{ taskId: number }>()

const reminders = ref<Reminder[]>([])
const loading = ref(false)

watch(() => props.taskId, async (id) => {
  if (!id) return
  loading.value = true
  try {
    reminders.value = await remindersApi.list(id)
  } finally {
    loading.value = false
  }
}, { immediate: true })

const RELATIVE_PRESETS = [
  { label: 'À l\'heure exacte', value: 0 },
  { label: '5 min avant',       value: 5 },
  { label: '15 min avant',      value: 15 },
  { label: '30 min avant',      value: 30 },
  { label: '1 h avant',         value: 60 },
  { label: '1 jour avant',      value: 1440 },
]

const newType = ref<'relative' | 'absolute'>('relative')
const newMinutes = ref(0)
const newAt = ref('')
const newAnnoying = ref(false)

async function add() {
  if (reminders.value.length >= 5) return
  const data: Partial<Reminder> = {
    task: props.taskId,
    trigger_type: newType.value,
    annoying: newAnnoying.value,
    minutes_before: newType.value === 'relative' ? newMinutes.value : null,
    trigger_at: newType.value === 'absolute' ? (newAt.value ? new Date(newAt.value).toISOString() : null) : null,
  }
  const r = await remindersApi.create(data)
  reminders.value.push(r)
  newAt.value = ''
}

async function remove(r: Reminder) {
  await remindersApi.remove(r.id)
  reminders.value = reminders.value.filter(x => x.id !== r.id)
}

function describeReminder(r: Reminder) {
  if (r.trigger_type === 'relative') {
    const preset = RELATIVE_PRESETS.find(p => p.value === r.minutes_before)
    if (preset) return preset.label
    if (r.minutes_before === 0) return 'À l\'heure exacte'
    if ((r.minutes_before ?? 0) >= 1440) return `${Math.round((r.minutes_before ?? 0) / 1440)} j avant`
    if ((r.minutes_before ?? 0) >= 60) return `${Math.round((r.minutes_before ?? 0) / 60)} h avant`
    return `${r.minutes_before} min avant`
  }
  return r.trigger_at ? new Date(r.trigger_at).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '—'
}
</script>

<template>
  <div class="reminder-editor">
    <!-- Liste des rappels -->
    <div v-if="loading" class="loading-hint">Chargement…</div>
    <div v-for="r in reminders" :key="r.id" class="reminder-row">
      <span class="reminder-icon">{{ r.annoying ? '🔔🔴' : '🔔' }}</span>
      <span class="reminder-desc">{{ describeReminder(r) }}</span>
      <button class="icon-btn remove-btn" @click="remove(r)">✕</button>
    </div>
    <div v-if="!loading && reminders.length === 0" class="no-reminder">Aucun rappel</div>

    <!-- Ajout -->
    <div v-if="reminders.length < 5" class="add-form">
      <div class="add-type">
        <label class="rec-radio">
          <input type="radio" v-model="newType" value="relative" /> Relatif
        </label>
        <label class="rec-radio">
          <input type="radio" v-model="newType" value="absolute" /> Absolu
        </label>
        <label class="rec-radio annoying-toggle">
          <input type="checkbox" v-model="newAnnoying" /> 🔴 Persistent
        </label>
      </div>

      <div v-if="newType === 'relative'" class="add-row">
        <select v-model.number="newMinutes" class="freq-select">
          <option v-for="p in RELATIVE_PRESETS" :key="p.value" :value="p.value">{{ p.label }}</option>
        </select>
      </div>
      <div v-else class="add-row">
        <input v-model="newAt" type="datetime-local" class="until-input" />
      </div>

      <button class="btn btn-ghost add-btn" @click="add">＋ Ajouter</button>
    </div>
    <div v-else class="limit-hint">Maximum 5 rappels atteint</div>
  </div>
</template>

<style scoped>
.reminder-editor { display: flex; flex-direction: column; gap: 6px; }

.reminder-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 4px;
  border-radius: 6px;
}
.reminder-row:hover { background: var(--bg-hover); }
.reminder-icon { font-size: 14px; }
.reminder-desc { flex: 1; font-size: 13px; }
.remove-btn { opacity: 0; }
.reminder-row:hover .remove-btn { opacity: 1; }

.no-reminder, .loading-hint { font-size: 12.5px; color: var(--text-muted); }

.add-form { display: flex; flex-direction: column; gap: 6px; padding-top: 6px; border-top: 1px solid var(--border); }
.add-type { display: flex; gap: 12px; flex-wrap: wrap; }
.rec-radio { display: flex; align-items: center; gap: 5px; font-size: 12.5px; cursor: pointer; }
.annoying-toggle { margin-left: auto; }
.add-row { display: flex; gap: 8px; }
.freq-select, .until-input {
  padding: 4px 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text);
  font-size: 13px;
  flex: 1;
}
.add-btn { font-size: 12.5px; padding: 4px 10px; }
.limit-hint { font-size: 12px; color: var(--text-muted); }
</style>
