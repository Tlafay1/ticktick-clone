<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useTaskStore } from '@/stores/tasks'
import { useTagStore } from '@/stores/tags'
import { checkItemsApi, commentsApi, tasksApi } from '@/api'
import type { CheckItem, Comment, ActivityEntry, Task } from '@/types'
import { renderMarkdown, toggleMarkdownCheckbox } from '@/lib/markdown'
import { toLocalInput } from '@/lib/dates'
import RecurrenceEditor from './RecurrenceEditor.vue'
import ReminderEditor from './ReminderEditor.vue'
import AttachmentsPanel from './AttachmentsPanel.vue'
import VersionHistory from './VersionHistory.vue'
import TemplateManager from './TemplateManager.vue'

const taskStore = useTaskStore()
const tagStore = useTagStore()

const task = computed(() => taskStore.selected())

const editingTitle = ref(false)
const titleDraft = ref('')
const descDraft = ref('')
const editingDesc = ref(false)
const checkItems = ref<CheckItem[]>([])
const newItemTitle = ref('')
const subtasks = ref<Task[]>([])
const newSubtaskTitle = ref('')
const comments = ref<Comment[]>([])
const newComment = ref('')
const loadingComments = ref(false)
const showTagPicker = ref(false)
const newTagName = ref('')
const showRecurrence = ref(false)
const showReminders = ref(false)
const showActivity = ref(false)
const activity = ref<ActivityEntry[]>([])

watch(task, async (t) => {
  if (t) {
    titleDraft.value = t.title
    descDraft.value = t.description
    checkItems.value = [...t.check_items]
    showTagPicker.value = false
    subtasks.value = await tasksApi.list({ parent: t.id })
    loadingComments.value = true
    try {
      comments.value = await commentsApi.list(t.id)
    } finally {
      loadingComments.value = false
    }
  }
}, { immediate: true })

async function saveTitle() {
  if (!task.value) return
  editingTitle.value = false
  if (titleDraft.value.trim() === task.value.title) return
  await taskStore.update(task.value.id, { title: titleDraft.value.trim() })
}

async function saveDesc() {
  if (!task.value) return
  editingDesc.value = false
  if (descDraft.value === task.value.description) return
  await taskStore.update(task.value.id, { description: descDraft.value })
}

async function setDateField(field: 'due_date' | 'start_date', e: Event) {
  if (!task.value) return
  const val = (e.target as HTMLInputElement).value
  const update: Record<string, unknown> = { [field]: val ? new Date(val).toISOString() : null }
  if (field === 'due_date') {
    // Toute heure autre que minuit → is_all_day: false
    update.is_all_day = !val || val.endsWith('T00:00')
  }
  await taskStore.update(task.value.id, update)
}

async function setPriority(p: number) {
  if (!task.value) return
  await taskStore.update(task.value.id, { priority: p })
}

async function togglePin() {
  if (!task.value) return
  await taskStore.update(task.value.id, { is_pinned: !task.value.is_pinned })
}

async function addCheckItem() {
  if (!task.value || !newItemTitle.value.trim()) return
  const item = await checkItemsApi.create({ task: task.value.id, title: newItemTitle.value.trim() })
  checkItems.value.push(item)
  newItemTitle.value = ''
}

async function toggleCheckItem(item: CheckItem) {
  const updated = await checkItemsApi.update(item.id, { is_done: !item.is_done })
  const idx = checkItems.value.findIndex((x) => x.id === item.id)
  if (idx >= 0) checkItems.value[idx] = updated
  if (updated.is_done) {
    // Déplace l'item coché vers le bas après l'animation
    setTimeout(() => {
      checkItems.value = [
        ...checkItems.value.filter(x => !x.is_done),
        ...checkItems.value.filter(x => x.is_done),
      ]
    }, 500)
  }
}

async function removeCheckItem(item: CheckItem) {
  await checkItemsApi.remove(item.id)
  checkItems.value = checkItems.value.filter((x) => x.id !== item.id)
}

async function trashTask() {
  if (!task.value) return
  await taskStore.remove(task.value.id)
}

// ----- Sous-tâches (Task.parent, Tier 1) -----

async function addSubtask() {
  if (!task.value || !newSubtaskTitle.value.trim()) return
  const child = await tasksApi.create({
    title: newSubtaskTitle.value.trim(),
    parent: task.value.id,
    project: task.value.project,
  })
  subtasks.value.push(child)
  newSubtaskTitle.value = ''
}

async function toggleSubtask(child: Task) {
  const updated = child.status === 2
    ? await tasksApi.reopen(child.id)
    : await tasksApi.complete(child.id)
  const idx = subtasks.value.findIndex((x) => x.id === child.id)
  if (idx >= 0) subtasks.value[idx] = updated
}

async function removeSubtask(child: Task) {
  await tasksApi.remove(child.id)
  subtasks.value = subtasks.value.filter((x) => x.id !== child.id)
}

function openSubtask(child: Task) {
  // Charge l'enfant dans la liste si absent, puis le sélectionne.
  if (!taskStore.tasks.find((t) => t.id === child.id)) taskStore.tasks.push(child)
  taskStore.select(child.id)
}

async function toggleTag(tagId: number) {
  if (!task.value) return
  const current = task.value.tags ?? []
  const next = current.includes(tagId)
    ? current.filter((id) => id !== tagId)
    : [...current, tagId]
  await taskStore.update(task.value.id, { tags: next })
}

async function createAndAddTag() {
  const name = newTagName.value.trim()
  if (!name || !task.value) return
  const tag = await tagStore.create(name, '')
  await toggleTag(tag.id)
  newTagName.value = ''
}

onMounted(async () => {
  if (!tagStore.tags.length) await tagStore.load()
})

async function postComment() {
  if (!task.value || !newComment.value.trim()) return
  const c = await commentsApi.create(task.value.id, newComment.value.trim())
  comments.value.push(c)
  newComment.value = ''
}

async function deleteComment(c: Comment) {
  await commentsApi.remove(c.id)
  comments.value = comments.value.filter((x) => x.id !== c.id)
}

async function loadActivity() {
  if (!task.value) return
  activity.value = await tasksApi.activity(task.value.id)
  showActivity.value = true
}

const descHtml = computed(() => task.value ? renderMarkdown(task.value.description) : '')

async function onDescClick(e: MouseEvent) {
  if (!task.value) return
  const target = e.target as HTMLElement
  if (target.tagName === 'INPUT' && target.getAttribute('type') === 'checkbox') {
    e.preventDefault()
    // Compter l'index de cette checkbox dans le rendu
    const container = target.closest('.md-body')
    if (!container) return
    const boxes = container.querySelectorAll('input[type="checkbox"]')
    const idx = Array.from(boxes).indexOf(target as HTMLInputElement)
    if (idx < 0) return
    const newDesc = toggleMarkdownCheckbox(task.value.description, idx)
    await taskStore.update(task.value.id, { description: newDesc })
  }
}

const priorityOptions = [
  { value: 5, label: '🔴 Haute',   color: 'var(--prio-high)' },
  { value: 3, label: '🟡 Moyenne', color: 'var(--prio-medium)' },
  { value: 1, label: '🔵 Basse',   color: 'var(--prio-low)' },
  { value: 0, label: '⬜ Aucune',  color: 'var(--prio-none)' },
]

function priorityColor(p: number) {
  return priorityOptions.find((x) => x.value === p)?.color ?? 'var(--prio-none)'
}

function formatCommentDate(iso: string) {
  return new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <aside v-if="task" class="detail-panel">
    <!-- En-tête -->
    <div class="detail-header">
      <button class="close-btn icon-btn" @click="taskStore.select(null)">✕</button>
    </div>

    <!-- Titre -->
    <div class="detail-section">
      <div v-if="!editingTitle" class="detail-title" @click="editingTitle = true">
        {{ task.title }}
      </div>
      <input
        v-else
        v-model="titleDraft"
        class="title-input"
        autofocus
        @blur="saveTitle"
        @keydown.enter="saveTitle"
        @keydown.escape="editingTitle = false; titleDraft = task.title"
      />
    </div>

    <!-- Actions rapides -->
    <div class="detail-actions">
      <button
        class="action-chip"
        :class="{ pinned: task.is_pinned }"
        @click="togglePin"
      >📌 {{ task.is_pinned ? 'Épinglée' : 'Épingler' }}</button>

      <button
        v-if="task.status === 0"
        class="action-chip primary"
        @click="taskStore.complete(task.id)"
      >✓ Terminer</button>
      <button
        v-else-if="task.status === 2"
        class="action-chip"
        @click="taskStore.reopen(task.id)"
      >↩ Rouvrir</button>
      <button
        v-else
        class="action-chip"
        @click="taskStore.reopen(task.id)"
      >↩ Rouvrir (Won't Do)</button>

      <button class="action-chip danger" @click="trashTask">🗑 Supprimer</button>
    </div>

    <!-- Dates -->
    <div class="detail-field">
      <div class="dates-grid">
        <div class="date-row">
          <label class="field-label-sm">📅 Planifiée</label>
          <input type="datetime-local" class="field-input" :value="toLocalInput(task.start_date)" @change="setDateField('start_date', $event)" />
        </div>
        <div class="date-row">
          <label class="field-label-sm">⏰ Deadline</label>
          <input type="datetime-local" class="field-input" :value="toLocalInput(task.due_date)" @change="setDateField('due_date', $event)" />
        </div>
      </div>
    </div>

    <!-- Priorité -->
    <div class="detail-field">
      <label class="field-label">
        <span :style="`color: ${priorityColor(task.priority)}`">⚑</span>
        Priorité
      </label>
      <div class="priority-selector">
        <button
          v-for="opt in priorityOptions"
          :key="opt.value"
          class="prio-btn"
          :class="{ active: task.priority === opt.value }"
          :style="`--c: ${opt.color}`"
          @click="setPriority(opt.value)"
        >{{ opt.label }}</button>
      </div>
    </div>

    <!-- Progression + Estimation Pomodoro -->
    <div class="detail-field" v-if="task.progress > 0 || true">
      <label class="field-label">📊 Progression — {{ task.progress }}%</label>
      <input
        type="range"
        min="0" max="100" step="5"
        :value="task.progress"
        class="progress-range"
        @change="taskStore.update(task.id, { progress: Number(($event.target as HTMLInputElement).value) })"
      />
    </div>
    <div class="detail-field pomo-field">
      <label class="field-label-sm">🍅 Pomos estimés</label>
      <input
        type="number"
        class="field-input pomo-input"
        min="0" max="99"
        :value="task.estimated_pomos || 0"
        @change="taskStore.update(task.id, { estimated_pomos: Number(($event.target as HTMLInputElement).value) })"
      />
    </div>

    <!-- Tags -->
    <div class="detail-field">
      <label class="field-label">🏷 Tags</label>
      <div class="tags-row">
        <span
          v-for="tagId in task.tags"
          :key="tagId"
          class="tag-chip"
          :style="tagStore.byId(tagId)?.color ? `background: ${tagStore.byId(tagId)!.color}22; color: ${tagStore.byId(tagId)!.color}` : ''"
          @click="toggleTag(tagId)"
        >
          #{{ tagStore.byId(tagId)?.name ?? tagId }} ✕
        </span>
        <button class="tag-add-btn" @click="showTagPicker = !showTagPicker">＋ Tag</button>
      </div>
      <div v-if="showTagPicker" class="tag-picker">
        <button
          v-for="tag in tagStore.tags"
          :key="tag.id"
          class="tag-option"
          :class="{ selected: task.tags?.includes(tag.id) }"
          :style="tag.color ? `border-color: ${tag.color}` : ''"
          @click="toggleTag(tag.id)"
        >
          #{{ tag.name }}
        </button>
        <div v-if="tagStore.tags.length === 0" class="empty-hint">Aucun tag — créez-en un :</div>
        <div class="tag-create-row">
          <input
            v-model="newTagName"
            class="tag-create-input"
            placeholder="Nouveau tag…"
            @keydown.enter="createAndAddTag"
            @keydown.escape="showTagPicker = false"
          />
          <button class="btn btn-primary tag-create-btn" :disabled="!newTagName.trim()" @click="createAndAddTag">＋</button>
        </div>
      </div>
    </div>

    <!-- Récurrence -->
    <div class="detail-field">
      <button class="collapsible-label" @click="showRecurrence = !showRecurrence">
        <span class="field-label">🔄 Récurrence</span>
        <span v-if="task.rrule" class="rrule-badge">{{ task.rrule.replace('RRULE:', '').split(';')[0] }}</span>
        <span class="chevron">{{ showRecurrence ? '▲' : '▼' }}</span>
      </button>
      <RecurrenceEditor
        v-if="showRecurrence"
        :model-value="task.rrule"
        :repeat-from="task.repeat_from"
        @update:model-value="taskStore.update(task.id, { rrule: $event })"
        @update:repeat-from="taskStore.update(task.id, { repeat_from: $event })"
      />
    </div>

    <!-- Rappels -->
    <div class="detail-field">
      <button class="collapsible-label" @click="showReminders = !showReminders">
        <span class="field-label">🔔 Rappels</span>
        <span class="chevron">{{ showReminders ? '▲' : '▼' }}</span>
      </button>
      <ReminderEditor v-if="showReminders" :task-id="task.id" />
    </div>

    <!-- Description -->
    <div class="detail-field">
      <label class="field-label">📝 Note</label>
      <div
        v-if="!editingDesc"
        class="desc-display"
        :class="{ empty: !task.description }"
        @click.prevent="(e) => { const t = e.target as HTMLElement; if (t.tagName !== 'INPUT') { editingDesc = true; descDraft = task!.description } else { onDescClick(e) } }"
      >
        <div v-if="task.description" class="md-body" v-html="descHtml" />
        <span v-else class="empty-hint">Ajouter une note…</span>
      </div>
      <textarea
        v-else
        v-model="descDraft"
        class="desc-input"
        rows="6"
        autofocus
        placeholder="Markdown supporté…"
        @blur="saveDesc"
      />
    </div>

    <!-- Pièces jointes -->
    <div class="detail-field">
      <AttachmentsPanel :task-id="task.id" />
    </div>

    <!-- Historique des versions -->
    <div class="detail-field">
      <VersionHistory
        :task-id="task.id"
        @restored="(desc) => { descDraft = desc; taskStore.update(task!.id, { description: desc }) }"
      />
    </div>

    <!-- Templates -->
    <div class="detail-field">
      <TemplateManager :task="task" />
    </div>

    <!-- Sous-tâches (Tier 1) -->
    <div class="detail-field">
      <label class="field-label">↳ Sous-tâches <span v-if="subtasks.length" class="count-badge">{{ subtasks.filter(s => s.status === 2).length }}/{{ subtasks.length }}</span></label>
      <div class="subtasks">
        <div
          v-for="child in subtasks"
          :key="child.id"
          class="subtask-item"
          :class="{ done: child.status === 2 }"
        >
          <span
            class="task-checkbox"
            :class="[`p${child.priority}`, { checked: child.status === 2 }]"
            @click="toggleSubtask(child)"
          >
            <svg v-if="child.status === 2" width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M1.5 5L3.8 7.5L8.5 2.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
          <span class="subtask-title" @click="openSubtask(child)">{{ child.title }}</span>
          <button class="remove-item icon-btn" @click="removeSubtask(child)">✕</button>
        </div>
        <div class="check-item new-item">
          <input
            v-model="newSubtaskTitle"
            placeholder="Ajouter une sous-tâche"
            @keydown.enter="addSubtask"
          />
        </div>
      </div>
    </div>

    <!-- Check items -->
    <div class="detail-field">
      <label class="field-label">☑ Checklist</label>
      <div class="checklist">
        <TransitionGroup name="check-sort" tag="div">
          <div
            v-for="item in checkItems"
            :key="item.id"
            class="check-item"
            :class="{ done: item.is_done }"
          >
            <input
              type="checkbox"
              :checked="item.is_done"
              @change="toggleCheckItem(item)"
            />
            <span class="check-title">{{ item.title }}</span>
            <button class="remove-item icon-btn" @click="removeCheckItem(item)">✕</button>
          </div>
        </TransitionGroup>
        <div class="check-item new-item">
          <input
            v-model="newItemTitle"
            placeholder="Ajouter un élément"
            @keydown.enter="addCheckItem"
          />
        </div>
      </div>
    </div>

    <!-- Commentaires -->
    <div class="detail-field">
      <label class="field-label">💬 Commentaires</label>
      <div class="comments">
        <div v-for="c in comments" :key="c.id" class="comment">
          <div class="comment-body">
            <span class="comment-text">{{ c.content }}</span>
            <span v-if="c.edited_at" class="comment-edited">(modifié)</span>
          </div>
          <div class="comment-footer">
            <span class="comment-date">{{ formatCommentDate(c.created_at) }}</span>
            <button class="icon-btn comment-del" @click="deleteComment(c)">✕</button>
          </div>
        </div>
        <div v-if="loadingComments" class="comment-loading">Chargement…</div>
        <div class="comment-new">
          <input
            v-model="newComment"
            placeholder="Ajouter un commentaire…"
            @keydown.enter="postComment"
          />
        </div>
      </div>
    </div>
    <!-- Journal d'activité -->
    <div class="detail-field">
      <button class="collapsible-label" @click="showActivity ? showActivity = false : loadActivity()">
        <span class="field-label">📋 Activité</span>
        <span class="chevron">{{ showActivity ? '▲' : '▼' }}</span>
      </button>
      <div v-if="showActivity" class="activity-list">
        <div v-for="a in activity" :key="a.id" class="activity-item">
          <span class="activity-action">{{ a.action }}</span>
          <span class="activity-date">{{ formatCommentDate(a.created_at) }}</span>
        </div>
        <div v-if="activity.length === 0" class="empty-hint">Aucune activité</div>
      </div>
    </div>
  </aside>

  <aside v-else class="detail-empty">
    <p>Sélectionnez une tâche</p>
  </aside>
</template>

<style scoped>
.detail-panel, .detail-empty {
  width: var(--detail-width);
  min-width: var(--detail-width);
  border-left: 1px solid var(--border);
  height: 100%;
  overflow-y: auto;
  background: var(--bg);
}
.detail-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

/* Mobile : le détail passe en plein écran ; le placeholder « vide » disparaît. */
@media (max-width: 768px) {
  .detail-empty { display: none; }
  .detail-panel {
    position: fixed;
    inset: 0;
    z-index: 1500;
    width: 100%;
    min-width: 0;
    border-left: none;
  }
}

.detail-header {
  display: flex;
  justify-content: flex-end;
  padding: 12px 12px 0;
}
.close-btn { color: var(--text-muted); }

.detail-section { padding: 4px 20px 0; }
.detail-title {
  font-size: 18px;
  font-weight: 600;
  cursor: pointer;
  line-height: 1.3;
  padding: 4px 0;
}
.detail-title:hover { color: var(--primary); }
.title-input {
  font-size: 18px;
  font-weight: 600;
  border: none;
  border-bottom: 2px solid var(--primary);
  outline: none;
  width: 100%;
  padding: 4px 0;
  background: none;
}

.detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 12px 20px;
}
.action-chip {
  font-size: 12px;
  padding: 5px 10px;
  border-radius: 20px;
  border: 1px solid var(--border);
  background: none;
  cursor: pointer;
  color: var(--text-secondary);
}
.action-chip:hover { background: var(--bg-hover); }
.action-chip.pinned { background: var(--primary-soft); color: var(--primary); border-color: var(--primary); }
.action-chip.primary { background: var(--primary); color: #fff; border-color: var(--primary); }
.action-chip.danger { color: var(--danger); border-color: var(--danger); }
.action-chip.danger:hover { background: var(--bg-hover); }

.detail-field { padding: 10px 20px; }
.field-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  margin-bottom: 6px;
  display: block;
}
.field-input {
  padding: 6px 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  font-size: 14px;
  color: var(--text);
}

.dates-grid { display: flex; flex-direction: column; gap: 6px; }
.date-row { display: flex; align-items: center; gap: 8px; }
.field-label-sm {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  white-space: nowrap;
  min-width: 90px;
}

.priority-selector { display: flex; gap: 4px; flex-wrap: wrap; }
.prio-btn {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: none;
  cursor: pointer;
  color: var(--text-secondary);
}
.prio-btn:hover, .prio-btn.active { background: var(--c); color: #fff; border-color: var(--c); }

/* Tags */
.tags-row { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.tag-chip {
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 12px;
  background: var(--primary-soft);
  color: var(--primary);
  cursor: pointer;
  border: none;
}
.tag-chip:hover { opacity: 0.8; }
.tag-add-btn {
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 12px;
  border: 1px dashed var(--border);
  color: var(--text-muted);
  cursor: pointer;
  background: none;
}
.tag-add-btn:hover { border-color: var(--primary); color: var(--primary); }
.tag-picker {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px;
  background: var(--bg-hover);
  border-radius: 8px;
}
.tag-option {
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: none;
  cursor: pointer;
  color: var(--text-secondary);
}
.tag-option:hover { border-color: var(--primary); color: var(--primary); }
.tag-option.selected { background: var(--primary-soft); color: var(--primary); border-color: var(--primary); }

/* Description */
.desc-display {
  min-height: 60px;
  cursor: pointer;
  padding: 6px 8px;
  border: 1px solid transparent;
  border-radius: 6px;
}
.desc-display:hover { border-color: var(--border); }
.empty-hint { color: var(--text-muted); font-size: 13px; }
.tag-create-row { display: flex; gap: 6px; margin-top: 6px; }
.tag-create-input {
  flex: 1; padding: 4px 8px; border: 1px solid var(--border);
  border-radius: 6px; font-size: 13px; background: var(--bg); color: var(--text);
  outline: none;
}
.tag-create-input:focus { border-color: var(--primary); }
.tag-create-btn { padding: 4px 10px; font-size: 14px; }
.desc-input {
  width: 100%;
  padding: 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 13px;
  font-family: monospace;
  resize: vertical;
  background: none;
  outline: none;
  color: var(--text);
}

/* Sous-tâches */
.subtasks { display: flex; flex-direction: column; gap: 2px; }
.subtask-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 0;
}
.subtask-item .task-checkbox { width: 16px; height: 16px; cursor: pointer; }
.subtask-title { flex: 1; font-size: 13.5px; cursor: pointer; }
.subtask-title:hover { color: var(--primary); }
.subtask-item.done .subtask-title { text-decoration: line-through; color: var(--text-muted); }
.subtask-item .remove-item { opacity: 0; }
.subtask-item:hover .remove-item { opacity: 1; }
.count-badge {
  font-size: 10px;
  background: var(--bg-hover);
  color: var(--text-secondary);
  border-radius: 8px;
  padding: 1px 6px;
  margin-left: 4px;
}

/* Checklist */
.checklist { display: flex; flex-direction: column; gap: 4px; }
.check-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  transition: opacity 0.3s;
}
.check-item.done .check-title {
  text-decoration: line-through;
  color: var(--text-muted);
}

/* Animation tri automatique des check items cochés */
.check-sort-move { transition: transform 0.4s ease; }
.check-sort-enter-active { transition: opacity 0.3s, transform 0.3s; }
.check-sort-leave-active { transition: opacity 0.2s; position: absolute; }
.check-sort-enter-from { opacity: 0; transform: translateY(-4px); }
.check-sort-leave-to { opacity: 0; }
.check-title { flex: 1; font-size: 13.5px; }
.remove-item { opacity: 0; }
.check-item:hover .remove-item { opacity: 1; }
.new-item input {
  flex: 1;
  border: none;
  border-bottom: 1px solid var(--border);
  padding: 4px 0;
  outline: none;
  font-size: 13.5px;
  background: none;
  color: var(--text);
}

/* Récurrence / collapsible */
.collapsible-label {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  margin-bottom: 6px;
}
.collapsible-label .field-label { margin-bottom: 0; }
.chevron { margin-left: auto; font-size: 10px; color: var(--text-muted); }
.rrule-badge {
  font-size: 10px;
  background: var(--primary-soft);
  color: var(--primary);
  border-radius: 4px;
  padding: 1px 5px;
  font-family: monospace;
}

/* Commentaires */
.comments { display: flex; flex-direction: column; gap: 8px; }
.comment {
  background: var(--bg-hover);
  border-radius: 8px;
  padding: 8px 10px;
}
.comment-body { font-size: 13.5px; line-height: 1.5; }
.comment-edited { font-size: 11px; color: var(--text-muted); margin-left: 4px; }
.comment-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
}
.comment-date { font-size: 11px; color: var(--text-muted); }
.comment-del { opacity: 0; }
.comment:hover .comment-del { opacity: 1; }
.comment-loading { font-size: 13px; color: var(--text-muted); }
.comment-new input {
  width: 100%;
  border: none;
  border-bottom: 1px solid var(--border);
  padding: 6px 0;
  outline: none;
  font-size: 13.5px;
  background: none;
  color: var(--text);
}
.comment-new input:focus { border-bottom-color: var(--primary); }

.activity-list { display: flex; flex-direction: column; gap: 4px; }
.activity-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-secondary);
  padding: 3px 0;
  border-bottom: 1px solid var(--border);
}
.activity-action { flex: 1; }
.activity-date { color: var(--text-muted); flex-shrink: 0; margin-left: 8px; }

.progress-range {
  width: 100%;
  accent-color: var(--primary);
  cursor: pointer;
}
.pomo-field { display: flex; align-items: center; gap: 8px; padding-top: 0; }
.pomo-input { width: 64px; text-align: center; }
</style>
