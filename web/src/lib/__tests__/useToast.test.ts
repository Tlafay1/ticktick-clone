import { describe, it, expect, beforeEach } from 'vitest'
import { useToast } from '@/composables/useToast'

describe('useToast', () => {
  const { toasts, pushToast, removeToast } = useToast()

  beforeEach(() => {
    toasts.value = []
  })

  it('ajoute un toast avec message et type', () => {
    pushToast('échec', 'error', 0)
    expect(toasts.value).toHaveLength(1)
    expect(toasts.value[0].message).toBe('échec')
    expect(toasts.value[0].type).toBe('error')
  })

  it('retire un toast par id', () => {
    const id = pushToast('info', 'info', 0)
    pushToast('autre', 'success', 0)
    removeToast(id)
    expect(toasts.value).toHaveLength(1)
    expect(toasts.value[0].message).toBe('autre')
  })
})
