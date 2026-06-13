import { createRouter, createWebHistory } from 'vue-router'
import { tokens } from '@/api/client'

/**
 * Routes du client web. Les vues de la liste/du détail restent à construire
 * (cf. les `it.todo` « Jalon 1 — cœur web » dans src/spec/acceptance.spec.ts) ;
 * AppView est pour l'instant une coque qui prouve que le shell tourne.
 *
 * Deep link (module 1.2) : /task/:id correspond à app://task/:id côté natif.
 */
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    { path: '/', redirect: '/today' },
    {
      // Smart lists par défaut (module 2.2).
      path: '/:smartList(today|tomorrow|next7|all|completed|inbox)',
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
    { path: '/:pathMatch(.*)*', redirect: '/today' },
  ],
})

router.beforeEach((to) => {
  if (!to.meta.public && !tokens.access) return { name: 'login' }
})
