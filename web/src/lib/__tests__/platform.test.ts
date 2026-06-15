import { describe, it, expect, vi } from 'vitest'
import { webPlatform } from '@/platform/web'

// Simulation de l'environnement web sans vraies Notification API
describe('webPlatform', () => {
  it("a le nom 'web'", () => {
    expect(webPlatform.name).toBe('web')
  })

  it('store.set/get/remove fonctionne', async () => {
    await webPlatform.store.set('test_key', 'hello')
    expect(await webPlatform.store.get('test_key')).toBe('hello')
    await webPlatform.store.remove('test_key')
    expect(await webPlatform.store.get('test_key')).toBeNull()
  })

  it('isOffline() retourne un booléen', () => {
    expect(typeof webPlatform.isOffline()).toBe('boolean')
  })

  it('requestNotificationPermission() retourne false si Notification absent', async () => {
    // Dans Node/vitest, Notification n'est pas défini
    const result = await webPlatform.requestNotificationPermission()
    expect(result).toBe(false)
  })

  it('scheduleNotification() ne lance pas sans Notification API', async () => {
    // Ne doit pas throw
    await expect(webPlatform.scheduleNotification({ id: 1, title: 'T', body: 'B' })).resolves.toBeUndefined()
  })
})

describe('platform/index', () => {
  it('setPlatform() remplace la plateforme active', async () => {
    const { setPlatform } = await import('@/platform/index')
    const mockPlatform = { name: 'capacitor' as const, requestNotificationPermission: vi.fn(), scheduleNotification: vi.fn(), cancelNotification: vi.fn(), store: { get: vi.fn(), set: vi.fn(), remove: vi.fn() }, isOffline: vi.fn() }
    setPlatform(mockPlatform)
    const { platform } = await import('@/platform/index')
    expect(platform.name).toBe('capacitor')
    // Remettre web (cleanup)
    setPlatform(webPlatform)
  })
})
