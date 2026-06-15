/** État d'UI partagé (tiroir latéral mobile). */
import { ref } from 'vue'

const sidebarOpen = ref(false)

export function useUiState() {
  return {
    sidebarOpen,
    toggleSidebar: () => (sidebarOpen.value = !sidebarOpen.value),
    closeSidebar: () => (sidebarOpen.value = false),
  }
}
