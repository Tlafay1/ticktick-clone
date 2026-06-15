import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'
import './styles/main.css'

createApp(App).use(createPinia()).use(router).mount('#app')

// Enregistre le service worker (PWA installable + réception Web Push).
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {})
  })
}
