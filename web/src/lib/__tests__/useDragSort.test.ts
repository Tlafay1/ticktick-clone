import { describe, it, expect, vi } from 'vitest'
import { useDragSort } from '@/composables/useDragSort'

describe('useDragSort', () => {
  it('onReorder est appelé avec les bons index', () => {
    const reorder = vi.fn()
    const { onDragStart, onDrop } = useDragSort(reorder)
    onDragStart(2)
    onDrop(5)
    expect(reorder).toHaveBeenCalledWith(2, 5)
  })

  it('pas d\'appel si on drop sur le même index', () => {
    const reorder = vi.fn()
    const { onDragStart, onDrop } = useDragSort(reorder)
    onDragStart(3)
    onDrop(3)
    expect(reorder).not.toHaveBeenCalled()
  })

  it('draggingIdx est mis à null après drop', () => {
    const { draggingIdx, onDragStart, onDrop } = useDragSort(() => {})
    onDragStart(1)
    expect(draggingIdx.value).toBe(1)
    onDrop(2)
    expect(draggingIdx.value).toBeNull()
  })

  it('overIdx reflète l\'index survolé', () => {
    const { overIdx, onDragStart, onDragOver } = useDragSort(() => {})
    onDragStart(0)
    const fakeEvent = { preventDefault: () => {} } as DragEvent
    onDragOver(fakeEvent, 3)
    expect(overIdx.value).toBe(3)
  })

  it('onDragEnd réinitialise les index', () => {
    const { draggingIdx, overIdx, onDragStart, onDragEnd } = useDragSort(() => {})
    onDragStart(1)
    onDragEnd()
    expect(draggingIdx.value).toBeNull()
    expect(overIdx.value).toBeNull()
  })
})
