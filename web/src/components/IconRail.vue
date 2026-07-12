<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { authApi } from '@/api'
import Icon from './Icon.vue'

// Rail d'icônes vertical (double sidebar, comme TickTick desktop).
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const TASK_ROUTES = new Set(['smart-list', 'project', 'tag', 'task', 'kanban'])

const TOP_ITEMS = [
  { key: 'tasks',      icon: 'check-circle', title: 'Tâches',           to: '/today' },
  { key: 'calendar',   icon: 'calendar',     title: 'Calendrier',       to: '/calendar' },
  { key: 'eisenhower', icon: 'grid',         title: 'Matrice Eisenhower', to: '/eisenhower' },
  { key: 'focus',      icon: 'timer',        title: 'Focus',            to: '/focus' },
  { key: 'habits',     icon: 'sprout',       title: 'Habitudes',        to: '/habits' },
  { key: 'timeline',   icon: 'timeline',     title: 'Timeline',         to: '/timeline' },
  { key: 'countdown',  icon: 'hourglass',    title: 'Compte à rebours', to: '/countdown' },
  { key: 'stats',      icon: 'bar-chart',    title: 'Statistiques',     to: '/stats' },
]

const activeKey = computed(() => {
  if (TASK_ROUTES.has(String(route.name))) return 'tasks'
  const path = route.path
  const hit = TOP_ITEMS.find(i => i.key !== 'tasks' && path.startsWith(i.to))
  return hit?.key ?? (path.startsWith('/settings') ? 'settings' : '')
})

const avatarLetter = computed(() =>
  (userStore.user?.email?.[0] ?? '?').toUpperCase()
)

function openSearch() {
  if (!TASK_ROUTES.has(String(route.name))) {
    router.push('/all')
    setTimeout(() => window.dispatchEvent(new CustomEvent('tt:focus-search')), 250)
  } else {
    window.dispatchEvent(new CustomEvent('tt:focus-search'))
  }
}

const themeIcons: Record<string, string> = { auto: 'monitor', light: 'sun', dark: 'moon' }
const themeOrder: Array<'auto' | 'light' | 'dark'> = ['auto', 'light', 'dark']

function cycleTheme() {
  const idx = themeOrder.indexOf(userStore.theme)
  userStore.setTheme(themeOrder[(idx + 1) % themeOrder.length])
}

function logout() {
  authApi.logout()
  router.push('/login')
}
</script>

<template>
  <nav class="icon-rail">
    <button class="rail-avatar" title="Compte & paramètres" @click="router.push('/settings')">
      {{ avatarLetter }}
    </button>

    <button
      v-for="item in TOP_ITEMS"
      :key="item.key"
      class="rail-btn"
      :class="{ active: activeKey === item.key }"
      :title="item.title"
      @click="router.push(item.to)"
    >
      <Icon :name="item.icon" :size="19" />
    </button>

    <button class="rail-btn" title="Rechercher (Ctrl+F)" @click="openSearch">
      <Icon name="search" :size="19" />
    </button>

    <div class="rail-spacer" />

    <button class="rail-btn" :title="`Thème : ${userStore.theme}`" @click="cycleTheme">
      <Icon :name="themeIcons[userStore.theme]" :size="18" />
    </button>
    <button class="rail-btn" :class="{ active: activeKey === 'settings' }" title="Paramètres" @click="router.push('/settings')">
      <Icon name="settings" :size="18" />
    </button>
    <button class="rail-btn" title="Se déconnecter" @click="logout">
      <Icon name="logout" :size="18" />
    </button>
  </nav>
</template>

<style scoped>
.icon-rail {
  width: 46px;
  min-width: 46px;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 10px 0;
  background: var(--bg-rail, var(--bg-sidebar));
  border-right: 1px solid var(--border);
}

.rail-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: none;
  background: var(--primary);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 10px;
  flex-shrink: 0;
}

.rail-btn {
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 8px;
  background: none;
  color: var(--text-muted);
  cursor: pointer;
  flex-shrink: 0;
}
.rail-btn:hover { background: var(--bg-hover); color: var(--text); }
.rail-btn.active { background: var(--primary-soft); color: var(--primary); }

.rail-spacer { flex: 1; }

@media (max-width: 768px) {
  .icon-rail { display: none; }
}
</style>
