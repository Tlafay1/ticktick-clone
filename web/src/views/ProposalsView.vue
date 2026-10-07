<script setup lang="ts">
// Propositions des agents (M39) : rien n'entre dans tes listes sans ton accord.
import { computed, onMounted, ref } from 'vue'
import Sidebar from '@/components/Sidebar.vue'
import { tasksApi } from '@/api'
import { pushToast } from '@/composables/useToast'
import { dueLabel } from '@/lib/dates'
import { useProjectStore } from '@/stores/projects'
import type { Task } from '@/types'

const projectStore = useProjectStore()
const proposals = ref<Task[]>([])
const loading = ref(true)

async function load() {
  loading.value = true
  proposals.value = await tasksApi.list({ proposed: 1, status: 0 }).catch(() => [])
  loading.value = false
}

onMounted(() => {
  if (!projectStore.projects.length) projectStore.load()
  load()
})

const groups = computed(() => {
  const byProject = new Map<number, Task[]>()
  for (const t of proposals.value) {
    byProject.set(t.project, [...(byProject.get(t.project) ?? []), t])
  }
  return [...byProject.entries()].map(([id, tasks]) => ({
    id,
    name: projectStore.projects.find(p => p.id === id)?.name ?? 'Liste',
    tasks,
  }))
})

function drop(id: number) {
  proposals.value = proposals.value.filter(t => t.id !== id)
}

async function accept(task: Task) {
  await tasksApi.update(task.id, { proposed: false })
  drop(task.id)
}

async function reject(task: Task) {
  await tasksApi.remove(task.id, true)
  drop(task.id)
}

async function acceptAll() {
  const list = [...proposals.value]
  await Promise.all(list.map(t => tasksApi.update(t.id, { proposed: false })))
  proposals.value = []
  pushToast(`${list.length} tâche${list.length > 1 ? 's' : ''} ajoutée${list.length > 1 ? 's' : ''}`, 'success')
}

async function rejectAll() {
  if (!confirm('Refuser toutes les propositions ?')) return
  await Promise.all(proposals.value.map(t => tasksApi.remove(t.id, true)))
  proposals.value = []
}
</script>

<template>
  <div class="app-layout">
    <Sidebar />
    <main class="proposals-main">
      <div class="list-header">
        <h1 class="list-title">Propositions</h1>
        <div v-if="proposals.length" class="header-right">
          <button class="btn btn-primary" @click="acceptAll">Tout accepter</button>
          <button class="btn btn-ghost" @click="rejectAll">Tout refuser</button>
        </div>
      </div>
      <p class="intro">
        Ce que tes agents te proposent. Rien n'entre dans tes listes sans ton accord.
      </p>

      <div v-if="!loading && !proposals.length" class="empty-state">
        <div class="empty-icon">✨</div>
        <p>Rien à valider pour l'instant.</p>
      </div>

      <section v-for="g in groups" :key="g.id" class="group">
        <h2 class="group-name">{{ g.name }}</h2>
        <div v-for="t in g.tasks" :key="t.id" class="proposal">
          <div class="proposal-body">
            <span class="proposal-title">{{ t.title }}</span>
            <span v-if="t.due_date" class="proposal-due">{{ dueLabel(t.due_date, t.is_all_day) }}</span>
            <span v-if="t.description" class="proposal-desc">{{ t.description }}</span>
          </div>
          <button class="icon-btn accept" title="Accepter" @click="accept(t)">✓</button>
          <button class="icon-btn" title="Refuser" @click="reject(t)">✕</button>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.app-layout { display: flex; height: 100%; overflow: hidden; }
.proposals-main { flex: 1; min-width: 0; overflow-y: auto; padding-bottom: 40px; }
.list-header {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  padding: 20px 20px 8px;
}
.list-title { margin: 0; font-size: 20px; }
.header-right { display: flex; gap: 6px; }
.intro { margin: 0 20px 12px; color: var(--text-secondary); font-size: 13px; }
.group { margin: 0 20px 16px; }
.group-name { margin: 0 0 6px; font-size: 13px; color: var(--text-secondary); font-weight: 600; }
.proposal {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 0; border-bottom: 1px solid var(--border);
}
.proposal-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.proposal-title { font-size: 14px; }
.proposal-due { font-size: 12px; color: var(--primary); }
.proposal-desc {
  font-size: 12px; color: var(--text-muted);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.accept { color: var(--primary); font-weight: 700; }
.empty-state { text-align: center; color: var(--text-secondary); margin-top: 60px; }
.empty-icon { font-size: 32px; }
@media (max-width: 640px) {
  .list-header { padding: 56px 12px 8px; }
  .intro, .group { margin-left: 12px; margin-right: 12px; }
}
</style>
