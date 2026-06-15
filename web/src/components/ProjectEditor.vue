<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Project, FilterRule } from '@/types'
import { useProjectStore } from '@/stores/projects'
import { useRouter, useRoute } from 'vue-router'
import FilterEditor from './FilterEditor.vue'

const props = defineProps<{ project: Project }>()
const emit = defineEmits<{ close: [] }>()

const projectStore = useProjectStore()
const router = useRouter()
const route = useRoute()

const name = ref(props.project.name)
const color = ref(props.project.color || '#4772fa')
const icon = ref(props.project.icon || '')
const isSmart = ref(props.project.is_smart ?? false)
const filterRules = ref<FilterRule[]>(props.project.filter_rules ?? [])

watch(() => props.project, (p) => {
  name.value = p.name
  color.value = p.color || '#4772fa'
  icon.value = p.icon || ''
  isSmart.value = p.is_smart ?? false
  filterRules.value = p.filter_rules ?? []
})

const COLORS = [
  '#4772fa', '#5b87ff', '#34c6a0', '#20c997', '#f06595',
  '#e03131', '#e8590c', '#f59f00', '#74b816', '#1971c2',
  '#6741d9', '#9c36b5', '#c2255c', '#0ca678', '#1098ad',
  '#2f9e44', '#e67700', '#d9480f', '#364fc7', '#495057',
]

const ICONS = ['📋', '🏠', '💼', '🎯', '📚', '🎮', '🏃', '🛒', '✈️', '💡',
               '🔧', '🌱', '❤️', '⭐', '🎵', '🎨', '📷', '🍔', '🏋️', '📝']

async function save() {
  await projectStore.update(props.project.id, {
    name: name.value.trim() || props.project.name,
    color: color.value,
    icon: icon.value,
    is_smart: isSmart.value,
    filter_rules: isSmart.value ? filterRules.value : [],
  })
  emit('close')
}

async function archive() {
  if (!confirm(`Archiver « ${props.project.name} » ?`)) return
  await projectStore.update(props.project.id, { archived: true })
  if (route.params.id === String(props.project.id)) router.push('/today')
  emit('close')
}

async function remove() {
  if (!confirm(`Supprimer définitivement « ${props.project.name} » et toutes ses tâches ?`)) return
  await projectStore.remove(props.project.id)
  if (route.params.id === String(props.project.id)) router.push('/today')
  emit('close')
}
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h3>Modifier la liste</h3>
        <button class="icon-btn" @click="emit('close')">✕</button>
      </div>

      <div class="modal-body">
        <!-- Nom -->
        <div class="field">
          <label class="field-label">Nom</label>
          <input v-model="name" class="field-input" @keydown.enter="save" />
        </div>

        <!-- Icône -->
        <div class="field">
          <label class="field-label">Icône</label>
          <div class="icon-grid">
            <button
              v-for="ic in ICONS"
              :key="ic"
              class="icon-opt"
              :class="{ selected: icon === ic }"
              @click="icon = icon === ic ? '' : ic"
            >{{ ic }}</button>
          </div>
        </div>

        <!-- Couleur -->
        <div class="field">
          <label class="field-label">Couleur</label>
          <div class="color-grid">
            <button
              v-for="c in COLORS"
              :key="c"
              class="color-swatch"
              :class="{ selected: color === c }"
              :style="`background: ${c}`"
              @click="color = c"
            />
          </div>
        </div>

        <!-- Smart list -->
        <div class="field">
          <label class="smart-toggle">
            <input type="checkbox" v-model="isSmart" />
            <span>🔍 Smart list (filtres automatiques)</span>
          </label>
          <FilterEditor v-if="isSmart" v-model="filterRules" style="margin-top:10px" />
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-ghost danger-text" @click="archive">Archiver</button>
        <button v-if="!project.is_inbox" class="btn btn-ghost danger-text" @click="remove">Supprimer</button>
        <div class="spacer" />
        <button class="btn btn-ghost" @click="emit('close')">Annuler</button>
        <button class="btn btn-primary" @click="save">Enregistrer</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.35);
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal {
  background: var(--bg);
  border-radius: 14px;
  width: 400px;
  max-width: 90vw;
  box-shadow: 0 20px 60px rgba(0,0,0,0.25);
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px 12px;
  border-bottom: 1px solid var(--border);
}
.modal-header h3 { margin: 0; font-size: 16px; font-weight: 600; }

.modal-body { padding: 16px 20px; display: flex; flex-direction: column; gap: 16px; }

.field { display: flex; flex-direction: column; gap: 8px; }
.field-label {
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  color: var(--text-muted);
}
.field-input {
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  background: var(--bg);
  color: var(--text);
}
.field-input:focus { border-color: var(--primary); }

.icon-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.icon-opt {
  width: 36px;
  height: 36px;
  font-size: 18px;
  border-radius: 8px;
  border: 2px solid transparent;
  background: var(--bg-hover);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.icon-opt:hover { border-color: var(--border); }
.icon-opt.selected { border-color: var(--primary); background: var(--primary-soft); }

.color-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.color-swatch {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 3px solid transparent;
  cursor: pointer;
  outline: none;
}
.color-swatch:hover { transform: scale(1.15); }
.color-swatch.selected { border-color: var(--text); }

.modal-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid var(--border);
}
.spacer { flex: 1; }
.danger-text { color: var(--danger); }

.smart-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13.5px;
  cursor: pointer;
}
</style>
