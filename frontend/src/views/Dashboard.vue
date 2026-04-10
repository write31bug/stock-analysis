<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, h } from 'vue'
import { useRouter } from 'vue-router'
import {
  NCard,
  NPageHeader,
  NInputGroup,
  NInput,
  NInputNumber,
  NButton,
  NDataTable,
  NTag,
  NGrid,
  NGridItem,
  NSpace,
  NStatistic,
  NEmpty,
  NSpin,
  NProgress,
  NText,
  NSelect,
  NPopconfirm,
  NModal,
  useMessage,
} from 'naive-ui'
import { use } from 'echarts/core'
import { PieChart, BarChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { useWatchlistStore } from '../stores/watchlist'
import { analyzeStock, submitBatch, getBatchStatus, exportAnalysisCSV, importWatchlist, importPortfolio, getSchedulerStatus, manualRefresh, getRefreshStatus, getPortfolio, deletePortfolioItem, getInterval, updateInterval } from '../api'
import type { AnalysisResult, WatchlistItem, MergedRow, PortfolioItem, BatchResultItem, BatchState, SchedulerState } from '../types'
import { trendColorMap, getScoreColor, formatPrice, formatPct, getPctColor, formatDateTime } from '../utils/format'
import SystemLogs from '../components/SystemLogs.vue'

// ---------- ECharts Registration ----------

use([PieChart, BarChart, CanvasRenderer, TooltipComponent, LegendComponent, GridComponent])

// ---------- Router & Message ----------

const router = useRouter()
const message = useMessage()

// ---------- Store ----------

const watchlistStore = useWatchlistStore()

// ---------- Watchlist Add Form ----------

const addCode = ref('')
const addName = ref('')
const addGroup = ref<string | null>(null)

async function handleAddToWatchlist() {
  const code = addCode.value.trim()
  if (!code) {
    message.warning('请输入股票代码')
    return
  }
  try {
    await watchlistStore.add(code, addName.value.trim(), addGroup.value ?? undefined)
    message.success(`已添加 ${code} 到自选股`)
    addCode.value = ''
    addName.value = ''
    addGroup.value = null
  } catch {
    message.error('添加失败，请检查代码是否正确')
  }
}

async function handleRemove(code: string) {
  try {
    // 同时删除自选股和持仓数据
    await Promise.all([
      watchlistStore.remove(code),
      deletePortfolioItem(code).catch(() => {}), // 持仓可能不存在，忽略错误
    ])
    message.success(`已移除 ${code}`)
    await fetchPortfolio() // 刷新持仓数据
  } catch {
    message.error('移除失败')
  }
}

function goToAnalysis(code: string) {
  // 根据代码自动判断资产类型
  const assetType = _guessAssetType(code)
  router.push(`/analysis/${code}?type=${assetType}`)
}

/** 根据代码前缀猜测资产类型 */
function _guessAssetType(code: string): string {
  if (/^(15|51|52|58|16|50)/.test(code)) return 'fund'
  if (/^(00|01|02|03)/.test(code)) return 'stock' // 00/01 开头默认股票（开放式基金需用户手动选）
  return 'stock'
}

// ---------- Group Management ----------

const newGroupName = ref('')
const showGroupModal = ref(false)

const groupSelectOptions = computed(() => {
  const options = [{ label: '全部分组', value: '__all__' }]
  for (const g of watchlistStore.groups) {
    options.push({ label: g, value: g })
  }
  return options
})

const addGroupOptions = computed(() => {
  return watchlistStore.groups.map((g) => ({ label: g, value: g }))
})

function handleGroupSelect(val: string) {
  if (val === '__all__') {
    watchlistStore.currentGroup = null
  } else {
    watchlistStore.currentGroup = val
  }
}

async function handleCreateGroup() {
  const name = newGroupName.value.trim()
  if (!name) {
    message.warning('请输入分组名称')
    return
  }
  try {
    await watchlistStore.addGroup(name)
    message.success(`分组 "${name}" 创建成功`)
    newGroupName.value = ''
    showGroupModal.value = false
  } catch {
    message.error('创建分组失败')
  }
}

async function handleDeleteGroup(name: string) {
  try {
    await watchlistStore.removeGroup(name)
    message.success(`分组 "${name}" 已删除`)
  } catch {
    message.error('删除分组失败')
  }
}

// ---------- Watchlist Table ----------

// ---------- Merged Table: Watchlist + Analysis Results ----------

// 从 batch results 建立查找表
const analysisMap = computed(() => {
  const map: Record<string, BatchResultItem> = {}
  for (const r of batch.value.results) {
    map[r.code] = r
  }
  return map
})

// 合并数据源：自选股 + 分析结果
const mergedTableData = computed<MergedRow[]>(() => {
  return watchlistStore.filteredItems.map((item) => {
    const analysis = analysisMap.value[item.code]
    const portfolio = portfolioMap.value[item.code]
    return {
      code: item.code,
      name: item.name || analysis?.name || portfolio?.name || '--',
      group: item.group,
      score: analysis?.score ?? null,
      trend: analysis?.trend ?? null,
      recommendation: analysis?.recommendation ?? null,
      success: analysis?.success,
      error: analysis?.error,
      hold_amount: portfolio?.hold_amount ?? null,
      day_pnl: portfolio?.day_pnl ?? null,
      day_pnl_pct: portfolio?.day_pnl_pct ?? null,
      hold_pnl: portfolio?.hold_pnl ?? null,
      hold_pnl_pct: portfolio?.hold_pnl_pct ?? null,
      position_pct: portfolio?.position_pct ?? null,
      hold_quantity: portfolio?.hold_quantity ?? null,
      created_at: portfolio?.created_at ?? null,
      updated_at: portfolio?.updated_at ?? null,
    }
  })
})

const mergedColumns = [
  {
    title: '代码',
    key: 'code',
    width: 110,
    render(row: MergedRow) {
      return h(NText, { strong: true }, () => row.code)
    },
  },
  {
    title: '名称',
    key: 'name',
    ellipsis: { tooltip: true },
    render(row: MergedRow) {
      return row.name || '--'
    },
  },
  {
    title: '分组',
    key: 'group',
    width: 80,
    render(row: MergedRow) {
      if (!row.group) return '--'
      return h(NTag, { size: 'small', type: 'info', bordered: false }, () => row.group)
    },
  },
  {
    title: '持仓金额',
    key: 'hold_amount',
    width: 100,
    align: 'right' as const,
    sorter: true,
    render(row: MergedRow) {
      if (row.hold_amount == null) return '--'
      return h(NText, {}, () => row.hold_amount!.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }))
    },
  },
  {
    title: '当日盈亏',
    key: 'day_pnl',
    width: 110,
    align: 'right' as const,
    sorter: true,
    render(row: MergedRow) {
      if (row.day_pnl == null) return '--'
      const val = row.day_pnl!
      const color = val >= 0 ? '#ef5350' : '#26a69a'
      const sign = val >= 0 ? '+' : ''
      const pctStr = row.day_pnl_pct != null ? ` (${row.day_pnl_pct! >= 0 ? '+' : ''}${row.day_pnl_pct!.toFixed(2)}%)` : ''
      return h(NText, { style: { color } }, () => `${sign}${val.toFixed(2)}${pctStr}`)
    },
  },
  {
    title: '持仓收益',
    key: 'hold_pnl',
    width: 110,
    align: 'right' as const,
    sorter: true,
    render(row: MergedRow) {
      if (row.hold_pnl == null) return '--'
      const val = row.hold_pnl!
      const color = val >= 0 ? '#ef5350' : '#26a69a'
      const sign = val >= 0 ? '+' : ''
      const pctStr = row.hold_pnl_pct != null ? ` (${row.hold_pnl_pct! >= 0 ? '+' : ''}${row.hold_pnl_pct!.toFixed(2)}%)` : ''
      return h(NText, { style: { color } }, () => `${sign}${val.toFixed(2)}${pctStr}`)
    },
  },
  {
    title: '持仓占比',
    key: 'position_pct',
    width: 90,
    align: 'right' as const,
    sorter: true,
    render(row: MergedRow) {
      if (row.position_pct == null) return '--'
      return h(NText, {}, () => `${row.position_pct!.toFixed(2)}%`)
    },
  },
  {
    title: '持仓数',
    key: 'hold_quantity',
    width: 90,
    align: 'right' as const,
    sorter: true,
    render(row: MergedRow) {
      if (row.hold_quantity == null) return '--'
      return h(NText, {}, () => {
        const q = row.hold_quantity!
        return q >= 10000 ? `${(q / 10000).toFixed(2)}万` : String(q)
      })
    },
  },
  {
    title: '评分',
    key: 'score',
    width: 70,
    align: 'center' as const,
    sorter: true,
    render(row: MergedRow) {
      if (row.score == null) {
        return row.error
          ? h(NText, { type: 'error', style: { fontSize: '12px' } }, () => '失败')
          : h(NText, { depth: 3, style: { fontSize: '12px' } }, () => '--')
      }
      const color =
        row.score >= 75
          ? '#ef5350'
          : row.score >= 60
            ? '#FF9500'
            : row.score >= 40
              ? '#5B8FF9'
              : row.score >= 25
                ? '#26a69a'
                : '#61DDAA'
      return h(NText, { style: { color, fontWeight: 600 } }, () => String(row.score))
    },
  },
  {
    title: '趋势',
    key: 'trend',
    width: 110,
    render(row: MergedRow) {
      if (!row.trend) return '--'
      const color = trendColorMap[row.trend] ?? '#999'
      return h(
        NTag,
        {
          size: 'small',
          round: true,
          bordered: false,
          style: { backgroundColor: color, color: '#fff' },
        },
        () => row.trend,
      )
    },
  },
  {
    title: '建议',
    key: 'recommendation',
    ellipsis: { tooltip: true },
    render(row: MergedRow) {
      return row.recommendation || '--'
    },
  },
  {
    title: '导入时间',
    key: 'created_at',
    width: 100,
    align: 'center' as const,
    sorter: true,
    render(row: MergedRow) {
      if (!row.created_at) return '--'
      const date = new Date(row.created_at)
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      const hour = String(date.getHours()).padStart(2, '0')
      const minute = String(date.getMinutes()).padStart(2, '0')
      return h(NText, { depth: 3, style: { fontSize: '12px' } }, () => `${month}-${day} ${hour}:${minute}`)
    },
  },
  {
    title: '分析时间',
    key: 'updated_at',
    width: 100,
    align: 'center' as const,
    sorter: true,
    render(row: MergedRow) {
      if (!row.updated_at) return '--'
      const date = new Date(row.updated_at)
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      const hour = String(date.getHours()).padStart(2, '0')
      const minute = String(date.getMinutes()).padStart(2, '0')
      return h(NText, { depth: 3, style: { fontSize: '12px' } }, () => `${month}-${day} ${hour}:${minute}`)
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    render(row: MergedRow) {
      return h(NSpace, { size: 8 }, () => [
        h(
          NButton,
          {
            size: 'small',
            type: 'primary',
            secondary: true,
            onClick: () => goToAnalysis(row.code),
          },
          () => '详情',
        ),
        h(
          NButton,
          {
            size: 'small',
            type: 'error',
            secondary: true,
            onClick: () => handleRemove(row.code),
          },
          () => '删除',
        ),
      ])
    },
  },
]

// ---------- Batch Analysis ----------

const batch = ref<BatchState>({
  running: false,
  progress: 0,
  total: 0,
  completed: 0,
  failed: 0,
  results: [],
})

// ---------- Import Holdings ----------

const importing = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

function triggerImport() {
  fileInputRef.value?.click()
}

async function handleImportFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  importing.value = true
  try {
    // 预读文件内容，避免 File 对象被消费后不可重用
    const buffer = await file.arrayBuffer()
    const blob1 = new Blob([buffer], { type: file.type })
    const blob2 = new Blob([buffer], { type: file.type })
    const file1 = new File([blob1], file.name, { type: file.type })
    const file2 = new File([blob2], file.name, { type: file.type })

    // 同时导入到 portfolio 和 watchlist
    const group = watchlistStore.currentGroup || ''
    const [portfolioResult, watchlistResult] = await Promise.all([
      importPortfolio(file1),
      importWatchlist(file2, group),
    ])
    message.success(`${portfolioResult.message}；${watchlistResult.message}`)
    await watchlistStore.fetch()
    await watchlistStore.fetchGroups()
    await fetchPortfolio()
  } catch (e: any) {
    const detail = e.response?.data?.detail || e.message || '导入失败'
    message.error(detail)
  } finally {
    importing.value = false
    input.value = ''
  }
}

// ---------- Scheduler Status ----------

const schedulerInfo = ref<{
  running: boolean
  last_run: string | null
  next_run: number | null
  total_collected: number
  total_failed: number
} | null>(null)

const refreshing = ref(false)

// ---------- Portfolio Data ----------

const portfolioMap = computed<Record<string, PortfolioItem>>(() => {
  return portfolioData.value.reduce<Record<string, PortfolioItem>>((map, item) => {
    map[item.code] = item
    return map
  }, {})
})

const portfolioData = ref<PortfolioItem[]>([])

async function fetchPortfolio() {
  try {
    portfolioData.value = await getPortfolio()
    console.log('[Portfolio] 获取到', portfolioData.value.length, '条持仓数据')
    if (portfolioData.value.length > 0) {
      console.log('[Portfolio] 第一条:', JSON.stringify(portfolioData.value[0]))
    }
  } catch (e) {
    console.error('[Portfolio] 获取失败:', e)
  }
}

async function fetchSchedulerStatus() {
  try {
    schedulerInfo.value = await getSchedulerStatus()
  } catch {
    // ignore
  }
}

function formatLastRun(iso: string | null): string {
  if (!iso) return '尚未采集'
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour} 小时前`
  return d.toLocaleString('zh-CN')
}

// ---------- 采集间隔配置 ----------
const collectInterval = ref(3)
const intervalSaving = ref(false)

async function fetchInterval() {
  try {
    const res = await getInterval()
    collectInterval.value = res.interval_minutes
  } catch { /* ignore */ }
}

async function handleIntervalChange(val: number | null) {
  if (!val || val < 1) return
  intervalSaving.value = true
  try {
    const res = await updateInterval(val)
    if (res.success) {
      message.success(res.message)
      collectInterval.value = val
      await fetchSchedulerStatus()
    } else {
      message.error(res.message)
    }
  } catch {
    message.error('修改间隔失败')
  } finally {
    intervalSaving.value = false
  }
}

// ---------- System Logs (组件化) ----------

const systemLogsRef = ref<InstanceType<typeof SystemLogs> | null>(null)

let refreshPollTimer: ReturnType<typeof setInterval> | null = null

async function handleManualRefresh() {
  refreshing.value = true
  try {
    const resp = await manualRefresh()
    const taskId: string = resp.task_id ?? resp
    message.info('正在后台采集数据...')

    refreshPollTimer = setInterval(async () => {
      try {
        const status = await getRefreshStatus(taskId)
        if (status.status === 'completed') {
          clearInterval(refreshPollTimer!)
          refreshPollTimer = null
          refreshing.value = false
          message.success(status.message || `采集完成：成功 ${status.collected}，失败 ${status.failed}`)
          await fetchSchedulerStatus()
          // 自动用离线模式加载结果到表格（秒出）
          await loadCachedResults()
        }
      } catch {
        // continue polling
      }
    }, 3000)
  } catch (e: any) {
    refreshing.value = false
    message.error(e.response?.data?.detail || '触发刷新失败')
  }
}

onUnmounted(() => {
  stopPolling()
  if (refreshPollTimer) {
    clearInterval(refreshPollTimer)
    refreshPollTimer = null
  }
})

// ---------- Load Cached Results ----------

async function loadCachedResults() {
  try {
    const resp = await submitBatch(
      watchlistStore.filteredItems.map((item) => item.code),
      'auto',
      'stock',
      60,
      true,
    )
    const taskId: string = resp.task_id ?? resp.id ?? resp
    startPolling(taskId)
  } catch {
    // ignore
  }
}

let pollTimer: ReturnType<typeof setInterval> | null = null

async function handleBatchAnalyze() {
  const itemsToAnalyze = watchlistStore.filteredItems
  if (itemsToAnalyze.length === 0) {
    message.warning('自选股列表为空，请先添加股票')
    return
  }

  const codes = itemsToAnalyze.map((item) => item.code)

  try {
    batch.value = {
      running: true,
      progress: 0,
      total: codes.length,
      completed: 0,
      failed: 0,
      results: [],
    }

    const resp = await submitBatch(codes, 'auto', 'stock', 60, false)
    const taskId: string = resp.task_id ?? resp.id ?? resp

    startPolling(taskId)
  } catch {
    message.error('批量分析提交失败，请稍后重试')
    batch.value.running = false
  }
}

function startPolling(taskId: string) {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const status = await getBatchStatus(taskId)

      batch.value.progress = status.progress ?? 0
      batch.value.completed = status.completed ?? 0
      batch.value.failed = status.failed ?? 0

      if (status.status === 'completed' || status.status === 'done') {
        stopPolling()
        batch.value.running = false
        batch.value.results = (status.results ?? []).map((r: Record<string, any>) => {
          const stockInfo = r.stock_info ?? {}
          const analysis = r.analysis ?? {}
          return {
            code: (stockInfo.code as string) ?? (r.code as string) ?? '',
            name: (stockInfo.name as string) ?? (r.name as string) ?? '--',
            score: (analysis.score as number) ?? (r.score as number) ?? null,
            trend: (analysis.trend as string) ?? (r.trend as string) ?? null,
            recommendation: (analysis.recommendation as string) ?? (r.recommendation as string) ?? null,
            success: !r.error,
            error: (r.error as string) ?? undefined,
          }
        })
        message.success('批量分析完成')
      } else if (status.status === 'failed' || status.status === 'error') {
        stopPolling()
        batch.value.running = false
        message.error('批量分析失败')
      }
    } catch {
      // polling error - continue trying
    }
  }, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// ---------- Batch Summary Stats ----------

const batchSummary = computed(() => {
  const results = batch.value.results
  if (results.length === 0) return null

  const valid = results.filter((r) => r.success && r.score != null)
  const failed = results.filter((r) => !r.success)
  const avgScore = valid.length > 0 ? valid.reduce((sum, r) => sum + (r.score ?? 0), 0) / valid.length : 0

  return {
    total: results.length,
    valid: valid.length,
    failed: failed.length,
    avgScore: Math.round(avgScore * 10) / 10,
  }
})

// ---------- Trend Distribution Pie Chart ----------

const trendPieOption = computed(() => {
  const results = batch.value.results.filter((r) => r.success && r.trend)
  const trendCount: Record<string, number> = {}

  for (const r of results) {
    const trend = r.trend!
    trendCount[trend] = (trendCount[trend] ?? 0) + 1
  }

  const data = Object.entries(trendCount).map(([name, value]) => ({
    name,
    value,
    itemStyle: { color: trendColorMap[name] ?? '#999' },
  }))

  return {
    tooltip: {
      trigger: 'item' as const,
      formatter: '{b}: {c} ({d}%)',
    },
    legend: {
      orient: 'horizontal' as const,
      bottom: 0,
      textStyle: { color: '#ccc', fontSize: 12 },
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#333',
          borderWidth: 2,
        },
        label: {
          show: true,
          color: '#ccc',
          formatter: '{b}\n{d}%',
        },
        data,
      },
    ],
  }
})

// ---------- Score Distribution Bar Chart ----------

const scoreBarOption = computed(() => {
  const results = batch.value.results.filter((r) => r.success && r.score != null)
  const ranges = [
    { label: '0-20', min: 0, max: 20 },
    { label: '20-40', min: 20, max: 40 },
    { label: '40-60', min: 40, max: 60 },
    { label: '60-80', min: 60, max: 80 },
    { label: '80-100', min: 80, max: 100 },
  ]

  const counts = ranges.map((range) => {
    return results.filter((r) => r.score! >= range.min && r.score! < (range.max === 100 ? 101 : range.max)).length
  })

  return {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'shadow' as const },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '8%',
      containLabel: true,
    },
    xAxis: {
      type: 'category' as const,
      data: ranges.map((r) => r.label),
      axisLabel: { color: '#ccc' },
      axisLine: { lineStyle: { color: '#555' } },
    },
    yAxis: {
      type: 'value' as const,
      minInterval: 1,
      axisLabel: { color: '#ccc' },
      splitLine: { lineStyle: { color: '#444' } },
    },
    series: [
      {
        type: 'bar',
        data: counts,
        barWidth: '50%',
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: '#5B8FF9' },
              { offset: 1, color: '#5B8FF966' },
            ],
          },
        },
      },
    ],
  }
})

// ---------- Batch Results Table ----------

// ---------- Quick Analysis ----------

const quickCode = ref('')
const quickLoading = ref(false)
const quickResult = ref<AnalysisResult | null>(null)

async function handleQuickAnalyze() {
  const code = quickCode.value.trim()
  if (!code) {
    message.warning('请输入股票代码')
    return
  }

  quickLoading.value = true
  quickResult.value = null

  try {
    quickResult.value = await analyzeStock(code)
    message.success(`${quickResult.value.stock_info.name} 分析完成`)
  } catch {
    message.error('分析失败，请检查代码是否正确')
  } finally {
    quickLoading.value = false
  }
}

function getQuickScoreColor(score: number): string {
  if (score >= 75) return '#ef5350'
  if (score >= 60) return '#FF9500'
  if (score >= 40) return '#5B8FF9'
  if (score >= 25) return '#26a69a'
  return '#61DDAA'
}

// ---------- Export CSV ----------

const exporting = ref(false)

function downloadCSV(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

async function handleExportAnalysis() {
  if (batch.value.results.length === 0) {
    message.warning('暂无分析结果可导出')
    return
  }
  exporting.value = true
  try {
    const codes = batch.value.results.filter((r) => r.success).map((r) => r.code)
    const blob = await exportAnalysisCSV({ codes })
    const now = new Date()
    const dateStr = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`
    downloadCSV(blob, `分析结果_${dateStr}.csv`)
    message.success('导出成功')
  } catch {
    message.error('导出失败')
  } finally {
    exporting.value = false
  }
}

// ---------- Lifecycle ----------

onMounted(() => {
  watchlistStore.fetch()
  watchlistStore.fetchGroups()
  fetchSchedulerStatus()
  fetchPortfolio()
  fetchInterval()
})
</script>

<template>
  <div class="dashboard-page">
    <!-- ==================== Page Header ==================== -->
    <NCard :bordered="false" class="header-card">
      <NPageHeader title="股票技术分析仪表盘" subtitle="自选股管理 / 批量分析 / 快速查询" />
    </NCard>

    <!-- ==================== Watchlist Management ==================== -->
    <NCard title="自选股管理" :bordered="false">
      <!-- Add Form -->
      <NSpace vertical :size="12">
        <NSpace :size="8" :wrap="true">
          <NInputGroup>
            <NInput
              v-model:value="addCode"
              placeholder="股票代码"
              clearable
              style="width: 140px"
              @keyup.enter="handleAddToWatchlist"
            />
            <NInput
              v-model:value="addName"
              placeholder="名称（可选）"
              clearable
              style="width: 140px"
              @keyup.enter="handleAddToWatchlist"
            />
          </NInputGroup>
          <NSelect
            v-model:value="addGroup"
            :options="addGroupOptions"
            placeholder="分组（可选）"
            clearable
            style="width: 140px"
          />
          <NButton type="primary" @click="handleAddToWatchlist"> 添加到自选 </NButton>
        </NSpace>

        <!-- Group Tabs & Management -->
        <NSpace :size="8" align="center" :wrap="true">
          <NSelect
            :value="watchlistStore.currentGroup ?? '__all__'"
            :options="groupSelectOptions"
            style="width: 160px"
            size="small"
            @update:value="handleGroupSelect"
          />
          <NButton size="small" type="info" secondary @click="showGroupModal = true">
            添加分组
          </NButton>
          <NPopconfirm
            v-if="watchlistStore.currentGroup"
            @positive-click="handleDeleteGroup(watchlistStore.currentGroup!)"
          >
            <template #trigger>
              <NButton size="small" type="error" secondary> 删除当前分组 </NButton>
            </template>
            <span>确定删除分组 "{{ watchlistStore.currentGroup }}"？分组内的股票不会被删除。</span>
          </NPopconfirm>
        </NSpace>

        <!-- Batch Action -->
        <NSpace :size="8" align="center">
          <NButton :loading="importing" secondary @click="triggerImport">
            📥 导入持仓
          </NButton>
          <input
            ref="fileInputRef"
            type="file"
            accept=".xlsx,.xls,.csv"
            style="display: none;"
            @change="handleImportFile"
          />
          <NButton
            type="warning"
            :disabled="watchlistStore.filteredItems.length === 0 || batch.running"
            :loading="batch.running"
            @click="handleBatchAnalyze"
          >
            一键分析全部
          </NButton>
          <NButton
            :loading="refreshing"
            :disabled="refreshing"
            secondary
            type="info"
            @click="handleManualRefresh"
          >
            🔄 刷新数据
          </NButton>
          <NText v-if="batch.running" depth="3" style="font-size: 12px;">
            正在分析... {{ batch.completed }} / {{ batch.total }}
          </NText>
        </NSpace>

        <!-- Scheduler Status -->
        <NSpace v-if="schedulerInfo" :size="12" align="center" style="font-size: 12px;">
          <NText depth="3">
            📡 定时采集：{{ schedulerInfo.running ? '运行中' : '已停止' }}
          </NText>
          <NText depth="3">
            最后更新：{{ formatLastRun(schedulerInfo.last_run) }}
          </NText>
          <NText v-if="schedulerInfo.total_collected > 0" depth="3">
            累计采集 {{ schedulerInfo.total_collected }} 次
          </NText>
          <NText depth="3">|</NText>
          <NText depth="3">间隔：</NText>
          <NInputNumber
            :value="collectInterval"
            :min="1"
            :max="60"
            size="small"
            :disabled="intervalSaving"
            style="width: 80px"
            @update:value="handleIntervalChange"
          />
          <NText depth="3">分钟</NText>
        </NSpace>

        <!-- Batch Progress -->
        <NProgress
          v-if="batch.running"
          type="line"
          :percentage="Math.round(batch.progress)"
          :height="8"
          status="info"
          style="max-width: 480px"
        />

        <!-- Merged Table: Watchlist + Analysis -->
        <NSpin :show="watchlistStore.loading">
          <NDataTable
            v-if="mergedTableData.length > 0"
            :columns="mergedColumns"
            :data="mergedTableData"
            :bordered="false"
            :single-line="false"
            size="small"
            :row-key="(row: MergedRow) => row.code"
            :scroll-x="750"
            :max-height="520"
            :virtual-scroll="mergedTableData.length > 20"
          />
          <NEmpty v-else description="暂无自选股，请添加股票代码" style="padding: 32px 0" />
        </NSpin>
      </NSpace>
    </NCard>

    <!-- ==================== Batch Analysis Results ==================== -->
    <template v-if="batchSummary">
      <NCard title="批量分析结果" :bordered="false">
        <NSpace vertical :size="12">
          <!-- Summary Stats -->
          <NGrid :x-gap="16" :y-gap="12" responsive="screen" item-responsive :cols="{ s: 2, m: 4 }">
            <NGridItem span="1">
              <NStatistic label="总计" :value="batchSummary.total" />
            </NGridItem>
            <NGridItem span="1">
              <NStatistic label="成功" :value="batchSummary.valid">
                <template #suffix>
                  <NText type="success"> / {{ batchSummary.total }}</NText>
                </template>
              </NStatistic>
            </NGridItem>
            <NGridItem span="1">
              <NStatistic label="失败" :value="batchSummary.failed">
                <template #suffix>
                  <NText v-if="batchSummary.failed > 0" type="error"> / {{ batchSummary.total }}</NText>
                </template>
              </NStatistic>
            </NGridItem>
            <NGridItem span="1">
              <NStatistic label="平均评分" :value="batchSummary.avgScore" />
            </NGridItem>
          </NGrid>

          <!-- Export Button -->
          <NSpace :size="8">
            <NButton type="info" :loading="exporting" @click="handleExportAnalysis">
              导出分析结果
            </NButton>
          </NSpace>
        </NSpace>
      </NCard>

      <!-- Charts -->
      <NGrid :x-gap="16" :y-gap="16" responsive="screen" item-responsive :cols="{ s: 1, m: 2 }">
        <NGridItem span="1">
          <NCard title="趋势分布" :bordered="false">
            <VChart v-if="batch.results.length > 0" :option="trendPieOption" style="height: 320px" autoresize />
            <NEmpty v-else description="暂无数据" />
          </NCard>
        </NGridItem>
        <NGridItem span="1">
          <NCard title="评分分布" :bordered="false">
            <VChart v-if="batch.results.length > 0" :option="scoreBarOption" style="height: 320px" autoresize />
            <NEmpty v-else description="暂无数据" />
          </NCard>
        </NGridItem>
      </NGrid>
    </template>

    <!-- ==================== Quick Analysis ==================== -->
    <NCard title="快速分析" :bordered="false">
      <NSpace vertical :size="16">
        <NSpace :size="8" :wrap="true">
          <NInput
            v-model:value="quickCode"
            placeholder="输入股票代码快速分析"
            clearable
            style="width: 240px"
            @keyup.enter="handleQuickAnalyze"
          />
          <NButton type="primary" :loading="quickLoading" @click="handleQuickAnalyze"> 分析 </NButton>
        </NSpace>

        <!-- Quick Result Card -->
        <div v-if="quickResult" class="quick-result-card">
          <NSpace :size="24" align="center" :wrap="true">
            <div class="quick-result-info">
              <div class="quick-result-name">
                {{ quickResult.stock_info.name }}
                <NTag size="small" :bordered="false" type="info" style="margin-left: 8px">
                  {{ quickResult.stock_info.code }}
                </NTag>
              </div>
              <div class="quick-result-price">
                {{ formatPrice(quickResult.stock_info.current_price) }}
              </div>
            </div>
            <div class="quick-result-score">
              <div
                class="quick-score-value"
                :style="{
                  color: getQuickScoreColor(quickResult.analysis.score),
                }"
              >
                {{ quickResult.analysis.score }}
              </div>
              <div class="quick-score-label">评分</div>
            </div>
            <div>
              <NTag
                size="medium"
                round
                :bordered="false"
                :style="{
                  backgroundColor: trendColorMap[quickResult.analysis.trend] ?? '#999',
                  color: '#fff',
                }"
              >
                {{ quickResult.analysis.trend }}
              </NTag>
            </div>
            <NButton size="small" type="primary" secondary @click="goToAnalysis(quickResult.stock_info.code)">
              查看完整分析
            </NButton>
          </NSpace>
        </div>

        <NSpin v-if="quickLoading" size="small" style="padding: 16px 0">
          <NText depth="3">正在分析中...</NText>
        </NSpin>
      </NSpace>
    </NCard>

    <!-- ==================== Add Group Modal ==================== -->
    <NModal v-model:show="showGroupModal" preset="dialog" title="添加分组">
      <NSpace vertical :size="12" style="margin-top: 12px">
        <NInput
          v-model:value="newGroupName"
          placeholder="输入分组名称"
          clearable
          @keyup.enter="handleCreateGroup"
        />
        <NSpace :size="8" justify="end">
          <NButton @click="showGroupModal = false">取消</NButton>
          <NButton type="primary" @click="handleCreateGroup">确定</NButton>
        </NSpace>
      </NSpace>
    </NModal>

    <!-- ==================== 系统日志 ==================== -->
    <SystemLogs ref="systemLogsRef" />
  </div>
</template>

<style scoped>
.dashboard-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ---------- Header ---------- */
.header-card :deep(.n-page-header) {
  padding: 0;
}

.header-card :deep(.n-page-header .n-page-header__title) {
  font-size: 24px;
  font-weight: 700;
}

/* ---------- Quick Result ---------- */
.quick-result-card {
  background: var(--card-color-2, rgba(255, 255, 255, 0.03));
  border: 1px solid var(--border-color-2, rgba(255, 255, 255, 0.08));
  border-radius: 8px;
  padding: 16px 20px;
}

.quick-result-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.quick-result-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-color-1, #fff);
  display: flex;
  align-items: center;
}

.quick-result-price {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-color-1, #fff);
  font-variant-numeric: tabular-nums;
}

.quick-result-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.quick-score-value {
  font-size: 32px;
  font-weight: 700;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.quick-score-label {
  font-size: 12px;
  color: var(--text-color-3, #999);
}

/* ---------- Responsive ---------- */
@media (max-width: 768px) {
  .dashboard-page {
    padding: 8px;
    gap: 10px;
  }

  .quick-result-card {
    padding: 12px 14px;
  }

  .quick-result-price {
    font-size: 20px;
  }

  .quick-score-value {
    font-size: 26px;
  }
}
</style>
