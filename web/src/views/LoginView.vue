<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/api'
import { ApiError, serverBase } from '@/api/client'

const router = useRouter()
const mode = ref<'login' | 'register'>('login')
const email = ref('')
const password = ref('')
const displayName = ref('')
const error = ref('')
const busy = ref(false)

// App embarquée (Capacitor/Electron packagé) : l'UI n'est pas servie par le
// backend, il faut l'URL du serveur self-hosted. Ouvert par défaut si une
// plateforme native est détectée sans serveur configuré.
const isEmbedded = typeof window !== 'undefined' && ('Capacitor' in window || 'electronAPI' in window)
const serverUrl = ref(serverBase.get())
const showServer = ref(isEmbedded && !serverBase.get())

async function submit() {
  error.value = ''
  busy.value = true
  serverBase.set(serverUrl.value)
  try {
    if (mode.value === 'register') {
      await authApi.register(email.value, password.value, displayName.value)
    } else {
      await authApi.login(email.value, password.value)
    }
    router.push('/today')
  } catch (e) {
    error.value =
      e instanceof ApiError ? 'Identifiants invalides ou email déjà utilisé.' : 'Erreur réseau.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="login">
    <form class="card" @submit.prevent="submit">
      <h1>TickTick</h1>
      <p class="sub">{{ mode === 'login' ? 'Connexion' : 'Créer un compte' }}</p>

      <input v-model="email" type="email" placeholder="Email" required autocomplete="email" />
      <input
        v-model="password"
        type="password"
        placeholder="Mot de passe"
        required
        autocomplete="current-password"
      />
      <input
        v-if="mode === 'register'"
        v-model="displayName"
        type="text"
        placeholder="Nom affiché (optionnel)"
      />

      <button type="button" class="server-toggle" @click="showServer = !showServer">
        ⚙ Serveur{{ serverUrl ? ` : ${serverUrl}` : '' }}
      </button>
      <input
        v-if="showServer"
        v-model="serverUrl"
        type="url"
        placeholder="URL du serveur (ex. https://ticktick.mondomaine.fr)"
        autocomplete="url"
      />

      <p v-if="error" class="error">{{ error }}</p>

      <button class="btn btn-primary" type="submit" :disabled="busy">
        {{ mode === 'login' ? 'Se connecter' : "S'inscrire" }}
      </button>

      <button
        class="switch"
        type="button"
        @click="mode = mode === 'login' ? 'register' : 'login'"
      >
        {{ mode === 'login' ? 'Pas de compte ? Créer un compte' : 'Déjà un compte ? Se connecter' }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.server-toggle {
  border: none;
  background: none;
  color: var(--text-muted);
  font-size: 11.5px;
  cursor: pointer;
  text-align: left;
  padding: 0;
}
.server-toggle:hover { color: var(--primary); }

.login {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  background: var(--bg-sidebar);
}
.card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 320px;
  padding: 32px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.12);
}
@media (max-width: 480px) {
  .card { width: calc(100vw - 40px); padding: 24px 20px; }
}
h1 {
  margin: 0;
  color: var(--primary);
  font-size: 24px;
}
.sub {
  margin: 0 0 8px;
  color: var(--text-secondary);
}
.card input {
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  outline: none;
  background: var(--bg);
  color: var(--text);
}
.card input:focus {
  border-color: var(--primary);
}
.btn-primary {
  justify-content: center;
}
.btn-primary:disabled {
  opacity: 0.6;
}
.switch {
  color: var(--text-secondary);
  font-size: 13px;
}
.error {
  margin: 0;
  color: var(--danger);
  font-size: 13px;
}
</style>
