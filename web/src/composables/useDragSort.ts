import { ref } from 'vue'

/**
 * Drag & drop de liste avec HTML5 DnD.
 * Retourne les handlers à attacher aux éléments draggables.
 * onReorder(fromIndex, toIndex) est appelé à la fin du drag.
 */
export function useDragSort(onReorder: (from: number, to: number) => void) {
  const draggingIdx = ref<number | null>(null)
  const overIdx = ref<number | null>(null)

  function onDragStart(idx: number) {
    draggingIdx.value = idx
  }

  function onDragOver(e: DragEvent, idx: number) {
    e.preventDefault()
    overIdx.value = idx
  }

  function onDrop(idx: number) {
    if (draggingIdx.value !== null && draggingIdx.value !== idx) {
      onReorder(draggingIdx.value, idx)
    }
    draggingIdx.value = null
    overIdx.value = null
  }

  function onDragEnd() {
    draggingIdx.value = null
    overIdx.value = null
  }

  return { draggingIdx, overIdx, onDragStart, onDragOver, onDrop, onDragEnd }
}
