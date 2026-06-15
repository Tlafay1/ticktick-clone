import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { tagsApi } from '@/api'
import type { Tag } from '@/types'

export const useTagStore = defineStore('tags', () => {
  const tags = ref<Tag[]>([])

  async function load() {
    tags.value = await tagsApi.list()
  }

  async function create(name: string, color = '', parent: number | null = null) {
    const t = await tagsApi.create({ name, color, parent })
    tags.value.push(t)
    return t
  }

  async function update(id: number, data: Partial<Tag>) {
    const t = await tagsApi.update(id, data)
    const idx = tags.value.findIndex(x => x.id === id)
    if (idx >= 0) tags.value[idx] = t
    return t
  }

  async function remove(id: number) {
    await tagsApi.remove(id)
    tags.value = tags.value.filter(t => t.id !== id)
  }

  async function merge(id: number, targetId: number) {
    await tagsApi.merge(id, targetId)
    tags.value = tags.value.filter(t => t.id !== id)
  }

  function byId(id: number) {
    return tags.value.find((t) => t.id === id) ?? null
  }

  const rootTags = computed(() => tags.value.filter(t => t.parent === null))

  function childrenOf(parentId: number) {
    return tags.value.filter(t => t.parent === parentId)
  }

  function descendants(parentId: number): Tag[] {
    const direct = childrenOf(parentId)
    return direct.flatMap(t => [t, ...descendants(t.id)])
  }

  return { tags, load, create, update, remove, merge, byId, rootTags, childrenOf, descendants }
})
