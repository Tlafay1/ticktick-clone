/**
 * File de mutations offline.
 *
 * En production, utilise IndexedDB (si disponible) pour la persistance.
 * En tests Node, retombe sur la map en mémoire (pas d'IndexedDB dans Node).
 *
 * Chaque mutation = { id, method, url, body, attempt, createdAt }.
 * On rejoue la file via `flush()` dès qu'on se reconnecte.
 */

export interface QueuedMutation {
  id: string
  method: 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  url: string
  body?: unknown
  attempt: number
  createdAt: number
}

const DB_NAME = 'ticktick-offline'
const STORE_NAME = 'mutations'
const DB_VERSION = 1

// Fallback in-memory map (tests Node + quand IndexedDB absent)
const _mem: Map<string, QueuedMutation> = new Map()

function uid(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

// ---------- IndexedDB helpers ----------

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = () => {
      req.result.createObjectStore(STORE_NAME, { keyPath: 'id' })
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function idbAdd(m: QueuedMutation): Promise<void> {
  const db = await openDB()
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    tx.objectStore(STORE_NAME).put(m)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

async function idbGetAll(): Promise<QueuedMutation[]> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly')
    const req = tx.objectStore(STORE_NAME).getAll()
    req.onsuccess = () => resolve(req.result as QueuedMutation[])
    req.onerror = () => reject(req.error)
  })
}

async function idbDelete(id: string): Promise<void> {
  const db = await openDB()
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    tx.objectStore(STORE_NAME).delete(id)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

const hasIndexedDB = typeof indexedDB !== 'undefined'

// ---------- Public API ----------

export async function enqueue(
  method: QueuedMutation['method'],
  url: string,
  body?: unknown,
): Promise<QueuedMutation> {
  const m: QueuedMutation = { id: uid(), method, url, body, attempt: 0, createdAt: Date.now() }
  if (hasIndexedDB) {
    await idbAdd(m)
  } else {
    _mem.set(m.id, m)
  }
  return m
}

export async function dequeue(id: string): Promise<void> {
  if (hasIndexedDB) {
    await idbDelete(id)
  } else {
    _mem.delete(id)
  }
}

export async function getAll(): Promise<QueuedMutation[]> {
  if (hasIndexedDB) {
    return idbGetAll()
  }
  return Array.from(_mem.values()).sort((a, b) => a.createdAt - b.createdAt)
}

export async function clearAll(): Promise<void> {
  const items = await getAll()
  await Promise.all(items.map(m => dequeue(m.id)))
}

/**
 * Rejoue toutes les mutations en attente.
 * @param sender fonction qui envoie une requête HTTP (typiquement http.request)
 * @returns nb de mutations rejouées avec succès
 */
export async function flush(
  sender: (m: QueuedMutation) => Promise<void>,
): Promise<number> {
  const items = await getAll()
  let count = 0
  for (const m of items) {
    try {
      await sender({ ...m, attempt: m.attempt + 1 })
      await dequeue(m.id)
      count++
    } catch {
      // Laisse dans la file pour le prochain flush
    }
  }
  return count
}
