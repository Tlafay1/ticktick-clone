<script setup lang="ts">
import { authApi } from '@/api'
import { useRouter } from 'vue-router'

/**
 * Coque de l'application — placeholder.
 *
 * La vraie UI (sidebar / liste de tâches / panneau de détail) est à construire ;
 * voir les `it.todo` « Jalon 1 — cœur web » dans src/spec/acceptance.spec.ts et
 * le guide CLAUDE.md. La couche API (src/api) et la logique pure (src/lib) sont
 * prêtes à être branchées ici.
 */
const router = useRouter()
function logout() {
  authApi.logout()
  router.push('/login')
}
</script>

<template>
  <div class="shell">
    <p>Coque de l'application — la vue de liste reste à construire (Jalon 1 — cœur web).</p>
    <button class="btn btn-ghost" @click="logout">Se déconnecter</button>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  height: 100%;
  color: var(--text-secondary);
}
</style>
