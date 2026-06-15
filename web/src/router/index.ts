import { createRouter, createWebHistory } from 'vue-router'
import { tokens } from '@/api/client'
import { routes } from './routes'

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (!to.meta.public && !tokens.access) return { name: 'login' }
})
