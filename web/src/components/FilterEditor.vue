<script setup lang="ts">
import { ref, watch } from 'vue'
import type { FilterRule } from '@/types'

const props = defineProps<{ modelValue: FilterRule[] }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: FilterRule[]): void
}>()

type RuleOp = 'eq' | 'neq' | 'lt' | 'gt' | 'in' | 'is_null' | 'is_not_null'
type RuleField = 'priority' | 'status' | 'due' | 'tag'

interface SimpleRule { field: RuleField; op: RuleOp; value?: unknown }

// Flatten to a single AND group for simple UX (extend later for OR)
const rules = ref<SimpleRule[]>([])

watch(() => props.modelValue, (v) => {
  if (v.length && v[0].rules) {
    rules.value = v[0].rules as SimpleRule[]
  }
}, { immediate: true })

function emit_() {
  emit('update:modelValue', [{
    type: 'and',
    rules: rules.value,
  }])
}

function addRule() {
  rules.value.push({ field: 'priority', op: 'eq', value: 3 })
  emit_()
}

function removeRule(i: number) {
  rules.value.splice(i, 1)
  emit_()
}

const FIELDS: Array<{ value: RuleField; label: string }> = [
  { value: 'priority', label: 'Priorité' },
  { value: 'status', label: 'Statut' },
  { value: 'due', label: 'Échéance' },
  { value: 'tag', label: 'Tag' },
]

const OPS: Array<{ value: RuleOp; label: string }> = [
  { value: 'eq', label: '=' },
  { value: 'neq', label: '≠' },
  { value: 'lt', label: '<' },
  { value: 'gt', label: '>' },
  { value: 'is_null', label: 'est vide' },
  { value: 'is_not_null', label: "n'est pas vide" },
]

const PRIORITY_OPTS = [
  { v: 5, l: '🔴 Haute' }, { v: 3, l: '🟡 Moyenne' }, { v: 1, l: '🔵 Basse' }, { v: 0, l: '⬜ Aucune' },
]
const STATUS_OPTS = [
  { v: 0, l: 'En cours' }, { v: 2, l: 'Terminée' }, { v: -1, l: "Won't Do" },
]
const DUE_OPTS = [
  { v: 'today', l: "Aujourd'hui" }, { v: 'tomorrow', l: 'Demain' },
  { v: 'week', l: 'Cette semaine' }, { v: 'overdue', l: 'En retard' },
]
</script>

<template>
  <div class="filter-editor">
    <div class="filter-label">Toutes les conditions suivantes sont vraies (ET)</div>

    <div v-for="(rule, i) in rules" :key="i" class="rule-row">
      <select v-model="rule.field" class="rule-select" @change="emit_">
        <option v-for="f in FIELDS" :key="f.value" :value="f.value">{{ f.label }}</option>
      </select>

      <select v-model="rule.op" class="rule-select" @change="emit_">
        <option v-for="o in OPS" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>

      <template v-if="rule.op !== 'is_null' && rule.op !== 'is_not_null'">
        <select v-if="rule.field === 'priority'" v-model="rule.value" class="rule-select" @change="emit_">
          <option v-for="o in PRIORITY_OPTS" :key="o.v" :value="o.v">{{ o.l }}</option>
        </select>
        <select v-else-if="rule.field === 'status'" v-model="rule.value" class="rule-select" @change="emit_">
          <option v-for="o in STATUS_OPTS" :key="o.v" :value="o.v">{{ o.l }}</option>
        </select>
        <select v-else-if="rule.field === 'due'" v-model="rule.value" class="rule-select" @change="emit_">
          <option v-for="o in DUE_OPTS" :key="o.v" :value="o.v">{{ o.l }}</option>
        </select>
        <input v-else v-model="rule.value" class="rule-input" placeholder="valeur" @input="emit_" />
      </template>

      <button class="remove-rule" @click="removeRule(i)">✕</button>
    </div>

    <button class="add-rule-btn" @click="addRule">＋ Ajouter une condition</button>
  </div>
</template>

<style scoped>
.filter-editor { display: flex; flex-direction: column; gap: 8px; }
.filter-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.4px; }

.rule-row { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }

.rule-select, .rule-input {
  padding: 5px 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text);
  font-size: 12.5px;
  outline: none;
}
.rule-select:focus, .rule-input:focus { border-color: var(--primary); }
.rule-input { width: 100px; }

.remove-rule {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 12px;
  padding: 2px 4px;
}
.remove-rule:hover { color: var(--danger); }

.add-rule-btn {
  align-self: flex-start;
  font-size: 12px;
  padding: 4px 10px;
  border: 1px dashed var(--border);
  border-radius: 6px;
  background: none;
  color: var(--primary);
  cursor: pointer;
}
.add-rule-btn:hover { background: var(--bg-hover); }
</style>
