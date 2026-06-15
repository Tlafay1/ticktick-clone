import { describe, it, expect, beforeEach } from 'vitest'
import { enqueue, dequeue, getAll, clearAll, flush } from '../offlineQueue'

beforeEach(async () => {
  await clearAll()
})

describe('offlineQueue', () => {
  it('enqueue ajoute une mutation', async () => {
    await enqueue('POST', '/api/tasks/', { title: 'Test' })
    const items = await getAll()
    expect(items).toHaveLength(1)
    expect(items[0].method).toBe('POST')
    expect(items[0].url).toBe('/api/tasks/')
    expect(items[0].body).toEqual({ title: 'Test' })
    expect(items[0].attempt).toBe(0)
    expect(items[0].id).toBeDefined()
  })

  it('enqueue plusieurs mutations les trie par createdAt', async () => {
    await enqueue('POST', '/api/tasks/', { title: 'A' })
    await enqueue('PATCH', '/api/tasks/1/', { title: 'B' })
    await enqueue('DELETE', '/api/tasks/1/')
    const items = await getAll()
    expect(items).toHaveLength(3)
    expect(items[0].method).toBe('POST')
    expect(items[2].method).toBe('DELETE')
  })

  it('dequeue retire une mutation', async () => {
    const m = await enqueue('POST', '/api/tasks/', { title: 'X' })
    await dequeue(m.id)
    const items = await getAll()
    expect(items).toHaveLength(0)
  })

  it('clearAll vide la file', async () => {
    await enqueue('POST', '/api/tasks/', { title: 'A' })
    await enqueue('POST', '/api/tasks/', { title: 'B' })
    await clearAll()
    expect(await getAll()).toHaveLength(0)
  })

  it('flush rejoue les mutations et les retire en cas de succès', async () => {
    await enqueue('POST', '/api/tasks/', { title: 'A' })
    await enqueue('PATCH', '/api/tasks/1/', { title: 'B' })
    const sent: string[] = []
    const count = await flush(async (m) => { sent.push(m.url) })
    expect(count).toBe(2)
    expect(sent).toContain('/api/tasks/')
    expect(await getAll()).toHaveLength(0)
  })

  it('flush laisse les mutations en file si le sender échoue', async () => {
    await enqueue('POST', '/api/tasks/', { title: 'fail' })
    const count = await flush(async () => { throw new Error('réseau indisponible') })
    expect(count).toBe(0)
    expect(await getAll()).toHaveLength(1)
  })

  it('flush incrémente le numéro de tentative passé au sender', async () => {
    await enqueue('POST', '/api/tasks/', { title: 'retry' })
    let attempt = -1
    await flush(async (m) => { attempt = m.attempt }).catch(() => {})
    expect(attempt).toBe(1)
  })

  it('getAll retourne un tableau vide si la file est vide', async () => {
    expect(await getAll()).toEqual([])
  })
})
