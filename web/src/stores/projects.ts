import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { projectsApi } from '@/api'
import type { Project, ProjectGroup } from '@/types'

export const useProjectStore = defineStore('projects', () => {
  const projects = ref<Project[]>([])
  const groups = ref<ProjectGroup[]>([])
  const loading = ref(false)

  const inbox = computed(() => projects.value.find((p) => p.is_inbox) ?? null)

  async function load() {
    loading.value = true
    try {
      ;[projects.value, groups.value] = await Promise.all([
        projectsApi.list(),
        projectsApi.groups(),
      ])
    } finally {
      loading.value = false
    }
  }

  async function create(name: string, groupId?: number) {
    const p = await projectsApi.create({ name, group: groupId ?? null })
    projects.value.push(p)
    return p
  }

  async function update(id: number, data: Partial<Project>) {
    const p = await projectsApi.update(id, data)
    const idx = projects.value.findIndex((x) => x.id === id)
    if (idx >= 0) projects.value[idx] = p
    return p
  }

  async function remove(id: number) {
    await projectsApi.remove(id)
    projects.value = projects.value.filter((p) => p.id !== id)
  }

  async function createGroup(name: string) {
    const g = await projectsApi.createGroup({ name })
    groups.value.push(g)
    return g
  }

  async function updateGroup(id: number, data: Partial<ProjectGroup>) {
    const g = await projectsApi.updateGroup(id, data)
    const idx = groups.value.findIndex((x) => x.id === id)
    if (idx >= 0) groups.value[idx] = g
    return g
  }

  async function removeGroup(id: number) {
    await projectsApi.removeGroup(id)
    groups.value = groups.value.filter((g) => g.id !== id)
    // Déplace les projets orphelins hors du dossier
    projects.value = projects.value.map((p) => p.group === id ? { ...p, group: null } : p)
  }

  return { projects, groups, inbox, loading, load, create, update, remove, createGroup, updateGroup, removeGroup }
})
