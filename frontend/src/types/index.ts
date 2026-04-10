export interface OHLCVItem {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface SeriesPoint {
  date: string
  value: number | null
}

export interface StockInfo {
  code: string
  name: string
  market: string
  asset_type: string
  current_price: number | null
  change_pct: number | null
}

export interface AnalysisResult {
  stock_info: StockInfo
  technical_indicators: Record<string, any>
  key_levels: Record<string, any>
  analysis: {
    score: number
    trend: string
    recommendation: string
    summary: string
  }
  ohlcv: OHLCVItem[]
  indicator_series: Record<string, SeriesPoint[]>
}

export interface HistoryRecord {
  id: number
  code: string
  name: string | null
  score: number | null
  trend: string | null
  current_price: number | null
  change_pct: number | null
  analysis_time: string
}

export interface WatchlistItem {
  code: string
  name: string
  group?: string
}

export interface PriceAlert {
  id: number
  code: string
  name: string
  condition_type: 'above' | 'below' | 'pct_change_above' | 'pct_change_below'
  target_value: number
  current_price: number | null
  triggered: boolean
  created_at: string
  triggered_at: string | null
}

// ========== Dashboard 相关类型 ==========

/** 持仓数据项 */
export interface PortfolioItem {
  code: string
  name: string
  hold_amount: number | null
  day_pnl: number | null
  day_pnl_pct: number | null
  hold_pnl: number | null
  hold_pnl_pct: number | null
  position_pct: number | null
  hold_quantity: number | null
  created_at: string | null
  updated_at: string | null
}

/** 合并表格行（自选股 + 分析结果 + 持仓数据） */
export interface MergedRow {
  code: string
  name: string
  group?: string
  score: number | null
  trend: string | null
  recommendation: string | null
  success?: boolean
  error?: string
  hold_amount: number | null
  day_pnl: number | null
  day_pnl_pct: number | null
  hold_pnl: number | null
  hold_pnl_pct: number | null
  position_pct: number | null
  hold_quantity: number | null
  created_at: string | null
  updated_at: string | null
}

/** 批量分析结果项 */
export interface BatchResultItem {
  code: string
  name: string
  score: number | null
  trend: string | null
  recommendation: string | null
  success: boolean
  error?: string
}

/** 批量分析状态 */
export interface BatchState {
  running: boolean
  progress: number
  total: number
  completed: number
  failed: number
  results: BatchResultItem[]
}

/** 系统日志项 */
export interface LogItem {
  id: number
  level: string
  module: string | null
  message: string
  created_at: string | null
}

/** 调度器状态 */
export interface SchedulerState {
  running: boolean
  last_run: string | null
  last_status: Record<string, any> | null
  next_run: number | null
  interval: number
  total_collected: number
  total_failed: number
}
