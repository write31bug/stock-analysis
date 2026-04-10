import { describe, it, expect, vi, beforeEach } from 'vitest'

// Use vi.hoisted so these are available inside the hoisted vi.mock factory
const { mockGet, mockPost, mockDelete } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
  mockDelete: vi.fn(),
}))

vi.mock('axios', () => ({
  default: {
    create: () => ({
      get: mockGet,
      post: mockPost,
      delete: mockDelete,
      interceptors: {
        response: {
          use: vi.fn()
        }
      }
    }),
  },
}))

import {
  submitBatch,
  getBatchStatus,
  getSchedulerStatus,
  manualRefresh,
  getPortfolio,
  getWatchlist,
  addToWatchlist,
  removeFromWatchlist,
  getWatchlistGroups,
} from './index'

describe('API module', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('submitBatch should call POST /batch with correct params', async () => {
    mockPost.mockResolvedValue({ data: { task_id: 'abc123' } })
    const result = await submitBatch(['600519'], 'auto', 'stock', 60, true)
    expect(mockPost).toHaveBeenCalledWith('/batch', {
      codes: ['600519'],
      market: 'auto',
      asset_type: 'stock',
      days: 60,
      test: true,
    })
    expect(result).toEqual({ task_id: 'abc123' })
  })

  it('getBatchStatus should call GET /batch/:taskId', async () => {
    mockGet.mockResolvedValue({ data: { status: 'completed', progress: 100 } })
    const result = await getBatchStatus('abc123')
    expect(mockGet).toHaveBeenCalledWith('/batch/abc123')
    expect(result).toEqual({ status: 'completed', progress: 100 })
  })

  it('getSchedulerStatus should call GET /scheduler/status', async () => {
    mockGet.mockResolvedValue({ data: { running: true, interval: 180 } })
    const result = await getSchedulerStatus()
    expect(mockGet).toHaveBeenCalledWith('/scheduler/status')
    expect(result).toEqual({ running: true, interval: 180 })
  })

  it('manualRefresh should call POST /scheduler/refresh', async () => {
    mockPost.mockResolvedValue({ data: { task_id: 'refresh-001' } })
    const result = await manualRefresh()
    expect(mockPost).toHaveBeenCalledWith('/scheduler/refresh')
    expect(result).toEqual({ task_id: 'refresh-001' })
  })

  it('getPortfolio should call GET /portfolio', async () => {
    mockGet.mockResolvedValue({ data: [{ code: '600519', hold_amount: 1000 }] })
    const result = await getPortfolio()
    expect(mockGet).toHaveBeenCalledWith('/portfolio')
    expect(result).toEqual([{ code: '600519', hold_amount: 1000 }])
  })

  it('getWatchlist should call GET /watchlist', async () => {
    const mockData = [{ code: '600519', name: '贵州茅台', group: '默认' }]
    mockGet.mockResolvedValue({ data: mockData })
    const result = await getWatchlist()
    expect(mockGet).toHaveBeenCalledWith('/watchlist')
    expect(result).toEqual(mockData)
  })

  it('addToWatchlist should call POST /watchlist', async () => {
    mockPost.mockResolvedValue({ data: { success: true } })
    const result = await addToWatchlist('600519', '贵州茅台', '默认')
    expect(mockPost).toHaveBeenCalledWith('/watchlist', {
      code: '600519',
      name: '贵州茅台',
      group: '默认',
    })
    expect(result).toEqual({ success: true })
  })

  it('removeFromWatchlist should call DELETE /watchlist/:code', async () => {
    mockDelete.mockResolvedValue({ data: { success: true } })
    const result = await removeFromWatchlist('600519')
    expect(mockDelete).toHaveBeenCalledWith('/watchlist/600519')
    expect(result).toEqual({ success: true })
  })

  it('getWatchlistGroups should call GET /watchlist/groups', async () => {
    mockGet.mockResolvedValue({ data: ['默认', 'A股'] })
    const result = await getWatchlistGroups()
    expect(mockGet).toHaveBeenCalledWith('/watchlist/groups')
    expect(result).toEqual(['默认', 'A股'])
  })
})
