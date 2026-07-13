/** Raccourcis clavier globaux de l'app web (jeu inspiré de TickTick desktop).
 *
 * Volontairement sans Ctrl+chiffre (le navigateur garde le contrôle des
 * onglets). Les champs de saisie ne sont pas interceptés (sauf Échap).
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '@/stores/tasks'

export const showShortcutsHelp = ref(false)

export const SHORTCUTS: Array<{ keys: string; label: string }> = [
  { keys: 'Ctrl + Maj + A', label: 'Ajout rapide de tâche' },
  { keys: 'Ctrl + F', label: 'Rechercher' },
  { keys: 'Ctrl + Maj + M', label: 'Terminer la tâche sélectionnée' },
  { keys: 'Ctrl + Alt + T', label: 'Aujourd\'hui' },
  { keys: 'Ctrl + Alt + N', label: '7 prochains jours' },
  { keys: 'Ctrl + Alt + 1', label: 'Boîte de réception' },
  { keys: 'Ctrl + Alt + C', label: 'Calendrier' },
  { keys: 'Échap', label: 'Fermer le détail / désélectionner' },
  { keys: '?', label: 'Afficher cette aide' },
]

function isTyping(e: KeyboardEvent) {
  const el = e.target as HTMLElement | null
  return !!el && (
    el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable
  )
}

export function useKeyboardShortcuts() {
  const router = useRouter()
  const taskStore = useTaskStore()

  function onKeydown(e: KeyboardEvent) {
    // Échap marche partout : ferme l'aide, sinon désélectionne.
    if (e.key === 'Escape') {
      if (showShortcutsHelp.value) { showShortcutsHelp.value = false; return }
      if (!isTyping(e) && taskStore.selectedId !== null) taskStore.select(null)
      return
    }
    if (isTyping(e)) return

    if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
      e.preventDefault()
      showShortcutsHelp.value = !showShortcutsHelp.value
      return
    }

    const ctrl = e.ctrlKey || e.metaKey
    if (!ctrl) return

    if (e.shiftKey && e.code === 'KeyA') {
      e.preventDefault()
      window.dispatchEvent(new CustomEvent('tt:focus-quickadd'))
      return
    }
    if (e.shiftKey && e.code === 'KeyM') {
      e.preventDefault()
      const id = taskStore.selectedId
      if (id !== null) taskStore.complete(id)
      return
    }
    if (!e.altKey && !e.shiftKey && e.code === 'KeyF') {
      e.preventDefault()
      window.dispatchEvent(new CustomEvent('tt:focus-search'))
      return
    }
    if (e.altKey) {
      const routes: Record<string, string> = {
        KeyT: '/today',
        KeyN: '/next7',
        Digit1: '/inbox',
        KeyC: '/calendar',
      }
      const to = routes[e.code]
      if (to) {
        e.preventDefault()
        router.push(to)
      }
    }
  }

  onMounted(() => window.addEventListener('keydown', onKeydown))
  onUnmounted(() => window.removeEventListener('keydown', onKeydown))
}
