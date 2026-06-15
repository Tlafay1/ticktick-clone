<script setup lang="ts">
import { useUserStore } from '@/stores/user'
import { useTagStore } from '@/stores/tags'
import { useProjectStore } from '@/stores/projects'
import { useRouter } from 'vue-router'
import { onMounted, ref } from 'vue'

const userStore = useUserStore()
const tagStore = useTagStore()
const projectStore = useProjectStore()
const router = useRouter()

onMounted(async () => {
  if (!userStore.user) userStore.load()
  if (!tagStore.tags.length) await tagStore.load()
  if (!projectStore.projects.length) await projectStore.load()
})

const newTagName = ref('')
const newTagColor = ref('#4772fa')
const newTagParent = ref<number | null>(null)
const editingTagId = ref<number | null>(null)
const editingTagName = ref('')
const editingTagColor = ref('')
const editingTagParent = ref<number | null>(null)
const TAG_COLORS = ['#4772fa','#f55','#fa0','#4af','#8f4','#c4f','#f48','#34c6a0','#e8590c','#aaa']

async function createTag() {
  const name = newTagName.value.trim()
  if (!name) return
  await tagStore.create(name, newTagColor.value, newTagParent.value)
  newTagName.value = ''
  newTagParent.value = null
}

function startEdit(tag: { id: number; name: string; color: string; parent: number | null }) {
  editingTagId.value = tag.id
  editingTagName.value = tag.name
  editingTagColor.value = tag.color
  editingTagParent.value = tag.parent
}

async function saveEdit() {
  if (!editingTagId.value) return
  await tagStore.update(editingTagId.value, { name: editingTagName.value.trim(), color: editingTagColor.value, parent: editingTagParent.value })
  editingTagId.value = null
}

async function removeTag(id: number) {
  if (!confirm('Supprimer ce tag ? Il sera retiré de toutes les tâches.')) return
  await tagStore.remove(id)
}

function goBack() { router.back() }

const themeOptions = [
  { value: 'auto', label: 'Automatique (système)' },
  { value: 'light', label: 'Clair' },
  { value: 'dark', label: 'Sombre' },
]

const weekStartOptions = [
  { value: 0, label: 'Dimanche' },
  { value: 1, label: 'Lundi' },
  { value: 6, label: 'Samedi' },
]

const accentPresets = [
  { value: '',       label: 'Bleu', color: '#4772fa' },
  { value: 'red',    label: 'Rouge', color: '#e03131' },
  { value: 'green',  label: 'Vert', color: '#2f9e44' },
  { value: 'orange', label: 'Orange', color: '#e8590c' },
  { value: 'purple', label: 'Violet', color: '#7048e8' },
  { value: 'pink',   label: 'Rose', color: '#d6336c' },
  { value: 'teal',   label: 'Sarcelle', color: '#0c8599' },
]

const priorityOptions = [
  { value: 0, label: 'Aucune' },
  { value: 1, label: 'Basse' },
  { value: 3, label: 'Moyenne' },
  { value: 5, label: 'Haute' },
]

const defaultDueOptions = [
  { value: 'none', label: 'Aucune' },
  { value: 'today', label: "Aujourd'hui" },
  { value: 'tomorrow', label: 'Demain' },
]

const soundOptions = [
  { value: 'default', label: 'Son par défaut' },
  { value: 'chime', label: 'Carillon' },
  { value: 'bell', label: 'Cloche' },
  { value: 'none', label: 'Aucun son' },
]
</script>

<template>
  <div class="settings-layout">
    <aside class="settings-sidebar">
      <div class="settings-brand">TickTick</div>
      <button class="back-btn" @click="goBack">← Retour</button>
    </aside>

    <main class="settings-main">
      <h1 class="settings-title">Paramètres</h1>

      <section class="settings-section">
        <h2 class="section-title">Apparence</h2>

        <div class="setting-row">
          <label class="setting-label">Thème</label>
          <div class="theme-options">
            <button
              v-for="opt in themeOptions"
              :key="opt.value"
              class="theme-btn"
              :class="{ active: userStore.theme === opt.value }"
              @click="userStore.setTheme(opt.value as 'auto' | 'light' | 'dark')"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>

        <div class="setting-row accent-row">
          <label class="setting-label">Couleur d'accent</label>
          <div class="accent-options">
            <button
              v-for="p in accentPresets"
              :key="p.value"
              class="accent-dot"
              :class="{ active: (userStore.themePreset ?? '') === p.value }"
              :style="`background:${p.color}`"
              :title="p.label"
              @click="userStore.setPreset(p.value)"
            />
          </div>
        </div>
      </section>

      <section class="settings-section">
        <h2 class="section-title">Préférences</h2>

        <div class="setting-row">
          <label class="setting-label">Premier jour de la semaine</label>
          <select
            class="setting-select"
            :value="userStore.user?.settings?.week_start ?? 1"
            @change="userStore.updateSettings({ week_start: Number(($event.target as HTMLSelectElement).value) })"
          >
            <option v-for="opt in weekStartOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>

        <div class="setting-row">
          <label class="setting-label">Son de rappel</label>
          <select
            class="setting-select"
            :value="userStore.user?.settings?.reminder_sound ?? 'default'"
            @change="userStore.updateSettings({ reminder_sound: ($event.target as HTMLSelectElement).value })"
          >
            <option v-for="opt in soundOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>

        <div class="setting-row">
          <label class="setting-label">Parseur NLP (saisie rapide)</label>
          <label class="toggle">
            <input
              type="checkbox"
              :checked="userStore.user?.settings?.nlp_enabled ?? true"
              @change="userStore.updateSettings({ nlp_enabled: ($event.target as HTMLInputElement).checked })"
            />
            <span class="toggle-slider" />
          </label>
        </div>

        <div class="setting-row">
          <label class="setting-label">Supprimer les marqueurs NLP du titre</label>
          <label class="toggle">
            <input
              type="checkbox"
              :checked="userStore.user?.settings?.nlp_strip_text ?? true"
              @change="userStore.updateSettings({ nlp_strip_text: ($event.target as HTMLInputElement).checked })"
            />
            <span class="toggle-slider" />
          </label>
        </div>
      </section>

      <section class="settings-section">
        <h2 class="section-title">Valeurs par défaut des tâches</h2>
        <p class="section-hint">Pré-remplies à la création de chaque nouvelle tâche.</p>

        <div class="setting-row">
          <label class="setting-label">Liste par défaut</label>
          <select
            class="setting-select"
            :value="userStore.user?.settings?.default_project ?? ''"
            @change="userStore.updateSettings({ default_project: Number(($event.target as HTMLSelectElement).value) || null })"
          >
            <option value="">— Boîte de réception —</option>
            <option v-for="p in projectStore.projects.filter(p => !p.is_inbox && !p.archived && !p.is_smart)" :key="p.id" :value="p.id">
              {{ p.name }}
            </option>
          </select>
        </div>

        <div class="setting-row">
          <label class="setting-label">Priorité par défaut</label>
          <select
            class="setting-select"
            :value="userStore.user?.settings?.default_priority ?? 0"
            @change="userStore.updateSettings({ default_priority: Number(($event.target as HTMLSelectElement).value) })"
          >
            <option v-for="opt in priorityOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>

        <div class="setting-row">
          <label class="setting-label">Échéance par défaut</label>
          <select
            class="setting-select"
            :value="userStore.user?.settings?.default_due ?? 'none'"
            @change="userStore.updateSettings({ default_due: ($event.target as HTMLSelectElement).value as 'none' | 'today' | 'tomorrow' })"
          >
            <option v-for="opt in defaultDueOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>
      </section>

      <!-- Gestion des tags -->
      <section class="settings-section">
        <h2 class="section-title">Étiquettes (Tags)</h2>
        <p class="section-hint">Créez, renommez ou supprimez vos étiquettes.</p>

        <!-- Créer un tag -->
        <div class="tag-create-row setting-row">
          <div class="color-swatch-wrap">
            <span class="color-swatch" :style="`background:${newTagColor}`" />
            <div class="color-mini-picker">
              <button v-for="c in TAG_COLORS" :key="c" class="color-mini-dot"
                :class="{ active: newTagColor === c }" :style="`background:${c}`"
                @click="newTagColor = c" />
            </div>
          </div>
          <input v-model="newTagName" placeholder="Nouveau tag…" class="setting-input tag-input"
            @keydown.enter="createTag" />
          <select v-model="newTagParent" class="setting-select tag-parent-select">
            <option :value="null">— Racine —</option>
            <option v-for="t in tagStore.rootTags" :key="t.id" :value="t.id">#{{ t.name }}</option>
          </select>
          <button class="btn btn-primary" :disabled="!newTagName.trim()" @click="createTag">Créer</button>
        </div>

        <!-- Liste des tags existants -->
        <div class="tags-list">
          <div v-for="tag in tagStore.tags" :key="tag.id" class="tag-row">
            <template v-if="editingTagId === tag.id">
              <div class="color-swatch-wrap">
                <span class="color-swatch" :style="`background:${editingTagColor}`" />
                <div class="color-mini-picker">
                  <button v-for="c in TAG_COLORS" :key="c" class="color-mini-dot"
                    :class="{ active: editingTagColor === c }" :style="`background:${c}`"
                    @click="editingTagColor = c" />
                </div>
              </div>
              <input v-model="editingTagName" class="setting-input tag-input"
                @keydown.enter="saveEdit" @keydown.escape="editingTagId = null" autofocus />
              <select v-model="editingTagParent" class="setting-select tag-parent-select">
                <option :value="null">— Racine —</option>
                <option v-for="t in tagStore.rootTags.filter(t => t.id !== editingTagId)" :key="t.id" :value="t.id">#{{ t.name }}</option>
              </select>
              <button class="btn btn-primary" @click="saveEdit">✓</button>
              <button class="btn btn-ghost" @click="editingTagId = null">✕</button>
            </template>
            <template v-else>
              <span class="tag-color-dot" :style="tag.color ? `background:${tag.color}` : 'background:var(--border)'" />
              <span class="tag-name">#{{ tag.name }}</span>
              <button class="icon-btn tag-action" @click="startEdit(tag)">✏️</button>
              <button class="icon-btn tag-action danger-btn" @click="removeTag(tag.id)">🗑</button>
            </template>
          </div>
          <div v-if="!tagStore.tags.length" class="empty-hint">Aucun tag créé.</div>
        </div>
      </section>

      <!-- Daily review (M26) -->
      <section class="settings-section">
        <h2 class="section-title">Révision quotidienne</h2>
        <p class="section-hint">Recevez une notification de bilan à l'heure souhaitée (laissez vide pour désactiver).</p>

        <div class="setting-row">
          <label class="setting-label">🌅 Révision du matin</label>
          <input
            type="time"
            class="setting-input"
            :value="userStore.user?.settings?.daily_review_morning ?? ''"
            @change="userStore.updateSettings({ daily_review_morning: ($event.target as HTMLInputElement).value || null })"
          />
        </div>

        <div class="setting-row">
          <label class="setting-label">🌆 Révision du soir</label>
          <input
            type="time"
            class="setting-input"
            :value="userStore.user?.settings?.daily_review_evening ?? ''"
            @change="userStore.updateSettings({ daily_review_evening: ($event.target as HTMLInputElement).value || null })"
          />
        </div>
      </section>

      <section class="settings-section">
        <h2 class="section-title">Smart lists visibles</h2>
        <p class="section-hint">Choisissez quelles smart lists apparaissent dans la sidebar.</p>
        <div v-for="sl in ['today','tomorrow','next7','all','completed']" :key="sl" class="setting-row">
          <label class="setting-label">{{ { today: 'Aujourd\'hui', tomorrow: 'Demain', next7: '7 prochains jours', all: 'Toutes', completed: 'Terminées' }[sl] }}</label>
          <label class="toggle">
            <input
              type="checkbox"
              :checked="(userStore.user?.settings?.smart_list_visibility?.[sl] ?? true)"
              @change="userStore.updateSettings({ smart_list_visibility: { ...(userStore.user?.settings?.smart_list_visibility ?? {}), [sl]: ($event.target as HTMLInputElement).checked } })"
            />
            <span class="toggle-slider" />
          </label>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.settings-layout {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.settings-sidebar {
  width: 200px;
  min-width: 200px;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border);
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.settings-brand { font-size: 18px; font-weight: 700; color: var(--primary); }
.back-btn {
  font-size: 13px;
  color: var(--text-secondary);
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  padding: 6px 0;
}
.back-btn:hover { color: var(--primary); }

.settings-main {
  flex: 1;
  overflow-y: auto;
  padding: 32px 40px;
  max-width: 700px;
}
.settings-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 28px;
}

.settings-section {
  margin-bottom: 36px;
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  margin: 0 0 16px;
}
.section-hint { font-size: 13px; color: var(--text-secondary); margin: -8px 0 12px; }

.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}
.setting-label { font-size: 14px; color: var(--text); }

.setting-select {
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  font-size: 14px;
  color: var(--text);
  outline: none;
}

/* Thème */
.theme-options { display: flex; gap: 6px; }
.theme-btn {
  padding: 6px 14px;
  border-radius: 20px;
  border: 1px solid var(--border);
  background: none;
  font-size: 13px;
  cursor: pointer;
  color: var(--text-secondary);
}
.theme-btn:hover { border-color: var(--primary); color: var(--primary); }
.theme-btn.active { background: var(--primary); color: #fff; border-color: var(--primary); }

/* Presets accent */
.accent-row { flex-wrap: wrap; gap: 8px; }
.accent-options { display: flex; gap: 8px; }
.accent-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  transition: transform 0.1s, border-color 0.1s;
}
.accent-dot:hover { transform: scale(1.15); }
.accent-dot.active { border-color: var(--text); box-shadow: 0 0 0 2px var(--bg), 0 0 0 4px currentColor; }

/* Toggle */
.toggle {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
  cursor: pointer;
}
.toggle input { opacity: 0; width: 0; height: 0; }
.toggle-slider {
  position: absolute;
  inset: 0;
  background: var(--border);
  border-radius: 24px;
  transition: background 0.2s;
}
.toggle-slider::before {
  content: '';
  position: absolute;
  width: 18px;
  height: 18px;
  left: 3px;
  top: 3px;
  background: #fff;
  border-radius: 50%;
  transition: transform 0.2s;
}
.toggle input:checked + .toggle-slider { background: var(--primary); }
.toggle input:checked + .toggle-slider::before { transform: translateX(20px); }

/* Tags */
.setting-input { padding: 6px 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; background: var(--bg); color: var(--text); outline: none; }
.setting-input:focus { border-color: var(--primary); }
.tag-input { flex: 1; }
.tag-create-row { align-items: center; gap: 8px; }
.color-swatch-wrap { position: relative; }
.color-swatch { display: inline-block; width: 20px; height: 20px; border-radius: 50%; cursor: pointer; border: 2px solid var(--border); }
.color-mini-picker {
  display: none; position: absolute; top: 28px; left: 0;
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
  padding: 6px; display: none; flex-wrap: wrap; gap: 4px; width: 130px; z-index: 10;
}
.color-swatch-wrap:hover .color-mini-picker { display: flex; }
.color-mini-dot { width: 16px; height: 16px; border-radius: 50%; border: 2px solid transparent; cursor: pointer; }
.color-mini-dot.active { border-color: var(--text); }
.tag-parent-select { font-size: 12px; padding: 4px 6px; max-width: 130px; }
.tags-list { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; }
.tag-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; border-bottom: 1px solid var(--border); }
.tag-color-dot { width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0; }
.tag-name { flex: 1; font-size: 14px; }
.tag-action { font-size: 14px; }
.danger-btn { color: var(--danger, #e03131); }
.empty-hint { color: var(--text-muted); font-size: 13px; }
</style>
