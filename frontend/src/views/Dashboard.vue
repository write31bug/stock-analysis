<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, h } from 'vue'
import { useRouter } from 'vue-router'
import {
  NCard,
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

use([PieChart, BarChart, CanvasRenderer, TooltipComponent, LegendComponent, GridComponent])

const router = useRouter()
const message = useMessage()
const watchlistStore = useWatchlistStore()

const addCode = ref('')
const addName = ref('')
const addGroup = ref<string | null>(null)
const newGroupName = ref('')
const showGroupModal = ref(false)
const quickCode = ref('')
const quickLoading = ref(false)
const quickResult = ref<AnalysisResult | null>(null)
const exporting = ref(false)
const refreshing = ref(false)

const batch = ref<BatchState>({
  running: false,
  progress: 0,
  total: 0,
  completed: 0,
  failed: 0,
  results: [],
})

const portfolioData = ref<PortfolioItem[]>([])
const schedulerInfo = ref<{
  running: boolean
  last_run: string | null
  next_run: number | null
  total_collected: number
  total_failed: number
} | null>(null)
const collectInterval = ref(3)
const intervalSaving = ref(false)

const fileInputRef = ref<HTMLInputElement | null>(null)

let refreshPollTimer: ReturnType<typeof setInterval> | null = null
let pollTimer: ReturnType<typeof setInterval> | null = null

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

const portfolioMap = computed<Record<string, PortfolioItem>>(() => {
  return portfolioData.value.reduce<Record<string, PortfolioItem>>((map, item) => {
    map[item.code] = item
    return map
  }, {})
})

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

const analysisMap = computed(() => {
  const map: Record<string, BatchResultItem> = {}
  for (const r of batch.value.results) {
    map[r.code] = r
  }
  return map
})

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
    tooltip: { trigger: 'item' as const, formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'horizontal' as const, bottom: 0, textStyle: { color: '#666', fontSize: 12 } },
    series: [
      {
        type: 'pie',
        radius: ['45%', '65%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
        label: { show: true, color: '#333', formatter: '{b}\n{d}%', fontSize: 12 },
        data,
      },
    ],
  }
})

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
    tooltip: { trigger: 'axis' as const, axisPointer: { type: 'shadow' as const } },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '8%', containLabel: true },
    xAxis: { type: 'category' as const, data: ranges.map((r) => r.label), axisLabel: { color: '#666' }, axisLine: { lineStyle: { color: '#e5e5e5' } } },
    yAxis: { type: 'value' as const, minInterval: 1, axisLabel: { color: '#666' }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
    series: [
      {
        type: 'bar',
        data: counts,
        barWidth: '50%',
        itemStyle: { borderRadius: [4, 4, 0, 0], color: '#2563eb' },
      },
    ],
  }
})

async function handleAddToWatchlist() {
  const code = addCode.value.trim()
  if (!code) {
    message.warning('请输入股票代码')
    return
  }

  if (!/^[A-Za-z0-9.]+$/.test(code)) {
    message.warning('股票代码只能包含字母、数字和点')
    return
  }

  if (code.length > 20) {
    message.warning('股票代码长度不能超过20个字符')
    return
  }

  try {
    await watchlistStore.add(code, addName.value.trim(), addGroup.value ?? undefined)
    message.success(`已添加 ${code}`)
    addCode.value = ''
    addName.value = ''
    addGroup.value = null
  } catch (e: any) {
    const errorMessage = e.response?.data?.detail || '添加失败，请检查代码是否正确'
    message.error(errorMessage)
  }
}

async function handleRemove(code: string) {
  try {
    await Promise.all([watchlistStore.remove(code), deletePortfolioItem(code).catch(() => {})])
    message.success(`已移除 ${code}`)
    await fetchPortfolio()
  } catch {
    message.error('移除失败')
  }
}

function goToAnalysis(code: string) {
  const assetType = _guessAssetType(code)
  router.push(`/analysis/${code}?type=${assetType}`)
}

function _guessAssetType(code: string): string {
  if (/^(15|51|52|58|16|50)/.test(code)) return 'fund'
  if (/^(00|01|02|03)/.test(code)) return 'stock'
  return 'stock'
}

function handleGroupSelect(val: string) {
  watchlistStore.currentGroup = val === '__all__' ? null : val
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

function triggerImport() {
  fileInputRef.value?.click()
}

async function handleImportFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  exporting.value = true
  try {
    const buffer = await file.arrayBuffer()
    const blob1 = new Blob([buffer], { type: file.type })
    const blob2 = new Blob([buffer], { type: file.type })
    const file1 = new File([blob1], file.name, { type: file.type })
    const file2 = new File([blob2], file.name, { type: file.type })

    const group = watchlistStore.currentGroup || ''
    const [portfolioResult, watchlistResult] = await Promise.all([importPortfolio(file1), importWatchlist(file2, group)])
    message.success(`${portfolioResult.message}；${watchlistResult.message}`)
    await watchlistStore.fetch()
    await watchlistStore.fetchGroups()
    await fetchPortfolio()
  } catch (e: any) {
    const detail = e.response?.data?.detail || e.message || '导入失败'
    message.error(detail)
  } finally {
    exporting.value = false
    input.value = ''
  }
}

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
    }
  }, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

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
          await loadCachedResults()
        }
      } catch {
      }
    }, 3000)
  } catch (e: any) {
    refreshing.value = false
    message.error(e.response?.data?.detail || '触发刷新失败')
  }
}

async function loadCachedResults() {
  try {
    const resp = await submitBatch(watchlistStore.filteredItems.map((item) => item.code), 'auto', 'stock', 60, true)
    const taskId: string = resp.task_id ?? resp.id ?? resp
    startPolling(taskId)
  } catch {
  }
}

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
  if (score >= 75) return '#dc2626'
  if (score >= 60) return '#ea580c'
  if (score >= 40) return '#2563eb'
  if (score >= 25) return '#059669'
  return '#10b981'
}

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

async function fetchPortfolio() {
  try {
    portfolioData.value = await getPortfolio()
  } catch (e) {
    console.error('[Portfolio] 获取失败:', e)
  }
}

async function fetchSchedulerStatus() {
  try {
    schedulerInfo.value = await getSchedulerStatus()
  } catch {
  }
}

async function fetchInterval() {
  try {
    const res = await getInterval()
    collectInterval.value = res.interval_minutes
  } catch {
  }
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

onMounted(() => {
  watchlistStore.fetch()
  watchlistStore.fetchGroups()
  fetchSchedulerStatus()
  fetchPortfolio()
  fetchInterval()
})

onUnmounted(() => {
  stopPolling()
  if (refreshPollTimer) {
    clearInterval(refreshPollTimer)
    refreshPollTimer = null
  }
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
      const color = val >= 0 ? '#dc2626' : '#059669'
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
      const color = val >= 0 ? '#dc2626' : '#059669'
      const sign = val >= 0 ? '+' : ''
      const pctStr = row.hold_pnl_pct != null ? ` (${row.hold_pnl_pct! >= 0 ? '+' : ''}${row.hold_pnl_pct!.toFixed(2)}%)` : ''
      return h(NText, { style: { color } }, () => `${sign}${val.toFixed(2)}${pctStr}`)
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
        return row.error ? h(NText, { type: 'error', style: { fontSize: '12px' } }, () => '失败') : h(NText, { depth: 3, style: { fontSize: '12px' } }, () => '--')
      }
      const color =
        row.score >= 75 ? '#dc2626' : row.score >= 60 ? '#ea580c' : row.score >= 40 ? '#2563eb' : row.score >= 25 ? '#059669' : '#10b981'
      return h(NText, { style: { color, fontWeight: 600 } }, () => String(row.score))
    },
  },
  {
    title: '趋势',
    key: 'trend',
    width: 110,
    render(row: MergedRow) {
      if (!row.trend) return '--'
      const color = trendColorMap[row.trend] ?? '#666'
      return h(NTag, { size: 'small', round: true, bordered: false, style: { backgroundColor: color, color: '#fff' } }, () => row.trend)
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    render(row: MergedRow) {
      return h(NSpace, { size: 8 }, () => [
        h(NButton, { size: 'small', type: 'primary', secondary: true, onClick: () => goToAnalysis(row.code) }, () => '详情'),
        h(NButton, { size: 'small', type: 'error', secondary: true, onClick: () => handleRemove(row.code) }, () => '删除'),
      ])
    },
  },
]
</script>

<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h1 class="page-title">股票技术分析</h1>
      <p class="page-subtitle">自选股管理 · 批量分析 · 专业数据</p>
    </div>

    <div class="content-section">
      <div class="section-header">
        <h2 class="section-title">自选股管理</h2>
        <div class="section-actions">
          <NInputGroup class="input-group">
            <NInput v-model:value="addCode" placeholder="股票代码" clearable class="code-input" @keyup.enter="handleAddToWatchlist" />
            <NInput v-model:value="addName" placeholder="名称（可选）" clearable class="name-input" @keyup.enter="handleAddToWatchlist" />
            <NSelect v-model:value="addGroup" :options="addGroupOptions" placeholder="分组" clearable class="group-select" />
            <NButton type="primary" class="add-button" @click="handleAddToWatchlist">添加</NButton>
          </NInputGroup>
        </div>
      </div>

      <div class="filter-bar">
        <NSelect :value="watchlistStore.currentGroup ?? '__all__'" :options="groupSelectOptions" class="filter-select" size="small" @update:value="handleGroupSelect" />
        <NSpace :size="8">
          <NButton size="small" secondary @click="showGroupModal = true">新建分组</NButton>
          <NPopconfirm v-if="watchlistStore.currentGroup" @positive-click="handleDeleteGroup(watchlistStore.currentGroup!)">
            <template #trigger>
              <NButton size="small" type="error" secondary>删除分组</NButton>
            </template>
            <span>确定删除分组 "{{ watchlistStore.currentGroup }}"？</span>
          </NPopconfirm>
        </NSpace>
      </div>

      <div class="action-bar">
        <NSpace :size="12" align="center" class="action-buttons">
          <NButton :loading="exporting" secondary @click="triggerImport" class="import-btn">
            <span class="btn-icon">📥</span>
            导入持仓
          </NButton>
          <input ref="fileInputRef" type="file" accept=".xlsx,.xls,.csv" class="file-input" @change="handleImportFile" />
          <NButton type="warning" :disabled="watchlistStore.filteredItems.length === 0 || batch.running" :loading="batch.running" @click="handleBatchAnalyze" class="analyze-btn">
            <span class="btn-icon">📊</span>
            一键分析
          </NButton>
          <NButton :loading="refreshing" :disabled="refreshing" secondary type="info" @click="handleManualRefresh" class="refresh-btn">
            <span class="btn-icon">🔄</span>
            刷新数据
          </NButton>
        </NSpace>
        <div v-if="batch.running" class="progress-info">
          <span class="progress-text">正在分析... {{ batch.completed }} / {{ batch.total }}</span>
        </div>
      </div>

      <div v-if="schedulerInfo" class="scheduler-bar">
        <div class="scheduler-item">
          <span class="scheduler-label">定时采集</span>
          <span class="scheduler-value" :class="{ running: schedulerInfo.running }">{{ schedulerInfo.running ? '运行中' : '已停止' }}</span>
        </div>
        <div class="scheduler-item">
          <span class="scheduler-label">最后更新</span>
          <span class="scheduler-value">{{ formatLastRun(schedulerInfo.last_run) }}</span>
        </div>
        <div v-if="schedulerInfo.total_collected > 0" class="scheduler-item">
          <span class="scheduler-label">累计采集</span>
          <span class="scheduler-value">{{ schedulerInfo.total_collected }} 次</span>
        </div>
        <div class="scheduler-divider"></div>
        <div class="scheduler-item">
          <span class="scheduler-label">间隔</span>
          <NInputNumber :value="collectInterval" :min="1" :max="60" size="small" :disabled="intervalSaving" class="interval-input" @update:value="handleIntervalChange" />
          <span class="scheduler-unit">分钟</span>
        </div>
      </div>

      <NProgress v-if="batch.running" type="line" :percentage="Math.round(batch.progress)" :height="6" status="info" class="progress-bar" />

      <div class="table-container">
        <NSpin :show="watchlistStore.loading">
          <NDataTable
            v-if="mergedTableData.length > 0"
            :columns="mergedColumns"
            :data="mergedTableData"
            :bordered="false"
            :single-line="false"
            size="small"
            :row-key="(row: MergedRow) => row.code"
            :scroll-x="800"
            :max-height="520"
            :virtual-scroll="mergedTableData.length > 20"
            class="data-table"
          />
          <div v-else class="empty-state">
            <NEmpty description="暂无自选股，请添加股票代码" />
          </div>
        </NSpin>
      </div>
    </div>

    <template v-if="batchSummary">
      <div class="content-section">
        <div class="section-header">
          <h2 class="section-title">分析结果</h2>
          <NButton type="info" :loading="exporting" @click="handleExportAnalysis" class="export-btn">
            <span class="btn-icon">📤</span>
            导出结果
          </NButton>
        </div>

        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">总计</div>
            <div class="stat-value">{{ batchSummary.total }}</div>
          </div>
          <div class="stat-card success">
            <div class="stat-label">成功</div>
            <div class="stat-value">
              {{ batchSummary.valid }}
              <span class="stat-suffix"> / {{ batchSummary.total }}</span>
            </div>
          </div>
          <div class="stat-card" :class="{ error: batchSummary.failed > 0 }">
            <div class="stat-label">失败</div>
            <div class="stat-value">
              {{ batchSummary.failed }}
              <span v-if="batchSummary.failed > 0" class="stat-suffix"> / {{ batchSummary.total }}</span>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-label">平均评分</div>
            <div class="stat-value">{{ batchSummary.avgScore }}</div>
          </div>
        </div>

        <div class="charts-grid">
          <div class="chart-card">
            <h3 class="chart-title">趋势分布</h3>
            <VChart v-if="batch.results.length > 0" :option="trendPieOption" class="chart" autoresize />
            <NEmpty v-else description="暂无数据" />
          </div>
          <div class="chart-card">
            <h3 class="chart-title">评分分布</h3>
            <VChart v-if="batch.results.length > 0" :option="scoreBarOption" class="chart" autoresize />
            <NEmpty v-else description="暂无数据" />
          </div>
        </div>
      </div>
    </template>

    <div class="content-section">
      <div class="section-header">
        <h2 class="section-title">快速分析</h2>
      </div>

      <div class="quick-analyze-section">
        <div class="quick-input-row">
          <NInput v-model:value="quickCode" placeholder="输入股票代码" clearable class="quick-input" @keyup.enter="handleQuickAnalyze" />
          <NButton type="primary" :loading="quickLoading" @click="handleQuickAnalyze" class="quick-analyze-btn">分析</NButton>
        </div>

        <div v-if="quickResult" class="quick-result">
          <div class="quick-result-main">
            <div class="quick-info">
              <div class="quick-name-row">
                <span class="quick-name">{{ quickResult.stock_info.name }}</span>
                <NTag size="small" type="info" bordered class="quick-code-tag">{{ quickResult.stock_info.code }}</NTag>
              </div>
              <div class="quick-price" :style="{ color: getPctColor(quickResult.stock_info.change_pct) }">
                {{ formatPrice(quickResult.stock_info.current_price) }}
                <span class="quick-change" :style="{ color: getPctColor(quickResult.stock_info.change_pct) }">{{ formatPct(quickResult.stock_info.change_pct) }}</span>
              </div>
            </div>
            <div class="quick-score-section">
              <div class="quick-score-value" :style="{ color: getQuickScoreColor(quickResult.analysis.score) }">{{ quickResult.analysis.score }}</div>
              <div class="quick-score-label">评分</div>
            </div>
            <NTag size="medium" round bordered :style="{ backgroundColor: trendColorMap[quickResult.analysis.trend] ?? '#666', color: '#fff' }" class="quick-trend-tag">{{ quickResult.analysis.trend }}</NTag>
            <NButton size="small" type="primary" secondary @click="goToAnalysis(quickResult.stock_info.code)" class="view-detail-btn">查看详情</NButton>
          </div>
        </div>

        <NSpin v-if="quickLoading" size="small" class="quick-loading">
          <span>正在分析中...</span>
        </NSpin>
      </div>
    </div>

    <SystemLogs ref="systemLogsRef" />

    <NModal v-model:show="showGroupModal" preset="dialog" title="新建分组" class="group-modal">
      <NSpace vertical :size="16" style="margin-top: 8px">
        <NInput v-model:value="newGroupName" placeholder="输入分组名称" clearable class="group-name-input" @keyup.enter="handleCreateGroup" />
        <NSpace :size="12" justify="end">
          <NButton @click="showGroupModal = false">取消</NButton>
          <NButton type="primary" @click="handleCreateGroup">确定</NButton>
        </NSpace>
      </NSpace>
    </NModal>
  </div>
</template>

<style scoped>
.dashboard-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.page-header {
  text-align: center;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.page-title {
  font-size: 32px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 8px 0;
  letter-spacing: -0.02em;
}

.page-subtitle {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
  font-weight: 400;
}

.content-section {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #f3f4f6;
  padding: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.input-group {
  flex: 1;
  max-width: 600px;
}

.code-input {
  min-width: 140px;
}

.name-input {
  min-width: 140px;
}

.group-select {
  min-width: 120px;
}

.add-button {
  font-weight: 500;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #f9fafb;
  border-radius: 8px;
}

.filter-select {
  width: 160px;
}

.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #f3f4f6;
  border-radius: 8px;
}

.action-buttons {
  flex-wrap: wrap;
}

.import-btn,
.analyze-btn,
.refresh-btn,
.export-btn {
  font-weight: 500;
}

.btn-icon {
  margin-right: 6px;
  font-size: 14px;
}

.file-input {
  display: none;
}

.progress-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-text {
  font-size: 13px;
  color: #4b5563;
  font-weight: 500;
}

.scheduler-bar {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 12px 16px;
  background: #f9fafb;
  border-radius: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.scheduler-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.scheduler-label {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.scheduler-value {
  font-size: 13px;
  color: #111827;
  font-weight: 500;
}

.scheduler-value.running {
  color: #059669;
}

.scheduler-divider {
  width: 1px;
  height: 20px;
  background: #e5e7eb;
}

.interval-input {
  width: 80px;
}

.scheduler-unit {
  font-size: 13px;
  color: #6b7280;
}

.progress-bar {
  margin-bottom: 16px;
  max-width: 400px;
}

.table-container {
  border-radius: 8px;
  overflow: hidden;
}

.data-table {
  border-radius: 8px;
}

.empty-state {
  padding: 48px 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #f9fafb;
  border: 1px solid #f3f4f6;
  border-radius: 10px;
  padding: 20px;
  text-align: center;
  transition: all 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.stat-card.success {
  background: #ecfdf5;
  border-color: #d1fae5;
}

.stat-card.error {
  background: #fef2f2;
  border-color: #fee2e2;
}

.stat-label {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #111827;
  line-height: 1.2;
}

.stat-suffix {
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
  margin-left: 4px;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 20px;
}

.chart-card {
  background: #f9fafb;
  border: 1px solid #f3f4f6;
  border-radius: 10px;
  padding: 20px;
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  margin: 0 0 16px 0;
}

.chart {
  height: 280px;
}

.quick-analyze-section {
  padding: 0;
}

.quick-input-row {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 20px;
}

.quick-input {
  flex: 1;
  max-width: 300px;
}

.quick-analyze-btn {
  font-weight: 500;
}

.quick-result {
  background: linear-gradient(135deg, #f9fafb 0%, #ffffff 100%);
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 24px;
}

.quick-result-main {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}

.quick-info {
  flex: 1;
  min-width: 200px;
}

.quick-name-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.quick-name {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.quick-code-tag {
  font-size: 12px;
}

.quick-price {
  font-size: 32px;
  font-weight: 700;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}

.quick-change {
  font-size: 18px;
  font-weight: 600;
  margin-left: 12px;
}

.quick-score-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.quick-score-value {
  font-size: 36px;
  font-weight: 700;
  line-height: 1;
}

.quick-score-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.quick-trend-tag {
  font-weight: 600;
}

.view-detail-btn {
  font-weight: 500;
}

.quick-loading {
  padding: 32px 0;
  text-align: center;
}

.group-modal :deep(.n-modal-body) {
  padding: 24px;
}

.group-name-input {
  margin-bottom: 8px;
}

@media (max-width: 768px) {
  .dashboard-page {
    padding: 20px 16px;
    gap: 24px;
  }

  .page-title {
    font-size: 24px;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .input-group {
    max-width: 100%;
    flex-wrap: wrap;
  }

  .code-input,
  .name-input,
  .group-select {
    flex: 1;
    min-width: 120px;
  }

  .filter-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .filter-select {
    width: 100%;
  }

  .action-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .action-buttons {
    width: 100%;
  }

  .scheduler-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .scheduler-divider {
    display: none;
  }

  .charts-grid {
    grid-template-columns: 1fr;
  }

  .quick-result-main {
    flex-direction: column;
    align-items: flex-start;
  }

  .quick-price {
    font-size: 28px;
  }

  .quick-score-value {
    font-size: 32px;
  }
}
</style>
