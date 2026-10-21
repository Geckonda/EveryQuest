import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope, nextTick, ref } from 'vue'
import { useNow } from '../useNow'

describe('useNow', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-21T12:00:00.000Z'))
  })
  afterEach(() => vi.useRealTimers())

  it('медленно по умолчанию, раз в секунду, пока кто-то просит', async () => {
    const fast = ref(false)
    const scope = effectScope()
    const now = scope.run(() => useNow(() => fast.value))!

    vi.advanceTimersByTime(1_000)
    expect(now.value.toISOString()).toBe('2026-10-21T12:00:00.000Z')
    vi.advanceTimersByTime(29_000)
    expect(now.value.toISOString()).toBe('2026-10-21T12:00:30.000Z')

    fast.value = true
    await nextTick()
    vi.advanceTimersByTime(1_000)
    expect(now.value.toISOString()).toBe('2026-10-21T12:00:31.000Z')

    fast.value = false
    await nextTick()
    vi.advanceTimersByTime(1_000)
    expect(now.value.toISOString()).toBe('2026-10-21T12:00:31.000Z')

    scope.stop()
  })

  it('условие пересчитывается со временем', async () => {
    const due = new Date('2026-10-21T13:00:30.000Z').getTime()
    const scope = effectScope()
    const now = scope.run(() => useNow((n) => due - n.getTime() < 60 * 60 * 1000))!

    // Async: watcher условия срабатывает в микрозадаче после тика.
    await vi.advanceTimersByTimeAsync(30_000) // 12:00:30 — до срока ровно час, ещё медленно
    await vi.advanceTimersByTimeAsync(30_000) // 12:01:00 — меньше часа, переключились на секунды
    await vi.advanceTimersByTimeAsync(1_000)
    expect(now.value.toISOString()).toBe('2026-10-21T12:01:01.000Z')

    scope.stop()
  })

  it('без подписчиков не тикает', () => {
    const scope = effectScope()
    const now = scope.run(() => useNow())!
    scope.stop()

    vi.advanceTimersByTime(60_000)
    expect(now.value.toISOString()).toBe('2026-10-21T12:00:00.000Z')
    expect(vi.getTimerCount()).toBe(0)
  })
})
