import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'
import './styles/main.css'

// Applique le thème mis en cache AVANT le montage : évite le flash light
// au refresh sur n'importe quelle route (le réglage serveur reprend la main
// dès que userStore.load() répond).
try {
  const cachedTheme = localStorage.getItem('tt-theme')
  if (cachedTheme) document.documentElement.setAttribute('data-theme', cachedTheme)
  const cachedAccent = localStorage.getItem('tt-accent')
  if (cachedAccent) document.documentElement.setAttribute('data-accent', cachedAccent)
} catch { /* stockage indisponible */ }

createApp(App).use(createPinia()).use(router).mount('#app')

// Enregistre le service worker (PWA installable + réception Web Push).
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {})
  })
}
