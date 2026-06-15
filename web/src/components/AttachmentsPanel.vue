<script setup lang="ts">
import { ref, watch } from 'vue'
import { attachmentsApi } from '@/api'
import type { Attachment } from '@/types'

const props = defineProps<{ taskId: number | null }>()

const attachments = ref<Attachment[]>([])
const uploading = ref(false)

watch(() => props.taskId, async (id) => {
  if (!id) { attachments.value = []; return }
  attachments.value = await attachmentsApi.list(id)
}, { immediate: true })

async function pick() {
  if (!props.taskId) return
  const input = document.createElement('input')
  input.type = 'file'
  input.multiple = true
  input.onchange = async () => {
    const files = Array.from(input.files ?? [])
    if (!files.length) return
    uploading.value = true
    try {
      for (const f of files) {
        const a = await attachmentsApi.upload(props.taskId!, f)
        attachments.value.push(a)
      }
    } finally {
      uploading.value = false
    }
  }
  input.click()
}

async function remove(a: Attachment) {
  await attachmentsApi.remove(a.id)
  attachments.value = attachments.value.filter(x => x.id !== a.id)
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} o`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`
  return `${(bytes / 1024 / 1024).toFixed(1)} Mo`
}

function isImage(ct: string) {
  return ct.startsWith('image/')
}

</script>

<template>
  <div class="attachments-panel">
    <div class="panel-header">
      <span class="panel-title">📎 Pièces jointes</span>
      <button class="add-btn" :disabled="uploading" @click="pick">
        {{ uploading ? '…' : '＋' }}
      </button>
    </div>

    <div v-if="attachments.length" class="attach-list">
      <div v-for="a in attachments" :key="a.id" class="attach-item">
        <img
          v-if="isImage(a.content_type)"
          :src="a.url"
          class="attach-thumb"
          :alt="a.filename"
        />
        <span v-else class="attach-icon">📄</span>

        <div class="attach-info">
          <a :href="a.url" target="_blank" class="attach-name">{{ a.filename }}</a>
          <span class="attach-size">{{ formatSize(a.size) }}</span>
        </div>

        <button class="remove-btn" title="Supprimer" @click="remove(a)">✕</button>
      </div>
    </div>

    <div v-else class="attach-empty">Aucune pièce jointe</div>
  </div>

</template>

<style scoped>
.attachments-panel {
  border-top: 1px solid var(--border);
  padding: 12px 0 4px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0 8px;
}
.panel-title { font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.4px; }
.add-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  color: var(--primary);
  padding: 0 4px;
}
.add-btn:disabled { opacity: 0.5; cursor: wait; }

.attach-list { display: flex; flex-direction: column; gap: 6px; }

.attach-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
}
.attach-item:hover .remove-btn { opacity: 1; }

.attach-thumb {
  width: 40px;
  height: 40px;
  object-fit: cover;
  border-radius: 4px;
  flex-shrink: 0;
}
.attach-icon { font-size: 28px; flex-shrink: 0; }

.attach-info { flex: 1; min-width: 0; }
.attach-name {
  display: block;
  font-size: 13px;
  color: var(--primary);
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.attach-name:hover { text-decoration: underline; }
.attach-size { font-size: 11px; color: var(--text-muted); }


.remove-btn {
  opacity: 0;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 12px;
  padding: 2px 4px;
  flex-shrink: 0;
}

.attach-empty { font-size: 12px; color: var(--text-muted); padding: 4px 0; }
</style>
