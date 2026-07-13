// @vitest-environment happy-dom
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ProjectContextMenu from '@/components/ProjectContextMenu.vue'
import type { Project } from '@/types'

vi.mock('@/api', () => ({
  projectsApi: { update: vi.fn(), remove: vi.fn() },
}))

const project = { id: 3, name: 'Perso', is_inbox: false, archived: false } as Project

describe('ProjectContextMenu', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it("émet 'edit' via l'entrée Modifier (point d'entrée des smart lists custom)", async () => {
    const wrapper = mount(ProjectContextMenu, { props: { project, x: 0, y: 0 } })
    await wrapper.find('button.menu-item:nth-of-type(2)').trigger('click')
    expect(wrapper.emitted('edit')).toHaveLength(1)
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
