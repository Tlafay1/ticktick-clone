<template>
  <div class="template-mgr">
    <div class="tmpl-header" @click="expanded = !expanded">
      <span>📋 Templates</span>
      <span class="tmpl-arrow">{{ expanded ? '▲' : '▼' }}</span>
    </div>
    <div v-if="expanded" class="tmpl-body">
      <!-- Sauvegarder la tâche courante comme template -->
      <div v-if="task" class="tmpl-save">
        <input v-model="newName" placeholder="Nom du template…" class="tmpl-input" />
        <button @click="saveTemplate" :disabled="!newName.trim()" class="tmpl-btn">Enregistrer</button>
      </div>

      <!-- Liste des templates existants -->
      <ul v-if="templates.length" class="tmpl-list">
        <li v-for="t in templates" :key="t.id" class="tmpl-item">
          <span class="tmpl-name">{{ t.name }}</span>
          <span class="tmpl-scope">{{ t.scope === 'task' ? 'tâche' : 'liste' }}</span>
          <button v-if="onApply" @click="apply(t)" class="tmpl-apply-btn" title="Appliquer">↩</button>
          <button @click="remove(t.id)" class="tmpl-del-btn" title="Supprimer">✕</button>
        </li>
      </ul>
      <p v-else-if="!task" class="tmpl-empty">Aucun template sauvegardé.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { templatesApi } from '@/api'
import type { Task, Template } from '@/types'

const props = defineProps<{
  task?: Task | null
  onApply?: ((data: Template['data']) => void) | null
}>()

const expanded = ref(false)
const templates = ref<Template[]>([])
const newName = ref('')

async function load() {
  templates.value = await templatesApi.list()
}

async function saveTemplate() {
  if (!props.task || !newName.value.trim()) return
  const data: Partial<Task> = {
    title: props.task.title,
    description: props.task.description,
    priority: props.task.priority,
    tags: props.task.tags,
    project: props.task.project,
  }
  const t = await templatesApi.create({ name: newName.value.trim(), scope: 'task', data })
  templates.value.push(t)
  newName.value = ''
}

async function remove(id: number) {
  await templatesApi.remove(id)
  templates.value = templates.value.filter(t => t.id !== id)
}

function apply(t: Template) {
  props.onApply?.(t.data)
}

onMounted(load)
</script>

<style scoped>
.template-mgr {
  margin-top: 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}
.tmpl-header {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
  background: var(--bg-card);
  user-select: none;
}
.tmpl-body { padding: 10px 12px; background: var(--bg); }
.tmpl-save { display: flex; gap: 8px; margin-bottom: 10px; }
.tmpl-input {
  flex: 1;
  padding: 4px 8px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--bg-card);
  color: var(--text);
  font-size: 12px;
}
.tmpl-btn, .tmpl-apply-btn, .tmpl-del-btn {
  padding: 4px 10px;
  border: 1px solid var(--border);
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  background: var(--bg-card);
  color: var(--text);
}
.tmpl-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.tmpl-apply-btn { color: var(--accent); }
.tmpl-del-btn { color: #e55; }
.tmpl-list { list-style: none; margin: 0; padding: 0; }
.tmpl-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
}
.tmpl-item:last-child { border-bottom: none; }
.tmpl-name { flex: 1; font-size: 13px; }
.tmpl-scope {
  font-size: 10px;
  color: var(--text-muted);
  padding: 1px 5px;
  background: var(--bg-card);
  border-radius: 3px;
}
.tmpl-empty { color: var(--text-muted); font-size: 12px; }
</style>
