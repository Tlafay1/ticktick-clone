<script setup lang="ts">
import { onMounted } from 'vue'
import ToastContainer from '@/components/ToastContainer.vue'
import ShortcutsHelp from '@/components/ShortcutsHelp.vue'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import { useUserStore } from '@/stores/user'
import { tokens } from '@/api/client'

useKeyboardShortcuts()

// Charge l'utilisateur (thème, réglages) quelle que soit la route d'arrivée —
// sinon un refresh sur /calendar ou /habits restait en thème par défaut.
const userStore = useUserStore()
onMounted(() => {
  if (tokens.access && !userStore.user) userStore.load()
})
</script>

<template>
  <RouterView />
  <ToastContainer />
  <ShortcutsHelp />
</template>
