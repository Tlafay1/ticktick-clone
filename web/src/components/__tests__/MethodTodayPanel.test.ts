// @vitest-environment happy-dom
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import type { MethodToday, SlotOccurrence } from '@/types'

const push = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))

const today = vi.fn()
const setDay = vi.fn()
const start = vi.fn()
vi.mock('@/api', () => ({
  methodApi: { today: () => today(), setDay: (c: string) => setDay(c) },
  occurrencesApi: { start: (id: number) => start(id), joker: vi.fn() },
}))

import MethodTodayPanel from '@/components/MethodTodayPanel.vue'

function occurrence(over: Partial<SlotOccurrence> = {}): SlotOccurrence {
  const startAt = new Date(Date.now() + 10 * 60_000) // dans 10 min : démarrable
  return {
    id: 7, slot: 1, date: startAt.toISOString().slice(0, 10), duration_minutes: 25, kind: 'work',
    start_at: startAt.toISOString(), end_at: startAt.toISOString(),
    status: 'planned', excuse_reason: '', task: null,
    next_action: { id: 3, title: 'Lab SQLi 1', project: 2 },
    started_at: null, focus_session: null, recovers: null,
    ...over,
  }
}

function dashboard(over: Partial<MethodToday> = {}): MethodToday {
  return {
    date: '2026-10-12', color: null, paused: false, pause_until: null, level: 1,
    today_limit: 3, today_count: 4, jokers_remaining: 2, proposals_count: 2,
    review_pending: true, occurrences: [occurrence()],
    ...over,
  }
}

async function mountPanel(data: MethodToday) {
  today.mockResolvedValue(data)
  const wrapper = mount(MethodTodayPanel, { global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } } })
  await flushPromises()
  return wrapper
}

describe('MethodTodayPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('demande la couleur du jour tant qu\'elle n\'est pas choisie', async () => {
    const wrapper = await mountPanel(dashboard())
    expect(wrapper.text()).toContain('Comment est ta journée ?')
    setDay.mockResolvedValue({})
    await wrapper.findAll('.color-btn')[1].trigger('click')
    expect(setDay).toHaveBeenCalledWith('orange')
  })

  it('montre la prochaine action et démarre en un geste vers le focus', async () => {
    start.mockResolvedValue(occurrence({ status: 'honored' }))
    const wrapper = await mountPanel(dashboard({ color: 'green' }))
    expect(wrapper.text()).toContain('Lab SQLi 1')
    await wrapper.find('.occ-start').trigger('click')
    await flushPromises()
    expect(start).toHaveBeenCalledWith(7)
    expect(push).toHaveBeenCalledWith('/focus')
  })

  it('signale le dépassement de la limite, la revue et les propositions', async () => {
    const wrapper = await mountPanel(dashboard({ color: 'green' }))
    expect(wrapper.find('.today-count').classes()).toContain('over')
    expect(wrapper.text()).toContain('Ta revue de la semaine t\'attend')
    expect(wrapper.text()).toContain('2 propositions à valider')
  })

  it('un tampon sans rattrapage est du temps libre (pas de bouton)', async () => {
    const wrapper = await mountPanel(dashboard({ color: 'green', occurrences: [occurrence({ kind: 'buffer' })] }))
    expect(wrapper.text()).toContain('Temps libre')
    expect(wrapper.find('.occ-start').exists()).toBe(false)
  })
})
