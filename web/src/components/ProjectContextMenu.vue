<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import type { Project } from '@/types'
import { useProjectStore } from '@/stores/projects'

const props = defineProps<{
  project: Project
  x: number
  y: number
}>()
const emit = defineEmits<{ close: []; edit: [] }>()

const projectStore = useProjectStore()
const router = useRouter()
const menuRef = ref<HTMLDivElement>()
const editingName = ref(false)
const nameInput = ref(props.project.name)
const showMove = ref(false)

const COLORS = ['#4772fa','#f55','#fa0','#4af','#8f4','#c4f','#f48','#aaa']
const ICONS  = ['📋','🏠','💼','📚','🎯','💡','🛒','🎮','✈️','❤️']
const BG_COLORS = ['','#fef9c3','#fce7f3','#e0f2fe','#d1fae5','#ede9fe','#fee2e2','#f1f5f9','#1e293b']

function close() { emit('close') }

async function rename() {
  const name = nameInput.value.trim()
  if (!name || name === props.project.name) { editingName.value = false; return }
  await projectStore.update(props.project.id, { name })
  editingName.value = false
  close()
}

async function setColor(color: string) {
  await projectStore.update(props.project.id, { color })
  close()
}

async function setBgColor(bg: string) {
  await projectStore.update(props.project.id, { bg_color: bg })
  close()
}

async function setIcon(icon: string) {
  await projectStore.update(props.project.id, { icon })
  close()
}

async function setViewMode(mode: Project['view_mode']) {
  await projectStore.update(props.project.id, { view_mode: mode })
  if (mode === 'kanban') router.push(`/project/${props.project.id}/kanban`)
  else if (mode === 'timeline') router.push('/timeline')
  close()
}

async function archive() {
  await projectStore.update(props.project.id, { archived: !props.project.archived })
  if (!props.project.archived) router.push('/today')
  close()
}

async function moveTo(groupId: number | null) {
  await projectStore.update(props.project.id, { group: groupId })
  close()
}

async function remove() {
  if (!confirm(`Supprimer la liste « ${props.project.name} » ?`)) return
  await projectStore.remove(props.project.id)
  router.push('/today')
  close()
}

function onClickOutside(e: MouseEvent) {
  if (menuRef.value && !menuRef.value.contains(e.target as Node)) close()
}

onMounted(() => document.addEventListener('mousedown', onClickOutside))
onUnmounted(() => document.removeEventListener('mousedown', onClickOutside))
</script>

<template>
  <div
    ref="menuRef"
    class="menu project-context-menu"
    :style="`left: ${x}px; top: ${y}px`"
    @contextmenu.prevent
  >
    <!-- Renommer inline -->
    <div v-if="editingName" class="rename-row">
      <input
        v-model="nameInput"
        class="rename-input"
        @keydown.enter="rename"
        @keydown.escape="editingName = false"
        autofocus
      />
      <button class="rename-ok" @click="rename">✓</button>
    </div>
    <template v-else>
      <button class="menu-item" @click="editingName = true; nameInput = project.name">
        <span class="mi-icon">✏️</span> Renommer
      </button>

      <button class="menu-item" @click="emit('edit'); close()">
        <span class="mi-icon">⚙️</span> Modifier (icône, smart list…)
      </button>

      <!-- Couleur -->
      <div class="color-row">
        <button
          v-for="c in COLORS" :key="c"
          class="color-dot"
          :class="{ selected: project.color === c }"
          :style="`background:${c}`"
          @click="setColor(c)"
        />
      </div>

      <!-- Icônes -->
      <div class="icon-row">
        <button
          v-for="ic in ICONS" :key="ic"
          class="icon-btn-sm"
          :class="{ selected: project.icon === ic }"
          @click="setIcon(ic)"
        >{{ ic }}</button>
      </div>

      <!-- Fond -->
      <div class="menu-label">Fond de liste</div>
      <div class="color-row">
        <button
          v-for="bg in BG_COLORS" :key="bg || 'none'"
          class="color-dot"
          :class="{ selected: project.bg_color === bg }"
          :style="bg ? `background:${bg}` : 'background:var(--bg-card);border:1px solid var(--border)'"
          :title="bg ? bg : 'Aucun'"
          @click="setBgColor(bg)"
        />
      </div>

      <div class="menu-sep" />

      <!-- Vue -->
      <div class="menu-label">Vue par défaut</div>
      <div class="view-row">
        <button
          v-for="v in ['list','kanban','timeline'] as const" :key="v"
          class="view-pill"
          :class="{ active: project.view_mode === v }"
          @click="setViewMode(v)"
        >{{ v === 'list' ? '☰ Liste' : v === 'kanban' ? '⊞ Kanban' : '📊 Timeline' }}</button>
      </div>

      <div class="menu-sep" />

      <!-- Déplacer dans un dossier -->
      <div class="menu-item submenu-trigger"
           @mouseenter="showMove = true" @mouseleave="showMove = false">
        <span class="mi-icon">📁</span> Déplacer dans un dossier
        <span class="submenu-arrow">▶</span>
        <div v-if="showMove" class="menu submenu">
          <button class="menu-item" @click="moveTo(null)">
            <span class="mi-icon">✕</span> Aucun dossier
            <span v-if="!project.group" class="mi-check">✓</span>
          </button>
          <button
            v-for="g in projectStore.groups" :key="g.id"
            class="menu-item"
            :class="{ active: project.group === g.id }"
            @click="moveTo(g.id)"
          >
            <span class="mi-icon">📁</span> {{ g.name }}
            <span v-if="project.group === g.id" class="mi-check">✓</span>
          </button>
        </div>
      </div>

      <!-- Archiver -->
      <button class="menu-item" @click="archive">
        <span class="mi-icon">{{ project.archived ? '📤' : '📦' }}</span>
        {{ project.archived ? 'Désarchiver' : 'Archiver' }}
      </button>

      <div class="menu-sep" />

      <!-- Supprimer -->
      <button v-if="!project.is_inbox" class="menu-item danger" @click="remove">
        <span class="mi-icon">🗑</span> Supprimer la liste
      </button>
    </template>
  </div>
</template>

<style scoped>
.project-context-menu {
  position: fixed;
  z-index: 2000;
  min-width: 220px;
}

.submenu-trigger {
  position: relative;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 10px;
  border-radius: 6px;
  color: var(--text);
  background: none;
  border: none;
  text-align: left;
  font-size: 13px;
}
.submenu-trigger:hover { background: var(--bg-hover); }
.submenu-arrow { margin-left: auto; font-size: 10px; color: var(--text-muted); }
.submenu {
  position: absolute;
  left: 100%;
  top: -5px;
  z-index: 2001;
  min-width: 180px;
}

.mi-icon { width: 18px; text-align: center; flex-shrink: 0; }
.mi-check { margin-left: auto; color: var(--accent); font-size: 12px; }

.rename-row {
  display: flex;
  gap: 6px;
  padding: 6px 10px;
}
.rename-input {
  flex: 1;
  padding: 4px 8px;
  border: 1px solid var(--accent);
  border-radius: 4px;
  background: var(--bg-card);
  color: var(--text);
  font-size: 13px;
}
.rename-ok {
  padding: 4px 8px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.color-row {
  display: flex;
  gap: 6px;
  padding: 6px 10px;
  flex-wrap: wrap;
}
.color-dot {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
}
.color-dot.selected { border-color: var(--text); }

.icon-row {
  display: flex;
  gap: 4px;
  padding: 4px 10px;
  flex-wrap: wrap;
}
.icon-btn-sm {
  width: 24px;
  height: 24px;
  font-size: 14px;
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: pointer;
  background: none;
}
.icon-btn-sm.selected { border-color: var(--accent); background: var(--bg-hover); }
.icon-btn-sm:hover { background: var(--bg-hover); }

.menu-label {
  padding: 4px 10px 2px;
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.view-row {
  display: flex;
  gap: 4px;
  padding: 4px 10px 8px;
}
.view-pill {
  flex: 1;
  padding: 4px 6px;
  font-size: 11px;
  border: 1px solid var(--border);
  border-radius: 4px;
  cursor: pointer;
  background: var(--bg-card);
  color: var(--text);
  white-space: nowrap;
}
.view-pill.active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

.menu-item.active { font-weight: 500; }
</style>
