<script setup lang="ts">
import { ref, watch } from 'vue'
import { versionsApi } from '@/api'
import type { TaskVersion } from '@/types'
import { renderMarkdown } from '@/lib/markdown'

const props = defineProps<{ taskId: number | null }>()
const emit = defineEmits<{ (e: 'restored', description: string): void }>()

const versions = ref<TaskVersion[]>([])
const expanded = ref(false)
const preview = ref<TaskVersion | null>(null)

watch(() => props.taskId, async (id) => {
  versions.value = []
  if (!id) return
  versions.value = await versionsApi.list(id)
}, { immediate: true })

async function restore(v: TaskVersion) {
  if (!props.taskId) return
  if (!confirm('Restaurer cette version de la description ?')) return
  const updated = await versionsApi.restore(props.taskId, v.id)
  emit('restored', updated.description)
  preview.value = null
}

function relativeDate(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60_000)
  if (m < 1) return "À l'instant"
  if (m < 60) return `Il y a ${m} min`
  const h = Math.floor(m / 60)
  if (h < 24) return `Il y a ${h} h`
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })
}
</script>

<template>
  <div class="version-history">
    <button class="toggle-btn" @click="expanded = !expanded">
      <span>🕐 Historique ({{ versions.length }})</span>
      <span class="chevron">{{ expanded ? '▲' : '▼' }}</span>
    </button>

    <div v-if="expanded" class="versions-list">
      <div
        v-for="v in versions"
        :key="v.id"
        class="version-item"
        :class="{ active: preview?.id === v.id }"
        @click="preview = preview?.id === v.id ? null : v"
      >
        <span class="version-date">{{ relativeDate(v.created_at) }}</span>
        <button class="restore-btn" title="Restaurer" @click.stop="restore(v)">↩ Restaurer</button>
      </div>

      <div v-if="preview" class="version-preview md-body" v-html="renderMarkdown(preview.description)" />

      <div v-if="versions.length === 0" class="no-versions">Aucun historique</div>
    </div>
  </div>
</template>

<style scoped>
.version-history {
  border-top: 1px solid var(--border);
  padding: 10px 0 4px;
}

.toggle-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  padding: 0 0 6px;
}
.chevron { font-size: 10px; }

.versions-list { display: flex; flex-direction: column; gap: 4px; }

.version-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
.version-item:hover { background: var(--bg-hover); }
.version-item.active { background: var(--bg-active); }

.version-date { color: var(--text-secondary); }

.restore-btn {
  background: none;
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 2px 8px;
  font-size: 11.5px;
  cursor: pointer;
  color: var(--primary);
}
.restore-btn:hover { background: var(--bg-hover); }

.version-preview {
  margin-top: 8px;
  padding: 10px;
  background: var(--bg-sidebar);
  border-radius: 8px;
  border: 1px solid var(--border);
  font-size: 13px;
  max-height: 200px;
  overflow-y: auto;
}

.no-versions { font-size: 12px; color: var(--text-muted); padding: 4px 0; }
</style>
