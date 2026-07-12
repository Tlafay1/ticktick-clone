<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import type { Task } from '@/types'
import { useTaskStore } from '@/stores/tasks'
import { useProjectStore } from '@/stores/projects'
import { useTagStore } from '@/stores/tags'
import { addDays, startOfDay, nextMonday, nextSaturday } from 'date-fns'
import Icon from './Icon.vue'

const props = defineProps<{ task: Task; x: number; y: number }>()
const emit = defineEmits<{ close: [] }>()

const taskStore = useTaskStore()
const projectStore = useProjectStore()
const tagStore = useTagStore()
const router = useRouter()

// Rangée Date (façon TickTick) : icônes d'accès rapide.
const DATE_OPTIONS = [
  { label: "Aujourd'hui",       icon: 'sun',           fn: () => startOfDay(new Date()) },
  { label: 'Demain',            icon: 'sunrise',       fn: () => addDays(startOfDay(new Date()), 1) },
  { label: 'Week-end prochain', icon: 'calendar',      fn: () => nextSaturday(startOfDay(new Date())) },
  { label: 'Semaine prochaine', icon: 'calendar-days', fn: () => nextMonday(startOfDay(new Date())) },
]

// Rangée Priorité : 4 drapeaux (haute, moyenne, basse, aucune).
const PRIORITIES = [
  { label: 'Haute',   value: 5, color: 'var(--prio-high)' },
  { label: 'Moyenne', value: 3, color: 'var(--prio-medium)' },
  { label: 'Basse',   value: 1, color: 'var(--prio-low)' },
  { label: 'Aucune',  value: 0, color: 'var(--prio-none)' },
]

const menuRef  = ref<HTMLDivElement>()
const showMove = ref(false)
const showTags = ref(false)

function close() { emit('close') }
function handle(fn: () => void) { fn(); close() }

async function wontDo()    { handle(() => taskStore.wontDo(props.task.id)) }
async function duplicate() { handle(() => taskStore.duplicate(props.task.id)) }
async function trash()     { handle(() => taskStore.remove(props.task.id)) }
async function pin()       { handle(() => taskStore.pin(props.task.id)) }

async function setDate(date: Date) {
  handle(() => taskStore.update(props.task.id, { due_date: date.toISOString(), is_all_day: true }))
}

async function setPriority(p: number) {
  handle(() => taskStore.update(props.task.id, { priority: p }))
}

async function moveTo(projectId: number) {
  handle(() => taskStore.moveTo(props.task.id, projectId))
}

async function toggleTag(tagId: number) {
  const tags = props.task.tags.includes(tagId)
    ? props.task.tags.filter((t) => t !== tagId)
    : [...props.task.tags, tagId]
  await taskStore.update(props.task.id, { tags })
}

function addSubtask() {
  // Ouvre le détail sur la tâche et place le focus sur l'ajout de sous-tâche.
  taskStore.select(props.task.id)
  setTimeout(() => window.dispatchEvent(new CustomEvent('tt:focus-subtask')), 80)
  close()
}

async function startFocus() {
  taskStore.select(props.task.id)
  router.push('/focus')
  close()
}

async function copyLink() {
  const url = `${location.origin}/task/${props.task.id}`
  await navigator.clipboard.writeText(url).catch(() => {})
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
    class="menu task-context-menu"
    :style="`left: ${x}px; top: ${y}px`"
    @contextmenu.prevent
  >
    <!-- Date : rangée d'icônes -->
    <div class="menu-label">Date</div>
    <div class="quick-row">
      <button
        v-for="opt in DATE_OPTIONS" :key="opt.label"
        class="quick-btn" :title="opt.label"
        @click="setDate(opt.fn())"
      ><Icon :name="opt.icon" :size="16" /></button>
    </div>

    <!-- Priorité : rangée de drapeaux -->
    <div class="menu-label">Priorité</div>
    <div class="quick-row">
      <button
        v-for="p in PRIORITIES" :key="p.value"
        class="quick-btn flag-btn"
        :class="{ active: task.priority === p.value }"
        :style="`color:${p.color}`"
        :title="p.label"
        @click="setPriority(p.value)"
      ><Icon name="flag" :size="16" /></button>
    </div>

    <div class="menu-sep" />

    <button class="menu-item" @click="addSubtask">
      <span class="mi-icon"><Icon name="subtask" :size="15" /></span> Ajouter une sous-tâche
    </button>
    <button class="menu-item" @click="pin">
      <span class="mi-icon"><Icon name="pin" :size="15" /></span> {{ task.is_pinned ? 'Désépingler' : 'Épingler' }}
    </button>
    <button class="menu-item" @click="wontDo">
      <span class="mi-icon"><Icon name="x-circle" :size="15" /></span> Ne fera pas (Won't Do)
    </button>

    <!-- Déplacer vers -->
    <div class="menu-item submenu-trigger"
         @mouseenter="showMove = true" @mouseleave="showMove = false">
      <span class="mi-icon"><Icon name="arrow-right" :size="15" /></span> Déplacer vers
      <span class="submenu-arrow"><Icon name="chevron-right" :size="11" /></span>
      <div v-if="showMove" class="menu submenu submenu-scroll">
        <button
          v-for="p in projectStore.projects.filter(p => !p.is_smart)" :key="p.id"
          class="menu-item"
          :class="{ active: task.project === p.id }"
          @click="moveTo(p.id)"
        >
          <span class="mi-icon"><Icon :name="p.is_inbox ? 'inbox' : 'layers'" :size="14" /></span>
          {{ p.name }}
          <span v-if="task.project === p.id" class="mi-check">✓</span>
        </button>
      </div>
    </div>

    <!-- Étiquettes -->
    <div class="menu-item submenu-trigger"
         @mouseenter="showTags = true" @mouseleave="showTags = false">
      <span class="mi-icon"><Icon name="tag" :size="15" /></span> Étiquettes
      <span class="submenu-arrow"><Icon name="chevron-right" :size="11" /></span>
      <div v-if="showTags" class="menu submenu submenu-scroll">
        <div v-if="!tagStore.tags.length" class="menu-item disabled">Aucun tag</div>
        <button
          v-for="t in tagStore.tags" :key="t.id"
          class="menu-item"
          :class="{ active: task.tags.includes(t.id) }"
          @click.stop="toggleTag(t.id)"
        >
          <span class="tag-dot" :style="t.color ? `background:${t.color}` : ''" />
          {{ t.name }}
          <span v-if="task.tags.includes(t.id)" class="mi-check">✓</span>
        </button>
      </div>
    </div>

    <button class="menu-item" @click="startFocus">
      <span class="mi-icon"><Icon name="play" :size="15" /></span> Lancer le focus
    </button>

    <div class="menu-sep" />

    <button class="menu-item" @click="duplicate">
      <span class="mi-icon"><Icon name="copy" :size="15" /></span> Dupliquer
    </button>
    <button class="menu-item" @click="copyLink">
      <span class="mi-icon"><Icon name="link" :size="15" /></span> Copier le lien
    </button>

    <div class="menu-sep" />

    <button class="menu-item danger" @click="trash">
      <span class="mi-icon"><Icon name="trash" :size="15" /></span> Supprimer
    </button>
  </div>
</template>

<style scoped>
.task-context-menu {
  position: fixed;
  z-index: 2000;
  min-width: 210px;
}

.menu-label {
  font-size: 11px;
  color: var(--text-muted);
  padding: 4px 10px 2px;
}

.quick-row {
  display: flex;
  gap: 4px;
  padding: 2px 8px 6px;
}
.quick-btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 0;
  border: none;
  border-radius: 6px;
  background: none;
  cursor: pointer;
  color: var(--text-secondary);
}
.quick-btn:hover { background: var(--bg-hover); color: var(--text); }
.flag-btn.active { background: var(--bg-hover); }
.flag-btn.active svg { fill: currentColor; }

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
.submenu-arrow { margin-left: auto; color: var(--text-muted); display: inline-flex; }

.submenu {
  position: absolute;
  left: 100%;
  top: -5px;
  z-index: 2001;
  min-width: 180px;
}
.submenu-scroll {
  max-height: 240px;
  overflow-y: auto;
}

.mi-icon {
  width: 18px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
}
.mi-check { margin-left: auto; color: var(--primary); font-size: 12px; }

.tag-dot {
  display: inline-block;
  width: 10px; height: 10px;
  border-radius: 50%;
  background: #aaa;
  flex-shrink: 0;
}

.menu-item.active { font-weight: 500; }
.menu-item.disabled { color: var(--text-muted); cursor: default; }
.menu-item.disabled:hover { background: none; }
</style>
