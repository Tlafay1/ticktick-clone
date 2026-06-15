<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Task } from '@/types'
import { dueLabel, dueTone } from '@/lib/dates'
import { useTaskStore } from '@/stores/tasks'
import { useTagStore } from '@/stores/tags'
import TaskContextMenu from './TaskContextMenu.vue'

const props = defineProps<{ task: Task; selected?: boolean }>()
const store = useTaskStore()
const tagStore = useTagStore()

const priorityClass = computed(() => {
  if (props.task.priority === 5) return 'p5'
  if (props.task.priority === 3) return 'p3'
  if (props.task.priority === 1) return 'p1'
  return 'p0'
})

const isCompleted = computed(() => props.task.status === 2)
const isWontDo = computed(() => props.task.status === -1)

// Compteur de sous-tâches parmi les tâches déjà chargées.
const childCounts = computed(() => {
  const children = store.tasks.filter((t) => t.parent === props.task.id)
  return { done: children.filter((c) => c.status === 2).length, total: children.length }
})

const dueTone_ = computed(() => dueTone(props.task.due_date, props.task.is_all_day, props.task.status))
const dueLabel_ = computed(() => dueLabel(props.task.due_date, props.task.is_all_day))

function toggleComplete() {
  if (isCompleted.value) {
    store.reopen(props.task.id)
  } else {
    store.complete(props.task.id)
  }
}

const ctx = ref<{ x: number; y: number } | null>(null)

function openContext(e: MouseEvent) {
  e.preventDefault()
  ctx.value = { x: e.clientX, y: e.clientY }
}
</script>

<template>
  <div
    class="task-row"
    :class="{ selected, completed: isCompleted, 'wont-do': isWontDo }"
    @click="store.select(task.id)"
    @contextmenu.prevent="openContext"
  >
    <button
      class="task-checkbox"
      :class="[priorityClass, { checked: isCompleted, wontdo: isWontDo }]"
      @click.stop="toggleComplete"
      :title="isCompleted ? 'Rouvrir' : 'Terminer'"
    >
      <svg v-if="isCompleted || isWontDo" width="10" height="10" viewBox="0 0 10 10" fill="none">
        <path d="M1.5 5L3.8 7.5L8.5 2.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>

    <div class="task-body">
      <span class="task-title">{{ task.title }}</span>
      <div v-if="task.progress > 0" class="task-progress-bar">
        <div class="task-progress-fill" :style="`width:${task.progress}%`" />
      </div>
      <div v-if="dueLabel_ || task.check_items?.length || childCounts.total || task.tags?.length" class="task-meta">
        <span v-if="dueLabel_" class="task-due" :class="`due-${dueTone_}`">{{ dueLabel_ }}</span>
        <span v-if="childCounts.total" class="task-checks">↳ {{ childCounts.done }}/{{ childCounts.total }}</span>
        <span v-if="task.check_items?.length" class="task-checks">
          ☑ {{ task.check_items.filter(c => c.is_done).length }}/{{ task.check_items.length }}
        </span>
        <span v-if="task.tags?.length" class="task-tags">
          <span
            v-for="tagId in task.tags.slice(0, 4)"
            :key="tagId"
            class="task-tag-dot"
            :title="tagStore.byId(tagId)?.name"
            :style="tagStore.byId(tagId)?.color ? `background:${tagStore.byId(tagId)!.color}` : ''"
          />
        </span>
      </div>
    </div>

    <div v-if="task.is_pinned" class="task-pin" title="Épinglée">📌</div>
  </div>

  <TaskContextMenu
    v-if="ctx"
    :task="task"
    :x="ctx.x"
    :y="ctx.y"
    @close="ctx = null"
  />
</template>

<style scoped>
.task-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.1s;
  margin: 1px 0;
}
.task-row:hover { background: var(--bg-hover); }
.task-row.selected { background: var(--bg-active); }
.task-row.completed .task-title { text-decoration: line-through; color: var(--text-muted); }
.task-row.wont-do .task-title { text-decoration: line-through; color: var(--text-muted); opacity: 0.7; }

.task-body { flex: 1; min-width: 0; padding-top: 1px; }
.task-title { font-size: 14px; display: block; }
.task-meta { display: flex; gap: 8px; margin-top: 3px; }

.task-progress-bar {
  height: 3px;
  background: var(--border);
  border-radius: 2px;
  margin: 4px 0 2px;
  overflow: hidden;
}
.task-progress-fill {
  height: 100%;
  background: var(--primary);
  border-radius: 2px;
  transition: width 0.3s;
}
.task-checks { font-size: 11px; color: var(--text-muted); }
.task-tags { display: flex; gap: 3px; align-items: center; }
.task-tag-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--primary); flex-shrink: 0;
  opacity: 0.8;
}
.task-due { font-size: 12px; }
.due-overdue { color: var(--danger); }
.due-today { color: var(--primary); }
.due-future { color: var(--text-muted); }
.due-muted { color: var(--text-muted); }

.task-pin { font-size: 12px; }
</style>
