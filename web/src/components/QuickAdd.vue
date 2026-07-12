<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useTaskStore } from '@/stores/tasks'
import { useProjectStore } from '@/stores/projects'
import { useTagStore } from '@/stores/tags'
import { parseQuickAdd } from '@/lib/nlp'
import { format } from 'date-fns'
import { templatesApi } from '@/api'
import type { Template } from '@/types'

const props = defineProps<{ projectId?: number }>()
const taskStore = useTaskStore()
const projectStore = useProjectStore()
const tagStore = useTagStore()

const projectNames = computed(() => projectStore.projects.map(p => p.name))

/** Résout des noms de tags en ids (crée les manquants). */
async function resolveTagIds(names: string[]): Promise<number[]> {
  const ids: number[] = []
  for (const name of names) {
    const existing = tagStore.tags.find(t => t.name.toLowerCase() === name.toLowerCase())
    const tag = existing ?? await tagStore.create(name)
    ids.push(tag.id)
  }
  return ids
}

/** ^Liste explicite (si reconnue) sinon la liste courante / Inbox. */
function resolveProjectId(name: string | null): number | null {
  if (name) {
    const p = projectStore.projects.find(pr => pr.name.toLowerCase() === name.toLowerCase())
    if (p) return p.id
  }
  return targetProject.value
}

const text = ref('')
const open = ref(false)
const input = ref<HTMLInputElement>()
const templates = ref<Template[]>([])
const showTemplates = ref(false)

async function loadTemplates() {
  if (!templates.value.length) templates.value = await templatesApi.list().catch(() => [])
}

function applyTemplate(t: Template) {
  const data = t.data as Partial<{ title: string; priority: number; description: string }>
  if (data.title) text.value = data.title
  showTemplates.value = false
}

const parsed = computed(() =>
  text.value ? parseQuickAdd(text.value, { projectNames: projectNames.value }) : null,
)

const targetProject = computed(() => {
  if (props.projectId) return props.projectId
  return projectStore.inbox?.id ?? null
})

async function submit() {
  const raw = text.value.trim()
  if (!raw || !targetProject.value) return
  const p = parsed.value
  const tags = p?.tagNames.length ? await resolveTagIds(p.tagNames) : []
  await taskStore.create({
    title: p?.title || raw,
    project: resolveProjectId(p?.projectName ?? null) ?? targetProject.value,
    due_date: p?.due ? p.due.toISOString() : undefined,
    is_all_day: !p?.hasTime,
    priority: p?.priority ?? 0,
    tags,
  })
  text.value = ''
  open.value = false
}

async function handlePaste(e: ClipboardEvent) {
  const pasted = e.clipboardData?.getData('text') ?? ''
  const lines = pasted.split('\n').map(l => l.trim()).filter(Boolean)
  if (lines.length < 2 || !targetProject.value) return
  // Multi-line : créer une tâche par ligne
  e.preventDefault()
  for (const line of lines) {
    const p = parseQuickAdd(line, { projectNames: projectNames.value })
    const tags = p.tagNames.length ? await resolveTagIds(p.tagNames) : []
    await taskStore.create({
      title: p.title || line,
      project: resolveProjectId(p.projectName) ?? targetProject.value!,
      due_date: p.due?.toISOString(),
      is_all_day: !p.hasTime,
      priority: p.priority ?? 0,
      tags,
    })
  }
  text.value = ''
  open.value = false
}

function focus() {
  open.value = true
  setTimeout(() => input.value?.focus(), 50)
}

// Raccourci global Ctrl+Maj+A
onMounted(() => window.addEventListener('tt:focus-quickadd', focus))
onUnmounted(() => window.removeEventListener('tt:focus-quickadd', focus))
</script>

<template>
  <div class="quick-add">
    <div v-if="!open" class="quick-add-trigger" @click="focus">
      <span class="plus">＋</span>
      <span class="placeholder">Ajouter une tâche</span>
    </div>
    <div v-else class="quick-add-form">
      <input
        ref="input"
        v-model="text"
        placeholder="Titre (demain, !high, #tag…)"
        @keydown.enter="submit"
        @keydown.escape="open = false; text = ''"
        @paste="handlePaste"
      />
      <div v-if="parsed" class="nlp-chips">
        <span v-if="parsed.due" class="nlp-chip">📅 {{ format(parsed.due, 'dd/MM') }}</span>
        <span v-if="parsed.priority" class="nlp-chip">
          {{ parsed.priority === 5 ? '🔴' : parsed.priority === 3 ? '🟡' : '🔵' }}
        </span>
        <span v-for="tag in parsed.tagNames" :key="tag" class="nlp-chip">#{{ tag }}</span>
      </div>
      <div class="quick-add-actions">
        <button class="btn btn-primary" @click="submit">Ajouter</button>
        <button class="btn btn-ghost" @click="open = false; text = ''">Annuler</button>
        <button class="btn btn-ghost" @click="showTemplates = !showTemplates; loadTemplates()" title="Templates">📋</button>
      </div>
      <div v-if="showTemplates" class="tmpl-picker">
        <div v-if="!templates.length" class="tmpl-empty">Aucun template.</div>
        <div
          v-for="t in templates.filter(t => t.scope === 'task')"
          :key="t.id"
          class="tmpl-option"
          @click="applyTemplate(t)"
        >{{ t.name }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.quick-add { padding: 8px 16px 4px; }

.quick-add-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 4px;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 8px;
}
.quick-add-trigger:hover { color: var(--primary); }
.plus { font-size: 18px; }
.placeholder { font-size: 14px; }

.quick-add-form {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}
.quick-add-form input {
  width: 100%;
  border: none;
  outline: none;
  font-size: 14px;
  background: none;
}
.nlp-chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin: 8px 0 4px;
}
.nlp-chip {
  font-size: 11px;
  background: var(--primary-soft);
  color: var(--primary);
  border-radius: 4px;
  padding: 2px 6px;
}
.quick-add-actions {
  display: flex;
  gap: 6px;
  margin-top: 10px;
}
.tmpl-picker {
  margin-top: 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
  max-height: 160px;
  overflow-y: auto;
}
.tmpl-option {
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
}
.tmpl-option:hover { background: var(--bg-hover); }
.tmpl-empty {
  padding: 8px 12px;
  color: var(--text-muted);
  font-size: 12px;
}
</style>
