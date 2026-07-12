<script setup lang="ts">
import { onMounted } from 'vue'
import ToastContainer from '@/components/ToastContainer.vue'
import ShortcutsHelp from '@/components/ShortcutsHelp.vue'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import { useUserStore } from '@/stores/user'
import { tokens } from '@/api/client'
import { electronAPI } from '@/lib/electron'
import { tasksApi } from '@/api'
import { pushToast } from '@/composables/useToast'

useKeyboardShortcuts()

// Charge l'utilisateur (thème, réglages) quelle que soit la route d'arrivée —
// sinon un refresh sur /calendar ou /habits restait en thème par défaut.
const userStore = useUserStore()
onMounted(() => {
  if (tokens.access && !userStore.user) userStore.load()

  // Bouton « Terminer » des notifications natives Electron.
  electronAPI()?.onNotificationAction(async ({ id, action }) => {
    if (action === 'complete') {
      await tasksApi.complete(id).catch(() => {})
      pushToast('Tâche terminée', 'success')
    }
  })
})
</script>

<template>
  <RouterView />
  <ToastContainer />
  <ShortcutsHelp />
</template>
