<script setup lang="ts">
import { ref, watch } from 'vue'
import { useTaskStore } from '@/stores/tasks'
import { tasksApi } from '@/api'
import type { Task } from '@/types'

const taskStore = useTaskStore()
const query = ref('')
const searching = ref(false)

let timer: ReturnType<typeof setTimeout> | null = null

watch(query, (q) => {
  if (timer) clearTimeout(timer)
  if (!q.trim()) {
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
  searching.value = false
}
</script>

<template>
  <div class="search-bar" :class="{ active: searching }">
    <span class="search-icon">🔍</span>
    <input
      v-model="query"
      placeholder="Rechercher…"
      class="search-input"
      @keydown.escape="clear"
    />
    <button v-if="query" class="clear-btn icon-btn" @click="clear">✕</button>
  </div>
</template>

<style scoped>
.search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--bg);
  transition: border-color 0.15s;
}
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
