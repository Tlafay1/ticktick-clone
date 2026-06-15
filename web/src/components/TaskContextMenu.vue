<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import type { Task } from '@/types'
import { useTaskStore } from '@/stores/tasks'
import { useProjectStore } from '@/stores/projects'
import { useTagStore } from '@/stores/tags'
import { addDays, startOfDay, addWeeks, nextMonday } from 'date-fns'

const props = defineProps<{ task: Task; x: number; y: number }>()
const emit = defineEmits<{ close: [] }>()

const taskStore = useTaskStore()
const projectStore = useProjectStore()
const tagStore = useTagStore()
const router = useRouter()

const SNOOZE_OPTIONS = [
  { label: 'Demain',           icon: '🌤️', fn: () => addDays(startOfDay(new Date()), 1) },
  { label: 'Après-demain',     icon: '📅', fn: () => addDays(startOfDay(new Date()), 2) },
  { label: 'Semaine prochaine',icon: '📆', fn: () => nextMonday(startOfDay(new Date())) },
  { label: '+3 jours',         icon: '⏩', fn: () => addDays(startOfDay(new Date()), 3) },
  { label: '+1 semaine',       icon: '⏭️', fn: () => addWeeks(startOfDay(new Date()), 1) },
]

const PRIORITIES = [
  { label: 'Haute',   value: 5, color: '#f55' },
  { label: 'Moyenne', value: 3, color: '#fa0' },
  { label: 'Basse',   value: 1, color: '#4af' },
  { label: 'Aucune',  value: 0, color: '#aaa' },
]

const menuRef   = ref<HTMLDivElement>()
const showSnooze  = ref(false)
const showMove    = ref(false)
const showTags    = ref(false)
const showPriority = ref(false)

function close() { emit('close') }

function handle(fn: () => void) { fn(); close() }

async function wontDo()    { handle(() => taskStore.wontDo(props.task.id)) }
async function duplicate() { handle(() => taskStore.duplicate(props.task.id)) }
async function trash()     { handle(() => taskStore.remove(props.task.id)) }
async function pin()       { handle(() => taskStore.pin(props.task.id)) }

async function snooze(date: Date) {
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
    <!-- Compléter / Won't Do -->
    <button class="menu-item" @click="taskStore.complete(task.id); close()">
      <span class="mi-icon">✓</span> Terminer
    </button>
    <button class="menu-item" @click="wontDo">
      <span class="mi-icon">✗</span> Ne fera pas (Won't Do)
    </button>

    <div class="menu-sep" />

    <!-- Priorité -->
    <div class="menu-item submenu-trigger"
         @mouseenter="showPriority = true" @mouseleave="showPriority = false">
      <span class="mi-icon">🚩</span> Priorité
      <span class="submenu-arrow">▶</span>
      <div v-if="showPriority" class="menu submenu">
        <button
          v-for="p in PRIORITIES" :key="p.value"
          class="menu-item"
          :class="{ active: task.priority === p.value }"
          @click="setPriority(p.value)"
        >
          <span class="priority-dot" :style="`background:${p.color}`" /> {{ p.label }}
          <span v-if="task.priority === p.value" class="mi-check">✓</span>
        </button>
      </div>
    </div>

    <!-- Épingler -->
    <button class="menu-item" @click="pin">
      <span class="mi-icon">📌</span> {{ task.is_pinned ? 'Désépingler' : 'Épingler' }}
    </button>

    <div class="menu-sep" />

    <!-- Reporter -->
    <div class="menu-item submenu-trigger"
         @mouseenter="showSnooze = true" @mouseleave="showSnooze = false">
      <span class="mi-icon">⏰</span> Reporter
      <span class="submenu-arrow">▶</span>
      <div v-if="showSnooze" class="menu submenu">
        <button
          v-for="opt in SNOOZE_OPTIONS" :key="opt.label"
          class="menu-item"
          @click="snooze(opt.fn())"
        ><span>{{ opt.icon }}</span> {{ opt.label }}</button>
      </div>
    </div>

    <!-- Déplacer vers -->
    <div class="menu-item submenu-trigger"
         @mouseenter="showMove = true" @mouseleave="showMove = false">
      <span class="mi-icon">→</span> Déplacer vers
      <span class="submenu-arrow">▶</span>
      <div v-if="showMove" class="menu submenu submenu-scroll">
        <button
          v-for="p in projectStore.projects" :key="p.id"
          class="menu-item"
          :class="{ active: task.project === p.id }"
          @click="moveTo(p.id)"
        >
          <span class="mi-icon">{{ p.is_inbox ? '📥' : '📋' }}</span>
          {{ p.name }}
          <span v-if="task.project === p.id" class="mi-check">✓</span>
        </button>
      </div>
    </div>

    <!-- Étiquettes -->
    <div class="menu-item submenu-trigger"
         @mouseenter="showTags = true" @mouseleave="showTags = false">
      <span class="mi-icon">#</span> Étiquettes
      <span class="submenu-arrow">▶</span>
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

    <div class="menu-sep" />

    <!-- Focus -->
    <button class="menu-item" @click="startFocus">
      <span class="mi-icon">🍅</span> Lancer le focus
    </button>

    <!-- Dupliquer -->
    <button class="menu-item" @click="duplicate">
      <span class="mi-icon">⧉</span> Dupliquer
    </button>

    <!-- Copier lien -->
    <button class="menu-item" @click="copyLink">
      <span class="mi-icon">🔗</span> Copier le lien
    </button>

    <div class="menu-sep" />

    <!-- Corbeille -->
    <button class="menu-item danger" @click="trash">
      <span class="mi-icon">🗑</span> Mettre à la corbeille
    </button>
  </div>
</template>

<style scoped>
.task-context-menu {
  position: fixed;
  z-index: 2000;
  min-width: 200px;
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
.submenu-scroll {
  max-height: 240px;
  overflow-y: auto;
}

.mi-icon { width: 18px; text-align: center; flex-shrink: 0; font-size: 13px; }
.mi-check { margin-left: auto; color: var(--accent); font-size: 12px; }

.priority-dot, .tag-dot {
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
