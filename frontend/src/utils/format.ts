/**
 * 格式化工具函数
 * 从 Dashboard/Analysis/History 中提取的公共函数
 */

// 趋势颜色映射
export const trendColorMap: Record<string, string> = {
  强势上涨: '#ef5350',
  上涨趋势: '#FF9500',
  震荡整理: '#5B8FF9',
  下跌趋势: '#26a69a',
  强势下跌: '#61DDAA',
}

/**
 * 根据评分获取颜色
 */
export function getScoreColor(score: number | null): string {
  if (score == null) return '#9e9e9e'
  if (score >= 75) return '#ef5350'
  if (score >= 60) return '#FF9500'
  if (score >= 40) return '#5B8FF9'
  if (score >= 25) return '#26a69a'
  return '#61DDAA'
}

/**
 * 格式化价格
 */
export function formatPrice(price: number | null | undefined): string {
  if (price == null) return '--'
  return price.toFixed(2)
}

/**
 * 格式化百分比
 */
export function formatPct(pct: number | null | undefined): string {
  if (pct == null) return '--'
  const sign = pct >= 0 ? '+' : ''
  return `${sign}${pct.toFixed(2)}%`
}

/**
 * 根据涨跌幅获取颜色
 */
export function getPctColor(pct: number | null | undefined): string {
  if (pct == null) return '#9e9e9e'
  return pct >= 0 ? '#ef5350' : '#26a69a'
}

/**
 * 格式化时间 (MM-DD HH:mm)
 */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '--'
  const d = new Date(iso)
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hour = String(d.getHours()).padStart(2, '0')
  const minute = String(d.getMinutes()).padStart(2, '0')
  return `${month}-${day} ${hour}:${minute}`
}

/**
 * 格式化完整时间 (YYYY-MM-DD HH:mm:ss)
 */
export function formatFullDateTime(iso: string | null | undefined): string {
  if (!iso) return '--'
  const d = new Date(iso)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hour = String(d.getHours()).padStart(2, '0')
  const minute = String(d.getMinutes()).padStart(2, '0')
  const second = String(d.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hour}:${minute}:${second}`
}
