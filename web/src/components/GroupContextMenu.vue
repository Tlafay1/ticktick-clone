<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import type { ProjectGroup } from '@/types'
import { useProjectStore } from '@/stores/projects'

const props = defineProps<{ group: ProjectGroup; x: number; y: number }>()
const emit = defineEmits<{ close: [] }>()

const projectStore = useProjectStore()
const menuRef = ref<HTMLDivElement>()
const editingName = ref(false)
const nameInput = ref(props.group.name)

function close() { emit('close') }

async function rename() {
  const name = nameInput.value.trim()
  if (!name || name === props.group.name) { editingName.value = false; return }
  await projectStore.updateGroup(props.group.id, { name })
  editingName.value = false
  close()
}

async function remove() {
  if (!confirm(`Supprimer le dossier « ${props.group.name} » ? Les listes seront déplacées hors du dossier.`)) return
  await projectStore.removeGroup(props.group.id)
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
    class="menu group-context-menu"
    :style="`left: ${x}px; top: ${y}px`"
    @contextmenu.prevent
  >
    <div v-if="editingName" class="rename-row">
      <input
        v-model="nameInput"
        class="rename-input"
        @keydown.enter="rename"
        @keydown.escape="editingName = false"
        autofocus
      />
      <button class="rename-ok" @click="rename">✓</button>
    </div>
    <template v-else>
      <button class="menu-item" @click="editingName = true; nameInput = group.name">
        <span class="mi-icon">✏️</span> Renommer le dossier
      </button>
      <div class="menu-sep" />
      <button class="menu-item danger" @click="remove">
        <span class="mi-icon">🗑</span> Supprimer le dossier
      </button>
    </template>
  </div>
</template>

<style scoped>
.group-context-menu { position: fixed; z-index: 2000; min-width: 200px; }
.mi-icon { width: 18px; text-align: center; flex-shrink: 0; }
.rename-row { display: flex; gap: 6px; padding: 6px 10px; }
.rename-input {
  flex: 1; padding: 4px 8px; border: 1px solid var(--accent);
  border-radius: 4px; background: var(--bg-card); color: var(--text); font-size: 13px;
}
.rename-ok {
  padding: 4px 8px; background: var(--accent); color: #fff;
  border: none; border-radius: 4px; cursor: pointer;
}
</style>
