<script setup lang="ts">
import { showShortcutsHelp, SHORTCUTS } from '@/composables/useKeyboardShortcuts'
</script>

<template>
  <div v-if="showShortcutsHelp" class="sh-overlay" @click.self="showShortcutsHelp = false">
    <div class="sh-modal">
      <div class="sh-head">
        <h2>Raccourcis clavier</h2>
        <button class="icon-btn" @click="showShortcutsHelp = false">✕</button>
      </div>
      <div class="sh-list">
        <div v-for="s in SHORTCUTS" :key="s.keys" class="sh-row">
          <span class="sh-label">{{ s.label }}</span>
          <kbd class="sh-keys">{{ s.keys }}</kbd>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sh-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3000;
}
.sh-modal {
  width: 380px;
  max-width: 92vw;
  background: var(--bg);
  border-radius: 14px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.22);
  padding: 18px 20px;
}
.sh-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.sh-head h2 { margin: 0; font-size: 16px; }
.sh-list { display: flex; flex-direction: column; }
.sh-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 0;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}
.sh-row:last-child { border-bottom: none; }
.sh-keys {
  font-family: inherit;
  font-size: 11.5px;
  color: var(--text-secondary);
  background: var(--bg-hover);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 2px 7px;
}
</style>
