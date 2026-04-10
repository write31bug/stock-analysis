import axios from 'axios'
import type { AnalysisResult, WatchlistItem, PriceAlert } from '../types'

const api = axios.create({ baseURL: '/api', timeout: 60000 })

// 单股分析
export async function analyzeStock(code: string, market = 'auto', assetType = 'stock', days = 60, test = false) {
  const { data } = await api.get<AnalysisResult>(`/analyze/${code}`, {
    params: { market, asset_type: assetType, days, test },
  })
  return data
}

// 批量分析提交
export async function submitBatch(codes: string[], market = 'auto', assetType = 'stock', days = 60, test = true) {
  const { data } = await api.post('/batch', {
    codes,
    market,
    asset_type: assetType,
    days,
    test,
  })
  return data
}

// 批量进度查询
export async function getBatchStatus(taskId: string) {
  const { data } = await api.get(`/batch/${taskId}`)
  return data
}

// 自选股 CRUD
export async function getWatchlist() {
  const { data } = await api.get<WatchlistItem[]>('/watchlist')
  return data
}
export async function addToWatchlist(code: string, name = '', group?: string) {
  const { data } = await api.post('/watchlist', { code, name, group })
  return data
}
export async function removeFromWatchlist(code: string) {
  const { data } = await api.delete(`/watchlist/${code}`)
  return data
}

// 自选股分组
export async function getWatchlistGroups() {
  const { data } = await api.get<string[]>('/watchlist/groups')
  return data
}
export async function createGroup(name: string) {
  const { data } = await api.post('/watchlist/group', { name })
  return data
}
export async function deleteGroup(name: string) {
  const { data } = await api.delete(`/watchlist/group/${encodeURIComponent(name)}`)
  return data
}

// 导入持仓文件（到 portfolio 表）
export async function importPortfolio(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/portfolio/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

// 导入自选股文件（到 watchlist）
export async function importWatchlist(
  file: File,
  group = '默认',
  codeCol = '代码',
  nameCol = '名称',
) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/watchlist/import', formData, {
    params: { group, code_col: codeCol, name_col: nameCol },
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

// 价格预警
export async function getAlerts() {
  const { data } = await api.get<PriceAlert[]>('/alerts')
  return data
}
export async function createAlert(alertData: {
  code: string
  name: string
  condition_type: 'above' | 'below' | 'pct_change_above' | 'pct_change_below'
  target_value: number
}) {
  const { data } = await api.post('/alerts', alertData)
  return data
}
export async function deleteAlert(id: number) {
  const { data } = await api.delete(`/alerts/${id}`)
  return data
}
export async function checkAlerts() {
  const { data } = await api.post('/alerts/check')
  return data
}

// 历史记录
export async function getHistory(params?: {
  code?: string
  trend?: string
  start?: string
  end?: string
  page?: number
  size?: number
}) {
  const { data } = await api.get('/history', { params })
  return data
}
export async function getScoreTrend(code: string, days = 30) {
  const { data } = await api.get(`/score-trend/${code}`, { params: { days } })
  return data
}
export async function deleteHistory(id: number) {
  const { data } = await api.delete(`/history/${id}`)
  return data
}
export async function clearHistory() {
  const { data } = await api.delete('/history')
  return data
}
export async function saveHistory(result: AnalysisResult) {
  const { data } = await api.post('/history', result)
  return data
}

// 数据导出
export async function exportAnalysisCSV(params: {
  codes?: string[]
  market?: string
  asset_type?: string
  days?: number
}) {
  const { data } = await api.get('/export/csv', {
    params,
    responseType: 'blob',
  })
  return data as Blob
}
export async function exportHistoryCSV(params?: {
  code?: string
  trend?: string
  start?: string
  end?: string
}) {
  const { data } = await api.get('/export/history', {
    params,
    responseType: 'blob',
  })
  return data as Blob
}

// 定时采集服务
export async function getSchedulerStatus() {
  const { data } = await api.get('/scheduler/status')
  return data
}
export async function manualRefresh() {
  const { data } = await api.post('/scheduler/refresh')
  return data
}
export async function getRefreshStatus(taskId: string) {
  const { data } = await api.get(`/scheduler/refresh/${taskId}`)
  return data
}

// 持仓数据
export async function getPortfolio() {
  const { data } = await api.get('/portfolio')
  return data
}
export async function getPortfolioSummary() {
  const { data } = await api.get('/portfolio/summary')
  return data
}
export async function deletePortfolioItem(code: string) {
  const { data } = await api.delete(`/portfolio/${code}`)
  return data
}

// 系统设置
export async function getInterval() {
  const { data } = await api.get('/settings/interval')
  return data
}
export async function updateInterval(minutes: number) {
  const { data } = await api.put('/settings/interval', { interval_minutes: minutes })
  return data
}

// 系统日志
export async function getLogs(params?: { level?: string; limit?: number; offset?: number }) {
  const { data } = await api.get('/logs', { params })
  return data
}
export async function clearLogs() {
  const { data } = await api.delete('/logs')
  return data
}
