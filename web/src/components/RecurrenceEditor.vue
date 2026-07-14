<script setup lang="ts">
/**
 * Éditeur de récurrence rrule (RFC 5545, sous-ensemble TickTick).
 * Produit une chaîne RRULE:FREQ=... ou '' pour supprimer.
 */
import { ref, computed, watch } from 'vue'
import { buildRRule, parseRRule, RRULE_PRESETS, isRDates, parseRDates, buildRDates, type RRuleFreq } from '@/lib/rrule'

const props = defineProps<{ modelValue: string | null; repeatFrom: 'due' | 'completion' }>()
const emit = defineEmits<{
  'update:modelValue': [string]
  'update:repeatFrom': ['due' | 'completion']
}>()

const DAYS = [
  { key: 'MO', label: 'L' }, { key: 'TU', label: 'M' }, { key: 'WE', label: 'M' },
  { key: 'TH', label: 'J' }, { key: 'FR', label: 'V' }, { key: 'SA', label: 'S' },
  { key: 'SU', label: 'D' },
]

const mode = ref<'none' | 'preset' | 'custom' | 'dates'>('none')
const selectedPreset = ref('')
const freq = ref<RRuleFreq>('DAILY')
const interval = ref(1)
const byDay = ref<string[]>([])
const count = ref<number | null>(null)
const until = ref('')
// Dates spécifiques (RDATE)
const specificDates = ref<string[]>([])
const newDate = ref('')

// Parse le rrule entrant
watch(() => props.modelValue, (v) => {
  if (!v) { mode.value = 'none'; return }
  const preset = RRULE_PRESETS.find(p => p.rrule === v)
  if (preset) {
    mode.value = 'preset'
    selectedPreset.value = v
    return
  }
  if (isRDates(v)) {
    mode.value = 'dates'
    specificDates.value = parseRDates(v)
    return
  }
  mode.value = 'custom'
  const parsed = parseRRule(v)
  if (parsed) {
    freq.value = parsed.freq
    interval.value = parsed.interval ?? 1
    byDay.value = parsed.byDay ?? []
    count.value = parsed.count ?? null
    until.value = parsed.until ?? ''
  }
}, { immediate: true })

const customRRule = computed(() =>
  buildRRule({ freq: freq.value, interval: interval.value, byDay: byDay.value, count: count.value, until: until.value })
)

function apply() {
  if (mode.value === 'none') emit('update:modelValue', '')
  else if (mode.value === 'preset') emit('update:modelValue', selectedPreset.value)
  else if (mode.value === 'dates') emit('update:modelValue', buildRDates(specificDates.value))
  else emit('update:modelValue', customRRule.value)
}

function addDate() {
  if (!newDate.value || specificDates.value.includes(newDate.value)) return
  specificDates.value = [...specificDates.value, newDate.value].sort()
  newDate.value = ''
  apply()
}

function removeDate(d: string) {
  specificDates.value = specificDates.value.filter(x => x !== d)
  apply()
}

function toggleDay(d: string) {
  if (byDay.value.includes(d)) byDay.value = byDay.value.filter(x => x !== d)
  else byDay.value = [...byDay.value, d]
}
</script>

<template>
  <div class="recurrence-editor">
    <!-- Aucune récurrence -->
    <div class="rec-mode-row">
      <label class="rec-radio">
        <input type="radio" v-model="mode" value="none" @change="apply" />
        Jamais
      </label>
      <label class="rec-radio">
        <input type="radio" v-model="mode" value="preset" />
        Preset
      </label>
      <label class="rec-radio">
        <input type="radio" v-model="mode" value="custom" />
        Personnalisé
      </label>
      <label class="rec-radio">
        <input type="radio" v-model="mode" value="dates" />
        Dates spécifiques
      </label>
    </div>

    <!-- Presets -->
    <div v-if="mode === 'preset'" class="preset-list">
      <button
        v-for="p in RRULE_PRESETS"
        :key="p.rrule"
        class="preset-btn"
        :class="{ active: selectedPreset === p.rrule }"
        @click="selectedPreset = p.rrule; apply()"
      >{{ p.label }}</button>
    </div>

    <!-- Custom -->
    <div v-if="mode === 'custom'" class="custom-form">
      <div class="custom-row">
        <label>Répéter tous les</label>
        <input v-model.number="interval" type="number" min="1" class="num-input" @change="apply" />
        <select v-model="freq" class="freq-select" @change="apply">
          <option value="DAILY">jours</option>
          <option value="WEEKLY">semaines</option>
          <option value="MONTHLY">mois</option>
          <option value="YEARLY">ans</option>
        </select>
      </div>

      <div v-if="freq === 'WEEKLY'" class="days-row">
        <button
          v-for="d in DAYS"
          :key="d.key"
          class="day-btn"
          :class="{ active: byDay.includes(d.key) }"
          @click="toggleDay(d.key); apply()"
        >{{ d.label }}</button>
      </div>

      <div class="custom-row">
        <label>Fin après</label>
        <input v-model.number="count" type="number" min="1" placeholder="∞" class="num-input" @change="apply" />
        <span>occurrences ou le</span>
        <input v-model="until" type="date" class="until-input" @change="apply" />
      </div>
    </div>

    <!-- Dates spécifiques (RDATE) : la tâche avance de date en date -->
    <div v-if="mode === 'dates'" class="dates-form">
      <div class="custom-row">
        <input v-model="newDate" type="date" class="until-input" @keydown.enter="addDate" />
        <button class="btn btn-ghost add-date-btn" :disabled="!newDate" @click="addDate">＋ Ajouter</button>
      </div>
      <div v-if="specificDates.length" class="date-chips">
        <span v-for="d in specificDates" :key="d" class="date-chip">
          {{ new Date(`${d}T00:00:00`).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' }) }}
          <button class="chip-x" @click="removeDate(d)">✕</button>
        </span>
      </div>
      <div v-else class="dates-hint">Ajoutez les dates auxquelles la tâche doit se répéter.</div>
    </div>

    <!-- repeat_from -->
    <div v-if="mode !== 'none'" class="repeat-from-row">
      <label class="field-sublabel">Basé sur</label>
      <label class="rec-radio">
        <input type="radio" :checked="repeatFrom === 'due'" @change="emit('update:repeatFrom', 'due')" />
        La date d'échéance
      </label>
      <label class="rec-radio">
        <input type="radio" :checked="repeatFrom === 'completion'" @change="emit('update:repeatFrom', 'completion')" />
        La complétion
      </label>
    </div>

    <div v-if="mode !== 'none'" class="rrule-preview">{{ mode === 'preset' ? selectedPreset : mode === 'dates' ? buildRDates(specificDates) : customRRule }}</div>
  </div>
</template>

<style scoped>
.recurrence-editor { display: flex; flex-direction: column; gap: 10px; }

.rec-mode-row { display: flex; gap: 16px; }
.rec-radio { display: flex; align-items: center; gap: 5px; font-size: 13px; cursor: pointer; }

.preset-list { display: flex; flex-wrap: wrap; gap: 6px; }
.preset-btn {
  padding: 5px 12px;
  border-radius: 16px;
  border: 1px solid var(--border);
  font-size: 12.5px;
  cursor: pointer;
  background: none;
  color: var(--text-secondary);
}
.preset-btn:hover { border-color: var(--primary); color: var(--primary); }
.preset-btn.active { background: var(--primary); color: #fff; border-color: var(--primary); }

.custom-form { display: flex; flex-direction: column; gap: 8px; }
.custom-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 13px; }
.num-input { width: 56px; padding: 4px 6px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); text-align: center; }
.freq-select { padding: 4px 6px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); }
.until-input { padding: 4px 6px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); }

.days-row { display: flex; gap: 4px; }
.day-btn { width: 28px; height: 28px; border-radius: 50%; border: 1px solid var(--border); font-size: 12px; cursor: pointer; background: none; color: var(--text-secondary); }
.day-btn:hover { border-color: var(--primary); }
.day-btn.active { background: var(--primary); color: #fff; border-color: var(--primary); }

.dates-form { display: flex; flex-direction: column; gap: 8px; }
.add-date-btn { font-size: 12.5px; }
.date-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.date-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: 12px;
  background: var(--primary-soft);
  color: var(--primary);
  font-size: 12px;
}
.chip-x { border: none; background: none; color: inherit; cursor: pointer; font-size: 10px; padding: 0; }
.dates-hint { font-size: 12px; color: var(--text-muted); }

.repeat-from-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.field-sublabel { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.4px; }

.rrule-preview {
  font-size: 11px;
  color: var(--text-muted);
  font-family: monospace;
  background: var(--bg-hover);
  padding: 4px 8px;
  border-radius: 6px;
  word-break: break-all;
}
</style>
