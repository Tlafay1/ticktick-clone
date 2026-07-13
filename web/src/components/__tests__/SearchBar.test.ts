// @vitest-environment happy-dom
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import SearchBar from '@/components/SearchBar.vue'

const list = vi.fn().mockResolvedValue([{ id: 1, title: 'trouvé', status: 0 }])
vi.mock('@/api', () => ({ tasksApi: { list: (...a: unknown[]) => list(...a) } }))

describe('SearchBar', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    list.mockClear()
    vi.useFakeTimers()
  })

  it('émet reset après avoir effacé une recherche active (évite les résultats périmés)', async () => {
    const wrapper = mount(SearchBar)
    await wrapper.find('input').setValue('rapport')
    await vi.advanceTimersByTimeAsync(350)
    expect(list).toHaveBeenCalledWith({ q: 'rapport', status: 0 })

    await wrapper.find('input').setValue('')
    await vi.advanceTimersByTimeAsync(0)
    expect(wrapper.emitted('reset')).toHaveLength(1)
  })

  it("n'émet pas reset si aucune recherche n'était en cours", async () => {
    const wrapper = mount(SearchBar)
    await wrapper.find('input').setValue('a')
    await wrapper.find('input').setValue('')
    await vi.advanceTimersByTimeAsync(0)
    expect(wrapper.emitted('reset')).toBeUndefined()
  })
})
