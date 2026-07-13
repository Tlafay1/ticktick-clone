import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { authApi } from '@/api'
import type { User, UserSettings } from '@/types'

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const theme = ref<'auto' | 'light' | 'dark'>('auto')

  const themePreset = ref('')

  function applyTheme(t: 'auto' | 'light' | 'dark') {
    if (typeof document === 'undefined') return
    const resolved =
      t === 'auto'
        ? window.matchMedia('(prefers-color-scheme: dark)').matches
          ? 'dark'
          : 'light'
        : t
    document.documentElement.setAttribute('data-theme', resolved)
    // Cache pour appliquer le thème dès le prochain chargement (avant l'API).
    try { localStorage.setItem('tt-theme', resolved) } catch { /* stockage indisponible */ }
  }

  function applyPreset(preset: string) {
    if (typeof document === 'undefined') return
    if (preset) {
      document.documentElement.setAttribute('data-accent', preset)
    } else {
      document.documentElement.removeAttribute('data-accent')
    }
    try { localStorage.setItem('tt-accent', preset) } catch { /* stockage indisponible */ }
  }

  watch(theme, applyTheme)
  watch(themePreset, applyPreset)

  async function load() {
    try {
      user.value = await authApi.me()
      theme.value = user.value.settings?.theme ?? 'auto'
      themePreset.value = user.value.settings?.theme_preset ?? ''
      applyTheme(theme.value)
      applyPreset(themePreset.value)
    } catch {
      // non connecté
    }
  }

  async function updateSettings(patch: Partial<UserSettings>) {
    await authApi.updateSettings(patch)
    if (user.value) {
      user.value = { ...user.value, settings: { ...user.value.settings, ...patch } }
    }
    if (patch.theme) {
      theme.value = patch.theme
    }
    if (patch.theme_preset !== undefined) {
      themePreset.value = patch.theme_preset
    }
  }

  function setTheme(t: 'auto' | 'light' | 'dark') {
    theme.value = t
    updateSettings({ theme: t })
  }

  function setPreset(p: string) {
    themePreset.value = p
    updateSettings({ theme_preset: p })
  }

  return { user, theme, themePreset, load, updateSettings, setTheme, setPreset }
})
