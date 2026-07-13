<script setup lang="ts">
// Fenêtre « Saisie rapide » d'Electron (Ctrl+Maj+A global) : un seul champ,
// NLP identique au quick-add, création dans l'Inbox (ou la ^Liste reconnue).
import { ref, computed, onMounted } from 'vue'
import { useProjectStore } from '@/stores/projects'
import { useTagStore } from '@/stores/tags'
import { tasksApi } from '@/api'
import { parseQuickAdd } from '@/lib/nlp'
import { format } from 'date-fns'

const projectStore = useProjectStore()
const tagStore = useTagStore()
const text = ref('')
const flash = ref(false)
const input = ref<HTMLInputElement>()

onMounted(async () => {
  if (!projectStore.projects.length) await projectStore.load().catch(() => {})
  if (!tagStore.tags.length) await tagStore.load().catch(() => {})
  input.value?.focus()
  // Refocus à chaque réaffichage de la fenêtre.
  window.addEventListener('focus', () => input.value?.focus())
})

const projectNames = computed(() => projectStore.projects.map(p => p.name))
const parsed = computed(() =>
  text.value ? parseQuickAdd(text.value, { projectNames: projectNames.value }) : null,
)

async function submit() {
  const raw = text.value.trim()
  if (!raw) return
  const p = parsed.value
  let projectId = projectStore.inbox?.id
  if (p?.projectName) {
    const match = projectStore.projects.find(pr => pr.name.toLowerCase() === p.projectName!.toLowerCase())
    if (match) projectId = match.id
  }
  if (!projectId) return
  const tags: number[] = []
  for (const name of p?.tagNames ?? []) {
    const existing = tagStore.tags.find(t => t.name.toLowerCase() === name.toLowerCase())
    const tag = existing ?? await tagStore.create(name)
    tags.push(tag.id)
  }
  await tasksApi.create({
    title: p?.title || raw,
    project: projectId,
    due_date: p?.due ? p.due.toISOString() : undefined,
    is_all_day: !p?.hasTime,
    priority: p?.priority ?? 0,
    tags,
  })
  text.value = ''
  flash.value = true
  setTimeout(() => { flash.value = false }, 1200)
}
</script>

<template>
  <div class="qa-window">
    <span class="qa-plus">＋</span>
    <input
      ref="input"
      v-model="text"
      class="qa-input"
      placeholder="Ajouter une tâche (demain, !high, #tag, ^Liste)…"
      @keydown.enter="submit"
      @keydown.escape="text = ''"
    />
    <span v-if="flash" class="qa-flash">✓ Ajoutée</span>
    <span v-else-if="parsed?.due" class="qa-chip">{{ format(parsed.due, 'dd/MM') }}</span>
  </div>
</template>

<style scoped>
.qa-window {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 100vh;
  padding: 0 18px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-sizing: border-box;
}
.qa-plus { font-size: 18px; color: var(--primary); }
.qa-input {
  flex: 1;
  border: none;
  outline: none;
  background: none;
  font-size: 15px;
  color: var(--text);
}
.qa-flash { font-size: 13px; color: var(--success, #2f9e44); white-space: nowrap; }
.qa-chip {
  font-size: 11px;
  background: var(--primary-soft);
  color: var(--primary);
  border-radius: 4px;
  padding: 2px 6px;
  white-space: nowrap;
}
</style>
