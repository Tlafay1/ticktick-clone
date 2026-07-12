<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useProjectStore } from '@/stores/projects'
import { useUserStore } from '@/stores/user'
import { useTagStore } from '@/stores/tags'
import { useTaskStore } from '@/stores/tasks'
import { authApi, projectsApi } from '@/api'
import type { Project, ProjectGroup } from '@/types'
import ProjectEditor from './ProjectEditor.vue'
import ProjectContextMenu from './ProjectContextMenu.vue'
import GroupContextMenu from './GroupContextMenu.vue'
import { useDragSort } from '@/composables/useDragSort'
import { useUiState } from '@/composables/useUiState'
import { watch } from 'vue'
import TagManager from './TagManager.vue'
import Icon from './Icon.vue'
import IconRail from './IconRail.vue'
import MiniCalendar from './MiniCalendar.vue'

const router = useRouter()
const route = useRoute()
const { sidebarOpen, toggleSidebar, closeSidebar } = useUiState()
// Referme le tiroir à chaque navigation (mobile).
watch(() => route.fullPath, closeSidebar)
const projectStore = useProjectStore()
const userStore = useUserStore()
const tagStore = useTagStore()
const taskStore = useTaskStore()

onMounted(async () => {
  if (!tagStore.tags.length) await tagStore.load()
  await loadCounts()
})

const ALL_SMART_LISTS = [
  { key: 'today',     label: 'Aujourd\'hui',      icon: 'sun' },
  { key: 'tomorrow',  label: 'Demain',             icon: 'sunrise' },
  { key: 'next7',     label: '7 prochains jours',  icon: 'calendar-days' },
  { key: 'all',       label: 'Toutes',             icon: 'layers' },
  { key: 'inbox',     label: 'Boîte de réception', icon: 'inbox' },
  { key: 'completed', label: 'Terminées',          icon: 'check-circle' },
]

const smartLists = computed(() => {
  const visibility = userStore.user?.settings?.smart_list_visibility ?? {}
  return ALL_SMART_LISTS.filter(sl => visibility[sl.key] !== false)
})

const newListName = ref('')
const showNewList = ref(false)

function isSmartActive(key: string) {
  return route.name === 'smart-list' && route.params.smartList === key
}
function isProjectActive(id: number) {
  return route.name === 'project' && route.params.id === String(id)
}

async function logout() {
  authApi.logout()
  router.push('/login')
}

async function addList() {
  const name = newListName.value.trim()
  if (!name) return
  await projectStore.create(name)
  newListName.value = ''
  showNewList.value = false
}

const userProjects = computed(() =>
  projectStore.projects.filter((p) => !p.is_inbox && !p.archived && !p.is_smart)
)

// Filtres (smart lists personnalisées) : section dédiée, comme TickTick.
const smartProjects = computed(() =>
  projectStore.projects.filter((p) => p.is_smart && !p.archived)
)

// Listes archivées : section repliée en bas, seul accès au désarchivage.
const archivedProjects = computed(() =>
  projectStore.projects.filter((p) => !p.is_inbox && p.archived)
)
const showArchived = ref(false)

// Compteurs de tâches actives (Aujourd'hui / 7 jours / Inbox), comme TickTick.
// Rafraîchis à chaque navigation (léger décalage accepté entre deux vues).
const smartCounts = ref<Record<string, number>>({})
// Compteurs par liste, dérivés d'UNE seule requête « toutes les actives ».
const projectCounts = ref<Record<number, number>>({})

async function loadCounts() {
  const { tasksApi } = await import('@/api')
  try {
    const [today, next7, all] = await Promise.all([
      tasksApi.list({ ...taskStore.smartParams('today'), smart: 1 }),
      tasksApi.list({ ...taskStore.smartParams('next7'), smart: 1 }),
      tasksApi.list({ smart: 1, status: 0 }),
    ])
    const byProject: Record<number, number> = {}
    for (const t of all) byProject[t.project] = (byProject[t.project] ?? 0) + 1
    projectCounts.value = byProject
    smartCounts.value = {
      today: today.length,
      next7: next7.length,
      inbox: projectStore.inbox ? (byProject[projectStore.inbox.id] ?? 0) : 0,
    }
  } catch { /* hors-ligne : on garde les derniers compteurs */ }
}
watch(() => route.fullPath, loadCounts)

const ungroupedProjects = computed(() =>
  userProjects.value.filter((p) => !p.group)
)

function projectsInGroup(groupId: number) {
  return userProjects.value.filter((p) => p.group === groupId)
}

// Repli des dossiers : persisté côté API (ProjectGroup.collapsed).
function isGroupCollapsed(id: number) {
  return projectStore.groups.find((g) => g.id === id)?.collapsed ?? false
}
function toggleGroup(id: number) {
  projectStore.updateGroup(id, { collapsed: !isGroupCollapsed(id) })
}

// Nouveau dossier
const newGroupName = ref('')
const showNewGroup = ref(false)

async function addGroup() {
  const name = newGroupName.value.trim()
  if (!name) return
  await projectStore.createGroup(name)
  newGroupName.value = ''
  showNewGroup.value = false
}

// ── Context menus ────────────────────────────────────────────────────────────

type ContextState =
  | { type: 'project'; target: Project; x: number; y: number }
  | { type: 'group';   target: ProjectGroup; x: number; y: number }
  | null

const contextMenu = ref<ContextState>(null)

function showProjectMenu(e: MouseEvent, p: Project) {
  e.preventDefault()
  contextMenu.value = { type: 'project', target: p, x: e.clientX, y: e.clientY }
}

function showGroupMenu(e: MouseEvent, g: ProjectGroup) {
  e.preventDefault()
  contextMenu.value = { type: 'group', target: g, x: e.clientX, y: e.clientY }
}

// ── Drag projet → dossier ───────────────────────────────────────────────────

const draggingProjectId = ref<number | null>(null)
const groupDropOver = ref<number | null>(null)

function onProjectDragStart(e: DragEvent, p: Project) {
  draggingProjectId.value = p.id
  e.dataTransfer?.setData('text/plain', String(p.id))
}

function onGroupDragOver(e: DragEvent, groupId: number) {
  if (draggingProjectId.value === null) return
  e.preventDefault()
  groupDropOver.value = groupId
}

async function onGroupDrop(groupId: number) {
  const pid = draggingProjectId.value
  draggingProjectId.value = null
  groupDropOver.value = null
  if (pid === null) return
  await projectStore.update(pid, { group: groupId })
}

function onGroupDragLeave() { groupDropOver.value = null }

// ── Tri des projets non groupés ─────────────────────────────────────────────

const editingProject = ref<Project | null>(null)

const { overIdx: listOverIdx, onDragStart: listDragStart, onDragOver: listDragOver, onDrop: listDrop, onDragEnd: listDragEnd } = useDragSort(
  async (from, to) => {
    const list = [...ungroupedProjects.value]
    const [moved] = list.splice(from, 1)
    list.splice(to, 0, moved)
    const updates = list.map((p, i) => ({ id: p.id, sort_order: (i + 1) * 1000 }))
    projectStore.projects = projectStore.projects.map((p) => {
      const u = updates.find((x) => x.id === p.id)
      return u ? { ...p, sort_order: u.sort_order } : p
    })
    await Promise.all(updates.map(({ id, sort_order }) => projectsApi.update(id, { sort_order })))
  }
)

// ── Tags hiérarchiques ───────────────────────────────────────────────────────
const collapsedTags = ref<Record<number, boolean>>({})
function toggleTagCollapse(id: number) {
  collapsedTags.value[id] = !collapsedTags.value[id]
}

// ── Drag tâche → tag ────────────────────────────────────────────────────────
const tagDropOver = ref<number | null>(null)

async function dropTaskOnTag(e: DragEvent, tagId: number) {
  tagDropOver.value = null
  const taskIdStr = e.dataTransfer?.getData('task-id')
  if (!taskIdStr) return
  const taskId = Number(taskIdStr)
  const task = taskStore.tasks.find(t => t.id === taskId)
  if (!task) return
  const currentTags = task.tags ?? []
  if (!currentTags.includes(tagId)) {
    await taskStore.update(taskId, { tags: [...currentTags, tagId] })
  }
}

const showTagManager = ref(false)

const themeIcons: Record<string, string> = { auto: 'monitor', light: 'sun', dark: 'moon' }
const themeOrder: Array<'auto' | 'light' | 'dark'> = ['auto', 'light', 'dark']

function cycleTheme() {
  const idx = themeOrder.indexOf(userStore.theme)
  userStore.setTheme(themeOrder[(idx + 1) % themeOrder.length])
}
</script>

<template>
  <!-- Bouton hamburger (mobile uniquement) -->
  <button class="drawer-toggle" aria-label="Menu" @click="toggleSidebar">☰</button>
  <!-- Voile cliquable pour fermer le tiroir -->
  <div v-if="sidebarOpen" class="drawer-overlay" @click="closeSidebar" />

  <!-- Rail d'icônes (desktop uniquement, comme TickTick) -->
  <IconRail />

  <aside class="sidebar" :class="{ open: sidebarOpen }">
    <div class="sidebar-top">
      <div class="app-title">TickTick</div>
    </div>

    <nav class="nav-section">
      <RouterLink
        v-for="sl in smartLists"
        :key="sl.key"
        :to="`/${sl.key}`"
        class="nav-item"
        :class="{ active: isSmartActive(sl.key) }"
      >
        <span class="nav-icon"><Icon :name="sl.icon" /></span>
        <span class="nav-label">{{ sl.label }}</span>
        <span v-if="smartCounts[sl.key]" class="nav-count">{{ smartCounts[sl.key] }}</span>
      </RouterLink>
    </nav>

    <!-- Outils : sur desktop ils vivent dans le rail d'icônes ; ces entrées
         ne servent qu'au tiroir mobile (rail masqué). -->
    <div class="section-header mobile-only">
      <span>Outils</span>
    </div>
    <nav class="nav-section mobile-only">
      <RouterLink to="/calendar"   class="nav-item"><span class="nav-icon"><Icon name="calendar" /></span><span class="nav-label">Calendrier</span></RouterLink>
      <RouterLink to="/timeline"   class="nav-item"><span class="nav-icon"><Icon name="timeline" /></span><span class="nav-label">Timeline</span></RouterLink>
      <RouterLink to="/eisenhower" class="nav-item"><span class="nav-icon"><Icon name="grid" /></span><span class="nav-label">Eisenhower</span></RouterLink>
      <RouterLink to="/habits"     class="nav-item"><span class="nav-icon"><Icon name="sprout" /></span><span class="nav-label">Habitudes</span></RouterLink>
      <RouterLink to="/focus"      class="nav-item"><span class="nav-icon"><Icon name="timer" /></span><span class="nav-label">Focus</span></RouterLink>
      <RouterLink to="/stats"      class="nav-item"><span class="nav-icon"><Icon name="bar-chart" /></span><span class="nav-label">Statistiques</span></RouterLink>
      <RouterLink to="/countdown"  class="nav-item"><span class="nav-icon"><Icon name="hourglass" /></span><span class="nav-label">Compte à rebours</span></RouterLink>
    </nav>

    <!-- Filtres = smart lists personnalisées (moteur de règles) -->
    <template v-if="smartProjects.length">
      <div class="section-header"><span>Filtres</span></div>
      <nav class="nav-section">
        <div
          v-for="p in smartProjects"
          :key="p.id"
          class="nav-item project-item"
          :class="{ active: isProjectActive(p.id) }"
          @click="router.push(`/project/${p.id}`)"
          @contextmenu.prevent="showProjectMenu($event, p)"
        >
          <span class="nav-icon"><Icon name="filter" /></span>
          <span class="nav-label">{{ p.name }}</span>
          <button class="project-edit-btn icon-btn" @click.stop="showProjectMenu($event, p)"><Icon name="dots" /></button>
        </div>
      </nav>
    </template>

    <div class="section-header">
      <span>Mes listes</span>
      <div style="display:flex;gap:2px">
        <button class="icon-btn" title="Nouveau dossier" @click="showNewGroup = true"><Icon name="folder" :size="14" /></button>
        <button class="icon-btn" title="Nouvelle liste"  @click="showNewList = true"><Icon name="plus" :size="14" /></button>
      </div>
    </div>

    <nav class="nav-section list-nav">

      <!-- ── Dossiers ── -->
      <template v-for="g in projectStore.groups" :key="`g-${g.id}`">
        <div
          class="nav-item group-item"
          :class="{ 'drop-target': groupDropOver === g.id }"
          @click="toggleGroup(g.id)"
          @contextmenu.prevent="showGroupMenu($event, g)"
          @dragover="onGroupDragOver($event, g.id)"
          @drop.prevent="onGroupDrop(g.id)"
          @dragleave="onGroupDragLeave"
        >
          <span class="nav-icon chevron-icon" :class="{ open: !isGroupCollapsed(g.id) }"><Icon name="chevron-right" :size="12" /></span>
          <span class="nav-label">{{ g.name }}</span>
          <span class="group-count">{{ projectsInGroup(g.id).length }}</span>
        </div>
        <template v-if="!isGroupCollapsed(g.id)">
          <div
            v-for="p in projectsInGroup(g.id)"
            :key="p.id"
            class="nav-item project-item group-child"
            :class="{ active: isProjectActive(p.id) }"
            draggable="true"
            @click="router.push(`/project/${p.id}`)"
            @contextmenu.prevent="showProjectMenu($event, p)"
            @dragstart="onProjectDragStart($event, p)"
          >
            <span v-if="!p.icon" class="nav-dot" :style="p.color ? `background:${p.color}` : ''" />
            <span v-if="p.icon" class="nav-icon project-icon">{{ p.icon }}</span>
            <span class="nav-label">{{ p.name }}</span>
            <span v-if="projectCounts[p.id]" class="nav-count">{{ projectCounts[p.id] }}</span>
            <button class="project-edit-btn icon-btn" @click.stop="showProjectMenu($event, p)"><Icon name="dots" :size="14" /></button>
          </div>
        </template>
      </template>

      <!-- ── Nouveau dossier ── -->
      <div v-if="showNewGroup" class="new-list-input">
        <input
          v-model="newGroupName"
          placeholder="Nom du dossier"
          autofocus
          @keydown.enter="addGroup"
          @keydown.escape="showNewGroup = false; newGroupName = ''"
        />
      </div>

      <!-- ── Zone de dépôt "sans dossier" ── -->
      <div
        v-if="draggingProjectId !== null"
        class="drop-no-group"
        :class="{ 'drop-target': groupDropOver === -1 }"
        @dragover.prevent="groupDropOver = -1"
        @drop.prevent="projectStore.update(draggingProjectId!, { group: null }); draggingProjectId = null; groupDropOver = null"
        @dragleave="groupDropOver = null"
      >Déposer ici pour retirer du dossier</div>

      <!-- ── Projets sans dossier (triables) ── -->
      <div
        v-for="(p, idx) in ungroupedProjects"
        :key="p.id"
        class="nav-item project-item"
        :class="{ active: isProjectActive(p.id), 'drag-over': listOverIdx === idx }"
        draggable="true"
        @click="router.push(`/project/${p.id}`)"
        @contextmenu.prevent="showProjectMenu($event, p)"
        @dragstart="(e) => { listDragStart(idx); onProjectDragStart(e, p) }"
        @dragover="listDragOver($event, idx)"
        @drop="listDrop(idx)"
        @dragend="listDragEnd"
      >
        <span v-if="!p.icon" class="nav-dot" :style="p.color ? `background:${p.color}` : ''" />
        <span v-if="p.icon" class="nav-icon project-icon">{{ p.icon }}</span>
        <span class="nav-label">{{ p.name }}</span>
        <span v-if="projectCounts[p.id]" class="nav-count">{{ projectCounts[p.id] }}</span>
        <button class="project-edit-btn icon-btn" @click.stop="showProjectMenu($event, p)"><Icon name="dots" :size="14" /></button>
      </div>

      <!-- Inbox (non triable, non déplaçable) -->
      <template v-if="projectStore.inbox">
        <div
          class="nav-item project-item"
          :class="{ active: isSmartActive('inbox') }"
          @click="router.push('/inbox')"
          @contextmenu.prevent="showProjectMenu($event, projectStore.inbox!)"
        >
          <span class="nav-dot" />
          <span class="nav-icon"><Icon name="inbox" /></span>
          <span class="nav-label">{{ projectStore.inbox.name }}</span>
          <span v-if="smartCounts.inbox" class="nav-count">{{ smartCounts.inbox }}</span>
        </div>
      </template>

      <div v-if="showNewList" class="new-list-input">
        <input
          v-model="newListName"
          placeholder="Nom de la liste"
          autofocus
          @keydown.enter="addList"
          @keydown.escape="showNewList = false; newListName = ''"
        />
      </div>

      <!-- Listes archivées (repliées) : accès au désarchivage -->
      <template v-if="archivedProjects.length">
        <button class="archived-toggle" @click="showArchived = !showArchived">
          {{ showArchived ? '▾' : '▸' }} Archivées ({{ archivedProjects.length }})
        </button>
        <div
          v-for="p in archivedProjects"
          v-show="showArchived"
          :key="p.id"
          class="nav-item project-item archived-item"
          @click="router.push(`/project/${p.id}`)"
          @contextmenu.prevent="showProjectMenu($event, p)"
        >
          <span v-if="!p.icon" class="nav-dot" :style="p.color ? `background:${p.color}` : ''" />
          <span v-if="p.icon" class="nav-icon project-icon">{{ p.icon }}</span>
          <span class="nav-label">{{ p.name }}</span>
          <button class="project-edit-btn icon-btn" @click.stop="showProjectMenu($event, p)"><Icon name="dots" :size="14" /></button>
        </div>
      </template>
    </nav>

    <!-- Section tags hiérarchiques (toujours visible : point d'accès au gestionnaire) -->
    <div class="section-header">
      <span>Étiquettes</span>
      <button class="icon-btn" title="Gérer les étiquettes" @click="showTagManager = true"><Icon name="settings" :size="13" /></button>
    </div>
      <nav class="nav-section">
        <template v-for="tag in tagStore.rootTags" :key="tag.id">
          <div
            class="nav-item tag-item"
            :class="{ active: route.name === 'tag' && route.params.id === String(tag.id), 'drop-target': tagDropOver === tag.id }"
            @click="router.push(`/tag/${tag.id}`)"
            @dragover.prevent="tagDropOver = tag.id"
            @dragleave="tagDropOver = null"
            @drop.prevent="dropTaskOnTag($event, tag.id)"
          >
            <span class="tag-dot" :style="tag.color ? `background:${tag.color}` : ''" />
            <span class="nav-label">#{{ tag.name }}</span>
            <span
              v-if="tagStore.childrenOf(tag.id).length"
              class="tag-chevron"
              @click.stop="toggleTagCollapse(tag.id)"
            ><Icon :name="collapsedTags[tag.id] ? 'chevron-right' : 'chevron-down'" :size="11" /></span>
          </div>
          <template v-if="!collapsedTags[tag.id]">
            <div
              v-for="child in tagStore.childrenOf(tag.id)"
              :key="child.id"
              class="nav-item tag-item tag-child"
              :class="{ active: route.name === 'tag' && route.params.id === String(child.id), 'drop-target': tagDropOver === child.id }"
              @click="router.push(`/tag/${child.id}`)"
              @dragover.prevent="tagDropOver = child.id"
              @dragleave="tagDropOver = null"
              @drop.prevent="dropTaskOnTag($event, child.id)"
            >
              <span class="tag-dot" :style="child.color ? `background:${child.color}` : ''" />
              <span class="nav-label">#{{ child.name }}</span>
            </div>
          </template>
        </template>
      </nav>

    <!-- Tag Manager Modal -->
    <TagManager v-if="showTagManager" @close="showTagManager = false" />

    <!-- Modals & menus -->
    <ProjectEditor
      v-if="editingProject"
      :project="editingProject"
      @close="editingProject = null"
    />

    <ProjectContextMenu
      v-if="contextMenu?.type === 'project'"
      :project="contextMenu.target"
      :x="contextMenu.x"
      :y="contextMenu.y"
      @edit="editingProject = contextMenu.target"
      @close="contextMenu = null"
    />

    <GroupContextMenu
      v-if="contextMenu?.type === 'group'"
      :group="contextMenu.target"
      :x="contextMenu.x"
      :y="contextMenu.y"
      @close="contextMenu = null"
    />

    <div class="sidebar-footer">
      <RouterLink to="/trash" class="nav-item" :class="{ active: isSmartActive('trash') }">
        <span class="nav-icon"><Icon name="trash" /></span>
        <span class="nav-label">Corbeille</span>
      </RouterLink>
      <!-- Sur desktop : réglages/thème/déconnexion vivent dans le rail. -->
      <RouterLink to="/settings" class="nav-item mobile-only">
        <span class="nav-icon"><Icon name="settings" /></span>
        <span class="nav-label">Paramètres</span>
      </RouterLink>
      <div class="sidebar-actions mobile-only">
        <button class="icon-btn theme-btn" :title="`Thème : ${userStore.theme}`" @click="cycleTheme">
          <Icon :name="themeIcons[userStore.theme]" :size="14" />
        </button>
        <button class="nav-item logout-btn" @click="logout">
          <span class="nav-icon">⎋</span>
          <span class="nav-label">Se déconnecter</span>
        </button>
      </div>
      <MiniCalendar class="desktop-only" />
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
}

/* Hamburger + voile : masqués sur desktop, visibles en tiroir sur mobile. */
.drawer-toggle { display: none; }
.drawer-overlay { display: none; }

/* Entrées réservées au tiroir mobile (le rail les porte sur desktop). */
.mobile-only { display: none !important; }
@media (max-width: 768px) {
  .mobile-only { display: flex !important; }
  .desktop-only { display: none !important; }
}

@media (max-width: 768px) {
  .drawer-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    position: fixed;
    top: 8px;
    left: 8px;
    z-index: 1200;
    width: 40px;
    height: 40px;
    font-size: 20px;
    border-radius: 10px;
    background: var(--bg);
    border: 1px solid var(--border);
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.12);
    color: var(--text);
  }
  .drawer-overlay {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 1300;
    background: rgba(0, 0, 0, 0.4);
  }
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    z-index: 1400;
    width: 82vw;
    max-width: 300px;
    min-width: 0;
    transform: translateX(-100%);
    transition: transform 0.25s ease;
    box-shadow: 2px 0 20px rgba(0, 0, 0, 0.18);
  }
  .sidebar.open { transform: translateX(0); }
}

.sidebar-top { padding: 16px 12px 10px; }
.app-title { font-size: 15px; font-weight: 600; color: var(--primary); }

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px 3px;
  font-size: 10.5px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.7px;
  color: var(--text-muted);
}

.nav-section { display: flex; flex-direction: column; padding: 2px 6px; margin-bottom: 4px; }
.list-nav { flex: 1; }

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  color: var(--text);
  text-decoration: none;
  cursor: pointer;
  font-size: 13px;
  border: none;
  background: none;
  width: 100%;
  text-align: left;
}
.nav-item:hover { background: var(--bg-hover); }
.nav-item.active,
.nav-item.router-link-active {
  background: var(--bg-hover);
  color: var(--primary);
  font-weight: 500;
  box-shadow: inset 3px 0 0 var(--primary);
}

.nav-icon {
  width: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
}
.nav-item.active .nav-icon { color: var(--primary); }
.nav-label { flex: 1; }

/* Compteur de tâches à droite (façon TickTick) */
.nav-count {
  font-size: 11px;
  color: var(--text-muted);
  padding-left: 6px;
}

/* Chevron rotatif des dossiers */
.chevron-icon { transition: transform 0.15s; color: var(--text-muted); }
.chevron-icon.open { transform: rotate(90deg); }

.nav-dot {
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--primary); flex-shrink: 0; margin-left: 5px;
}

.project-item { position: relative; }
.project-edit-btn { opacity: 0; margin-left: auto; font-size: 16px; color: var(--text-muted); }
.project-item:hover .project-edit-btn { opacity: 1; }
.project-icon { font-size: 14px; }
.drag-over { border-top: 2px solid var(--primary); }

.group-item {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-muted);
  cursor: pointer;
  user-select: none;
}
.group-count {
  margin-left: auto;
  font-size: 11px;
  background: var(--border);
  border-radius: 8px;
  padding: 1px 5px;
}
.group-child { padding-left: 22px !important; }

.drop-target { background: color-mix(in srgb, var(--accent) 15%, var(--bg-hover)); border-radius: 8px; }

.drop-no-group {
  margin: 2px 4px;
  padding: 4px 10px;
  border: 1px dashed var(--border);
  border-radius: 6px;
  font-size: 11px;
  color: var(--text-muted);
  text-align: center;
}

.archived-toggle {
  display: block;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 11.5px;
  color: var(--text-muted);
  padding: 6px 16px 4px;
}
.archived-toggle:hover { color: var(--text-secondary); }
.archived-item { opacity: 0.55; }
.archived-item:hover { opacity: 0.85; }

.new-list-input { padding: 4px 8px; }
.new-list-input input {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid var(--primary);
  border-radius: 6px;
  background: var(--bg);
  outline: none;
  font-size: 13.5px;
  color: var(--text);
}

.tag-item { font-size: 13px; }
.tag-child { padding-left: 24px !important; }
.tag-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--primary); flex-shrink: 0;
}
.tag-chevron { font-size: 9px; color: var(--text-muted); margin-left: auto; }

.sidebar-footer { margin-top: auto; padding: 8px; border-top: 1px solid var(--border); }
.sidebar-actions { display: flex; align-items: center; gap: 4px; }
.logout-btn { flex: 1; }
.theme-btn { font-size: 16px; flex-shrink: 0; }
</style>
