// @vitest-environment happy-dom
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import QuickAdd from '@/components/QuickAdd.vue'
import { useTaskStore } from '@/stores/tasks'
import { useTagStore } from '@/stores/tags'
import { useProjectStore } from '@/stores/projects'
import type { Task } from '@/types'

vi.mock('@/api', () => ({
  templatesApi: { list: vi.fn().mockResolvedValue([]) },
}))

function seedStores() {
  const taskStore = useTaskStore()
  const tagStore = useTagStore()
  const projectStore = useProjectStore()
  projectStore.projects = [
    { id: 1, name: 'Inbox', is_inbox: true },
    { id: 3, name: 'Perso', is_inbox: false },
  ] as unknown as typeof projectStore.projects
  tagStore.tags = [{ id: 7, name: 'travail', color: '', parent: null }] as unknown as typeof tagStore.tags
  const create = vi.spyOn(taskStore, 'create').mockResolvedValue({} as Task)
  return { taskStore, tagStore, projectStore, create }
}

async function submitWith(wrapper: ReturnType<typeof mount>, value: string) {
  await wrapper.find('.quick-add-trigger').trigger('click')
  await wrapper.find('input').setValue(value)
  await wrapper.find('.btn-primary').trigger('click')
  await new Promise(r => setTimeout(r, 0))
}

describe('QuickAdd', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('envoie les #tags parsés (résolus en ids) à la création', async () => {
    const { create } = seedStores()
    const wrapper = mount(QuickAdd)
    await submitWith(wrapper, 'Préparer la réunion #travail')
    expect(create).toHaveBeenCalledTimes(1)
    const payload = create.mock.calls[0][0]
    expect(payload.tags).toEqual([7])
    expect(payload.title).toBe('Préparer la réunion')
  })

  it('respecte ^Liste : la tâche va dans la liste nommée', async () => {
    const { create } = seedStores()
    const wrapper = mount(QuickAdd)
    await submitWith(wrapper, 'Acheter du pain ^Perso')
    expect(create.mock.calls[0][0].project).toBe(3)
  })

  it("ne crée jamais une tâche au titre vide (que des jetons NLP)", async () => {
    const { create } = seedStores()
    const wrapper = mount(QuickAdd)
    await submitWith(wrapper, 'demain !high')
    const payload = create.mock.calls[0][0]
    expect(payload.title).toBeTruthy()
    expect(payload.priority).toBe(5)
  })

  it("s'ouvre sur l'événement global tt:focus-quickadd (raccourci Ctrl+Maj+A)", async () => {
    seedStores()
    const wrapper = mount(QuickAdd)
    expect(wrapper.find('input').exists()).toBe(false)
    window.dispatchEvent(new CustomEvent('tt:focus-quickadd'))
    await new Promise(r => setTimeout(r, 80))
    expect(wrapper.find('input').exists()).toBe(true)
  })

  it('crée un tag manquant puis l\'attache', async () => {
    const { create, tagStore } = seedStores()
    const createTag = vi.spyOn(tagStore, 'create').mockResolvedValue(
      { id: 42, name: 'urgent', color: '', parent: null } as unknown as never,
    )
    const wrapper = mount(QuickAdd)
    await submitWith(wrapper, 'Payer la facture #urgent')
    expect(createTag).toHaveBeenCalledWith('urgent')
    expect(create.mock.calls[0][0].tags).toEqual([42])
  })
})
