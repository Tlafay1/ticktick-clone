<script setup lang="ts">
import { ref } from 'vue'
import { useTagStore } from '@/stores/tags'

defineEmits<{ close: [] }>()

const tagStore = useTagStore()

const newTagName = ref('')
const newTagColor = ref('#4772fa')
const newTagParent = ref<number | null>(null)
const editingTagId = ref<number | null>(null)
const editingTagName = ref('')
const editingTagColor = ref('')
const editingTagParent = ref<number | null>(null)
const TAG_COLORS = ['#4772fa','#f55','#fa0','#4af','#8f4','#c4f','#f48','#34c6a0','#e8590c','#aaa']

async function createTag() {
  const name = newTagName.value.trim()
  if (!name) return
  await tagStore.create(name, newTagColor.value, newTagParent.value)
  newTagName.value = ''
  newTagParent.value = null
}

function startEdit(tag: { id: number; name: string; color: string; parent: number | null }) {
  editingTagId.value = tag.id
  editingTagName.value = tag.name
  editingTagColor.value = tag.color
  editingTagParent.value = tag.parent
}

async function saveEdit() {
  if (!editingTagId.value) return
  await tagStore.update(editingTagId.value, { name: editingTagName.value.trim(), color: editingTagColor.value, parent: editingTagParent.value })
  editingTagId.value = null
}

async function removeTag(id: number) {
  if (!confirm('Supprimer ce tag ? Il sera retiré de toutes les tâches.')) return
  await tagStore.remove(id)
}

// Fusion : re-tague les tâches et reparente les enfants vers la cible.
const mergingTagId = ref<number | null>(null)
const mergeTargetId = ref<number | null>(null)

async function confirmMerge() {
  if (mergingTagId.value === null || mergeTargetId.value === null) return
  await tagStore.merge(mergingTagId.value, mergeTargetId.value)
  mergingTagId.value = null
  mergeTargetId.value = null
}
</script>

<template>
  <div class="modal-backdrop" @click.self="$emit('close')">
    <div class="modal-panel">
      <div class="modal-header">
        <h2>Gérer les étiquettes</h2>
        <button class="icon-btn" @click="$emit('close')">✕</button>
      </div>

      <!-- Créer un tag -->
      <div class="create-row">
        <div class="color-swatch-wrap">
          <span class="color-swatch" :style="`background:${newTagColor}`" />
          <div class="color-mini-picker">
            <button v-for="c in TAG_COLORS" :key="c" class="color-mini-dot"
              :class="{ active: newTagColor === c }" :style="`background:${c}`"
              @click="newTagColor = c" />
          </div>
        </div>
        <input v-model="newTagName" placeholder="Nom du tag…" class="tag-input"
          @keydown.enter="createTag" />
        <select v-model="newTagParent" class="parent-select">
          <option :value="null">— Racine —</option>
          <option v-for="t in tagStore.rootTags" :key="t.id" :value="t.id">#{{ t.name }}</option>
        </select>
        <button class="btn btn-primary" :disabled="!newTagName.trim()" @click="createTag">Créer</button>
      </div>

      <!-- Liste des tags -->
      <div class="tags-list">
        <div v-for="tag in tagStore.tags" :key="tag.id" class="tag-row">
          <template v-if="editingTagId === tag.id">
            <div class="color-swatch-wrap">
              <span class="color-swatch" :style="`background:${editingTagColor}`" />
              <div class="color-mini-picker">
                <button v-for="c in TAG_COLORS" :key="c" class="color-mini-dot"
                  :class="{ active: editingTagColor === c }" :style="`background:${c}`"
                  @click="editingTagColor = c" />
              </div>
            </div>
            <input v-model="editingTagName" class="tag-input"
              @keydown.enter="saveEdit" @keydown.escape="editingTagId = null" autofocus />
            <select v-model="editingTagParent" class="parent-select">
              <option :value="null">— Racine —</option>
              <option v-for="t in tagStore.rootTags.filter(t => t.id !== editingTagId)" :key="t.id" :value="t.id">#{{ t.name }}</option>
            </select>
            <button class="btn btn-primary" @click="saveEdit">✓</button>
            <button class="btn btn-ghost" @click="editingTagId = null">✕</button>
          </template>
          <template v-else-if="mergingTagId === tag.id">
            <span class="tag-name">Fusionner #{{ tag.name }} dans :</span>
            <select v-model="mergeTargetId" class="parent-select">
              <option :value="null">— Choisir la cible —</option>
              <option v-for="t in tagStore.tags.filter(t => t.id !== tag.id)" :key="t.id" :value="t.id">#{{ t.name }}</option>
            </select>
            <button class="btn btn-primary" :disabled="mergeTargetId === null" @click="confirmMerge">Fusionner</button>
            <button class="btn btn-ghost" @click="mergingTagId = null; mergeTargetId = null">✕</button>
          </template>
          <template v-else>
            <span class="tag-dot" :style="tag.color ? `background:${tag.color}` : 'background:var(--border)'" />
            <span class="tag-name">#{{ tag.name }}</span>
            <span v-if="tag.parent" class="tag-parent-hint">→ #{{ tagStore.tags.find(t => t.id === tag.parent)?.name }}</span>
            <button class="icon-btn" title="Fusionner dans un autre tag" @click="mergingTagId = tag.id; mergeTargetId = null">⇄</button>
            <button class="icon-btn" @click="startEdit(tag)">✏️</button>
            <button class="icon-btn danger-btn" @click="removeTag(tag.id)">🗑</button>
          </template>
        </div>
        <div v-if="!tagStore.tags.length" class="empty-hint">Aucune étiquette créée.</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 500;
}

.modal-panel {
  background: var(--bg);
  border-radius: 14px;
  padding: 24px;
  width: 520px;
  max-height: 80vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.modal-header h2 { margin: 0; font-size: 18px; font-weight: 700; }

.create-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: var(--bg-sidebar);
  border-radius: 10px;
}

.tag-input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 13px;
  background: var(--bg);
  color: var(--text);
  outline: none;
}
.tag-input:focus { border-color: var(--primary); }

.parent-select {
  padding: 6px 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 12px;
  background: var(--bg);
  color: var(--text);
  outline: none;
  max-width: 110px;
}

.tags-list { display: flex; flex-direction: column; gap: 4px; }

.tag-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  transition: background 0.1s;
}
.tag-row:hover { background: var(--bg-hover); }

.tag-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
.tag-name { flex: 1; font-size: 14px; }
.tag-parent-hint { font-size: 11px; color: var(--text-muted); }
.danger-btn { color: var(--danger); }

/* Sélecteur de couleur */
.color-swatch-wrap { position: relative; flex-shrink: 0; }
.color-swatch {
  display: inline-block;
  width: 20px; height: 20px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid var(--border);
}
.color-mini-picker {
  position: absolute;
  top: 28px; left: 0;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 6px;
  display: none;
  flex-wrap: wrap;
  gap: 4px;
  width: 130px;
  z-index: 10;
}
.color-swatch-wrap:hover .color-mini-picker { display: flex; }
.color-mini-dot { width: 16px; height: 16px; border-radius: 50%; border: 2px solid transparent; cursor: pointer; }
.color-mini-dot.active { border-color: var(--text); }

.empty-hint { color: var(--text-muted); font-size: 13px; padding: 8px; }
</style>
