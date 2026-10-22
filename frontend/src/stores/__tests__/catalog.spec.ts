import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { Tier } from '@/api/types'
import { useAuthStore } from '../auth'
import { useCatalogStore } from '../catalog'

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

const tier = (id: number, level: number, extra: Partial<Tier> = {}): Tier => ({
  id,
  name: `T${id}`,
  level,
  default_reward: 10,
  color: null,
  is_archived: false,
  ...extra,
})

/** fetch, который отвечает по пути запроса. */
function routeFetch(routes: Record<string, () => unknown>) {
  const fetchMock = vi.fn<typeof fetch>(async (input) => {
    const path = String(input).replace('/api/v1', '').split('?')[0]!
    const handler = routes[path]
    return handler ? json(handler()) : json({ detail: 'not found' }, 404)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('catalog store', () => {
  beforeEach(() => setActivePinia(createPinia()))
  afterEach(() => vi.unstubAllGlobals())

  it('загружает справочники один раз на пользователя', async () => {
    const fetchMock = routeFetch({
      '/tiers': () => [tier(1, 1), tier(2, 2, { is_archived: true })],
      '/categories': () => [],
      '/rewards': () => [],
    })
    const auth = useAuthStore()
    auth.user = { id: 7 } as never
    const catalog = useCatalogStore()

    await catalog.load()
    await catalog.load()
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(catalog.activeTiers.map((t) => t.id)).toEqual([1])

    auth.user = { id: 8 } as never
    await catalog.load()
    expect(fetchMock).toHaveBeenCalledTimes(6)
  })

  it('saveTier обновляет список и держит сортировку по уровню', async () => {
    routeFetch({
      '/tiers': () => [tier(1, 1), tier(2, 3)],
      '/categories': () => [],
      '/rewards': () => [],
      '/tiers/1': () => tier(1, 4, { name: 'Поднят' }),
    })
    const catalog = useCatalogStore()
    await catalog.load()

    await catalog.saveTier(1, { level: 4 })

    expect(catalog.tiers.map((t) => [t.id, t.level])).toEqual([
      [2, 3],
      [1, 4],
    ])
    expect(catalog.tiers[1]!.name).toBe('Поднят')
  })

  it('удаление тира с переносом — квесты перечитываются', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockImplementation(async (url) =>
        String(url).includes('/tiers/')
          ? new Response(null, { status: 204 })
          : new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }),
      )
    vi.stubGlobal('fetch', fetchMock)
    const catalog = useCatalogStore()
    catalog.tiers = [tier(1, 1), tier(2, 2)]

    await catalog.removeTier(1, 2)

    expect(String(fetchMock.mock.calls[0]?.[0])).toMatch(/\/tiers\/1\?move_to=2$/)
    expect(fetchMock.mock.calls[0]?.[1]?.method).toBe('DELETE')
    expect(catalog.tiers.map((t) => t.id)).toEqual([2])
    // Квесты перечитаны: у них поменялся тир.
    expect(
      fetchMock.mock.calls.some(([url]) => String(url).includes('/quests?status=active')),
    ).toBe(true)
  })
})
