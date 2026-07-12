<script setup lang="ts">
import ToastContainer from '@/components/ToastContainer.vue'
import ShortcutsHelp from '@/components/ShortcutsHelp.vue'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'

useKeyboardShortcuts()
</script>

<template>
  <RouterView />
  <ToastContainer />
  <ShortcutsHelp />
</template>
