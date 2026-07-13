<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useTaskStore } from '@/stores/tasks'
import Icon from './Icon.vue'
import { tasksApi } from '@/api'
import type { Task } from '@/types'

const emit = defineEmits<{ reset: [] }>()
const taskStore = useTaskStore()
const query = ref('')
const searching = ref(false)

// Historique des recherches (module 9) : suggestions au focus, champ vide.
const history = ref<string[]>([])
const showHistory = ref(false)

async function loadHistory() {
  const entries = await tasksApi.searchHistory().catch(() => [])
  history.value = [...new Set(entries.map(e => e.query))].slice(0, 8)
}

async function onFocus() {
  if (query.value.trim()) return
  await loadHistory()
  if (history.value.length) showHistory.value = true
}

function pickHistory(q: string) {
  query.value = q
  showHistory.value = false
}

async function clearHistory() {
  await tasksApi.clearSearchHistory().catch(() => {})
  history.value = []
  showHistory.value = false
}

function onBlur() {
  // Laisse le mousedown des items s'exécuter avant de fermer.
  setTimeout(() => { showHistory.value = false }, 150)
}

let timer: ReturnType<typeof setTimeout> | null = null

watch(query, (q) => {
  if (timer) clearTimeout(timer)
  if (q.trim()) showHistory.value = false
  if (!q.trim()) {
    // Fin de recherche : recharger la vue courante (sinon résultats périmés).
    if (searching.value) emit('reset')
    searching.value = false
    return
  }
  timer = setTimeout(async () => {
    searching.value = true
    taskStore.tasks = await tasksApi.list({ q: q.trim(), status: 0 }) as Task[]
  }, 300)
})

function clear() {
  query.value = ''
}

// Raccourci global Ctrl+F
const inputEl = ref<HTMLInputElement>()
function focusSearch() { inputEl.value?.focus() }
onMounted(() => window.addEventListener('tt:focus-search', focusSearch))
onUnmounted(() => window.removeEventListener('tt:focus-search', focusSearch))
</script>

<template>
  <div class="search-bar" :class="{ active: searching }">
    <span class="search-icon"><Icon name="search" :size="14" /></span>
    <input
      ref="inputEl"
      v-model="query"
      placeholder="Rechercher…"
      class="search-input"
      @focus="onFocus"
      @blur="onBlur"
      @keydown.escape="clear(); showHistory = false"
    />
    <button v-if="query" class="clear-btn icon-btn" @click="clear">✕</button>

    <!-- Historique des recherches -->
    <div v-if="showHistory" class="history-pop">
      <div class="history-head">
        <span>Recherches récentes</span>
        <button class="history-clear" @click="clearHistory">Effacer</button>
      </div>
      <button v-for="q in history" :key="q" class="history-item" @mousedown.prevent="pickHistory(q)">
        <Icon name="search" :size="12" /> {{ q }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.search-bar {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--bg);
  transition: border-color 0.15s;
}

.history-pop {
  position: absolute;
  top: 100%;
  left: 12px;
  right: 12px;
  z-index: 60;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 0 0 10px 10px;
  box-shadow: 0 6px 18px rgba(0,0,0,0.15);
  overflow: hidden;
}
.history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 12px 4px;
  font-size: 10.5px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  color: var(--text-muted);
}
.history-clear {
  border: none;
  background: none;
  color: var(--text-muted);
  font-size: 11px;
  cursor: pointer;
}
.history-clear:hover { color: var(--danger); }
.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 12px;
  border: none;
  background: none;
  color: var(--text);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
}
.history-item:hover { background: var(--bg-hover); }
.search-bar.active { border-bottom-color: var(--primary); }

.search-icon { color: var(--text-muted); font-size: 14px; }

.search-input {
  flex: 1;
  border: none;
  outline: none;
  background: none;
  font-size: 14px;
  color: var(--text);
}

.clear-btn { color: var(--text-muted); }
</style>
