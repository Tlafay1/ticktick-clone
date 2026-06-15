import type { RouteRecordRaw } from 'vue-router'

export const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  { path: '/', redirect: '/today' },
  {
    path: '/:smartList(today|tomorrow|next7|all|completed|inbox|trash)',
    name: 'smart-list',
    component: () => import('@/views/AppView.vue'),
  },
  {
    path: '/project/:id',
    name: 'project',
    component: () => import('@/views/AppView.vue'),
  },
  {
    path: '/task/:id',
    name: 'task',
    component: () => import('@/views/AppView.vue'),
  },
  {
    path: '/tag/:id',
    name: 'tag',
    component: () => import('@/views/AppView.vue'),
  },
  { path: '/habits',    name: 'habits',     component: () => import('@/views/HabitsView.vue') },
  { path: '/focus',     name: 'focus',      component: () => import('@/views/FocusView.vue') },
  { path: '/stats',     name: 'stats',      component: () => import('@/views/StatsView.vue') },
  { path: '/countdown', name: 'countdown',  component: () => import('@/views/CountdownView.vue') },
  { path: '/settings',  name: 'settings',   component: () => import('@/views/SettingsView.vue') },
  { path: '/calendar',  name: 'calendar',   component: () => import('@/views/CalendarView.vue') },
  { path: '/timeline',  name: 'timeline',   component: () => import('@/views/TimelineView.vue') },
  { path: '/eisenhower',name: 'eisenhower', component: () => import('@/views/EisenhowerView.vue') },
  {
    path: '/project/:id/kanban',
    name: 'kanban',
    component: () => import('@/views/KanbanView.vue'),
  },
  { path: '/:pathMatch(.*)*', redirect: '/today' },
]
