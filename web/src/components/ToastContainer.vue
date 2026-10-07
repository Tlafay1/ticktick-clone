<script setup lang="ts">
import { useToast } from '@/composables/useToast'

const { toasts, removeToast } = useToast()
</script>

<template>
  <div class="toast-container">
    <TransitionGroup name="toast">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="toast"
        :class="t.type"
        @click="removeToast(t.id)"
      >
        {{ t.message }}
        <button
          v-if="t.action"
          class="toast-action"
          @click.stop="t.action.run(); removeToast(t.id)"
        >{{ t.action.label }}</button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 3000;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: min(92vw, 360px);
}
.toast {
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  color: #fff;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.18);
  cursor: pointer;
}
.toast-action {
  margin-left: 10px;
  padding: 2px 8px;
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: 4px;
  background: transparent;
  color: #fff;
  font: inherit;
  cursor: pointer;
}
.toast.error { background: var(--danger); }
.toast.success { background: #2f9e44; }
.toast.info { background: var(--text-secondary); }

.toast-enter-active, .toast-leave-active { transition: opacity 0.25s, transform 0.25s; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(8px); }
</style>
