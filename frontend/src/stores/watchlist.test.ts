import { setActivePinia, createPinia } from 'pinia'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useWatchlistStore } from './watchlist'

// Mock the API functions that the store actually imports
vi.mock('../api', () => ({
  getWatchlist: vi.fn(),
  getWatchlistGroups: vi.fn(),
  addToWatchlist: vi.fn(),
  removeFromWatchlist: vi.fn(),
  createGroup: vi.fn(),
  deleteGroup: vi.fn(),
}))

import { getWatchlist, getWatchlistGroups, removeFromWatchlist } from '../api'

describe('WatchlistStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('initial state should be empty', () => {
    const store = useWatchlistStore()
    expect(store.items).toEqual([])
    expect(store.groups).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.currentGroup).toBeNull()
  })

  it('fetch should populate items', async () => {
    const store = useWatchlistStore()
    ;(getWatchlist as any).mockResolvedValue([
      { code: '600519', name: '贵州茅台', group: '默认' },
      { code: '000001', name: '平安银行', group: '默认' },
    ])

    await store.fetch()
    expect(store.items).toHaveLength(2)
    expect(store.items[0].code).toBe('600519')
    expect(store.loading).toBe(false)
  })

  it('fetch should set loading to true during fetch', async () => {
    const store = useWatchlistStore()
    let resolvePromise: (value: any) => void
    ;(getWatchlist as any).mockReturnValue(
      new Promise((resolve) => {
        resolvePromise = resolve
      }),
    )

    const fetchPromise = store.fetch()
    expect(store.loading).toBe(true)

    resolvePromise!([{ code: '600519', name: '贵州茅台' }])
    await fetchPromise
    expect(store.loading).toBe(false)
  })

  it('remove should call apiRemove and re-fetch items', async () => {
    const store = useWatchlistStore()
    store.items = [
      { code: '600519', name: '贵州茅台', group: '默认' },
      { code: '000001', name: '平安银行', group: '默认' },
    ]
    ;(removeFromWatchlist as any).mockResolvedValue({})
    ;(getWatchlist as any).mockResolvedValue([{ code: '000001', name: '平安银行', group: '默认' }])

    await store.remove('600519')
    expect(removeFromWatchlist).toHaveBeenCalledWith('600519')
    expect(store.items).toHaveLength(1)
    expect(store.items[0].code).toBe('000001')
  })

  it('filteredItems should filter by currentGroup', () => {
    const store = useWatchlistStore()
    store.items = [
      { code: '600519', name: '贵州茅台', group: 'A股' },
      { code: '159797', name: '医疗器材', group: 'ETF' },
      { code: '000001', name: '平安银行', group: 'A股' },
    ]
    store.currentGroup = 'A股'
    expect(store.filteredItems).toHaveLength(2)
    expect(store.filteredItems.every((item) => item.group === 'A股')).toBe(true)
  })

  it('filteredItems should return all when currentGroup is null', () => {
    const store = useWatchlistStore()
    store.items = [
      { code: '600519', name: '贵州茅台', group: 'A股' },
      { code: '159797', name: '医疗器材', group: 'ETF' },
    ]
    store.currentGroup = null
    expect(store.filteredItems).toHaveLength(2)
  })

  it('fetchGroups should populate groups', async () => {
    const store = useWatchlistStore()
    ;(getWatchlistGroups as any).mockResolvedValue(['默认', 'A股'])

    await store.fetchGroups()
    expect(store.groups).toEqual(['默认', 'A股'])
  })

  it('fetchGroups should set groups to empty on error', async () => {
    const store = useWatchlistStore()
    ;(getWatchlistGroups as any).mockRejectedValue(new Error('Network error'))

    await store.fetchGroups()
    expect(store.groups).toEqual([])
  })

  it('removeGroup should reset currentGroup if it matches the deleted group', async () => {
    const store = useWatchlistStore()
    store.currentGroup = 'A股'
    ;(getWatchlistGroups as any).mockResolvedValue([])
    ;(getWatchlist as any).mockResolvedValue([])

    await store.removeGroup('A股')
    expect(store.currentGroup).toBeNull()
  })
})
