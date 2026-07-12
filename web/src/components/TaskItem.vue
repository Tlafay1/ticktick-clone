<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Task } from '@/types'
import { dueLabel, dueTone } from '@/lib/dates'
import { useTaskStore } from '@/stores/tasks'
import { useTagStore } from '@/stores/tags'
import { useProjectStore } from '@/stores/projects'
import TaskContextMenu from './TaskContextMenu.vue'

const props = defineProps<{
  task: Task
  selected?: boolean
  depth?: number
  hasChildren?: boolean
  collapsed?: boolean
}>()
const emit = defineEmits<{ 'toggle-collapse': [] }>()
const store = useTaskStore()
const tagStore = useTagStore()
const projectStore = useProjectStore()

const priorityClass = computed(() => {
  if (props.task.priority === 5) return 'p5'
  if (props.task.priority === 3) return 'p3'
  if (props.task.priority === 1) return 'p1'
  return 'p0'
})

const isCompleted = computed(() => props.task.status === 2)
const isWontDo = computed(() => props.task.status === -1)

const childCounts = computed(() => {
  const children = store.tasks.filter((t) => t.parent === props.task.id)
  return { done: children.filter((c) => c.status === 2).length, total: children.length }
})

const dueTone_ = computed(() => dueTone(props.task.due_date, props.task.is_all_day, props.task.status))
const dueLabel_ = computed(() => dueLabel(props.task.due_date, props.task.is_all_day))

const projectName = computed(() => {
  if (!props.task.project) return ''
  return projectStore.projects.find(p => p.id === props.task.project)?.name ?? ''
})

const visibleTags = computed(() =>
  (props.task.tags ?? []).slice(0, 3).map(id => tagStore.byId(id)).filter(Boolean)
)

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
    :style="depth ? `padding-left: ${14 + depth * 22}px` : ''"
    @click="store.select(task.id)"
    @contextmenu.prevent="openContext"
  >
    <button
      v-if="hasChildren"
      class="collapse-btn"
      :class="{ collapsed }"
      :title="collapsed ? 'Déplier' : 'Replier'"
      @click.stop="emit('toggle-collapse')"
    >
      <svg width="8" height="8" viewBox="0 0 8 8" fill="none"><path d="M2 1L6 4L2 7" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
    </button>
    <button
      class="task-checkbox"
      :class="[priorityClass, { checked: isCompleted, wontdo: isWontDo }]"
      @click.stop="toggleComplete"
      :title="isCompleted ? 'Rouvrir' : 'Terminer'"
    >
      <svg v-if="isCompleted || isWontDo" width="9" height="9" viewBox="0 0 10 10" fill="none">
        <path d="M1.5 5L3.8 7.5L8.5 2.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>

    <div class="task-body">
      <span class="task-title">{{ task.title }}</span>
      <div v-if="task.progress > 0 && !isCompleted && !isWontDo" class="task-progress-bar">
        <div class="task-progress-fill" :style="`width:${task.progress}%`" />
      </div>
      <div v-if="dueLabel_ || childCounts.total || task.check_items?.length" class="task-meta">
        <span v-if="dueLabel_" class="task-due" :class="`due-${dueTone_}`">{{ dueLabel_ }}</span>
        <span v-if="childCounts.total" class="task-checks">↳ {{ childCounts.done }}/{{ childCounts.total }}</span>
        <span v-if="task.check_items?.length" class="task-checks">
          ☑ {{ task.check_items.filter(c => c.is_done).length }}/{{ task.check_items.length }}
        </span>
      </div>
    </div>

    <div v-if="visibleTags.length || projectName" class="task-right">
      <span
        v-for="tag in visibleTags"
        :key="tag!.id"
        class="tag-pill"
        :style="tag!.color ? `background:${tag!.color}1a;color:${tag!.color}` : ''"
      >{{ tag!.name }}</span>
      <span v-if="projectName" class="task-list-name">{{ projectName }}</span>
    </div>
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
  align-items: center;
  gap: 10px;
  padding: 7px 14px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.1s;
  margin: 1px 0;
}
.task-row:hover { background: var(--bg-hover); }

.collapse-btn {
  width: 16px;
  height: 16px;
  margin-left: -6px;
  margin-right: -4px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  transform: rotate(90deg);
  transition: transform 0.15s;
}
.collapse-btn.collapsed { transform: rotate(0deg); }
.collapse-btn:hover { color: var(--text); }
.task-row.selected { background: var(--bg-hover); box-shadow: inset 3px 0 0 var(--primary); }
.task-row.completed .task-title { text-decoration: line-through; color: var(--text-muted); }
.task-row.wont-do .task-title { text-decoration: line-through; color: var(--text-muted); opacity: 0.6; }

.task-body { flex: 1; min-width: 0; }
.task-title { font-size: 13.5px; display: block; line-height: 1.4; }
.task-meta { display: flex; gap: 8px; margin-top: 2px; }

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
.task-due { font-size: 11px; }
.due-overdue { color: var(--danger); }
.due-today { color: var(--primary); }
.due-future { color: var(--text-muted); }
.due-muted { color: var(--text-muted); }

.task-right {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  max-width: 200px;
}

.tag-pill {
  display: inline-block;
  padding: 1px 7px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
  background: var(--bg-hover);
  color: var(--text-secondary);
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-list-name {
  font-size: 11px;
  color: var(--text-muted);
  max-width: 70px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
