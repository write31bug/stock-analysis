<script setup lang="ts">
import { ref, h, onMounted, computed } from 'vue'
import { NButton, NTag, NPopconfirm, NSpace, NDatePicker, NDrawer, NDrawerContent, NDataTable, NCard, NEmpty, NSpin, NInput, NSelect, useMessage } from 'naive-ui'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, MarkLineComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { getHistory, getScoreTrend, deleteHistory, clearHistory, exportHistoryCSV } from '../api'
import type { HistoryRecord } from '../types'

use([LineChart, GridComponent, TooltipComponent, MarkLineComponent, CanvasRenderer])

const message = useMessage()

const trendColorMap: Record<string, string> = {
  '强势上涨': '#dc2626',
  '上涨趋势': '#ea580c',
  '震荡整理': '#2563eb',
  '下跌趋势': '#059669',
  '强势下跌': '#10b981',
}

function getTrendColor(trend: string | null): string {
  if (!trend) return '#6b7280'
  return trendColorMap[trend] ?? '#6b7280'
}

function getScoreColor(score: number | null): string {
  if (score == null) return '#6b7280'
  if (score >= 75) return '#dc2626'
  if (score >= 60) return '#ea580c'
  if (score >= 40) return '#2563eb'
  if (score >= 25) return '#059669'
  return '#10b981'
}

function formatPrice(price: number | null): string {
  if (price == null) return '--'
  return price.toFixed(2)
}

function formatPct(pct: number | null): string {
  if (pct == null) return '--'
  const sign = pct >= 0 ? '+' : ''
  return `${sign}${pct.toFixed(2)}%`
}

function getPctColor(pct: number | null): string {
  if (pct == null) return '#6b7280'
  return pct >= 0 ? '#dc2626' : '#059669'
}

function formatTime(time: string): string {
  if (!time) return '--'
  return time.replace('T', ' ').slice(0, 19)
}

const trendOptions = [
  { label: '全部', value: '' },
  { label: '强势上涨', value: '强势上涨' },
  { label: '上涨趋势', value: '上涨趋势' },
  { label: '震荡整理', value: '震荡整理' },
  { label: '下跌趋势', value: '下跌趋势' },
  { label: '强势下跌', value: '强势下跌' },
]

const filterCode = ref('')
const filterTrend = ref('')
const dateRange = ref<[number, number] | null>(null)

const loading = ref(false)
const records = ref<HistoryRecord[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)

const drawerVisible = ref(false)
const trendLoading = ref(false)
const trendCode = ref('')
const trendName = ref('')
const trendData = ref<{ date: string; score: number }[]>([])

async function fetchHistory() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: page.value,
      size: size.value,
    }
    if (filterCode.value.trim()) {
      params.code = filterCode.value.trim()
    }
    if (filterTrend.value) {
      params.trend = filterTrend.value
    }
    if (dateRange.value) {
      params.start = new Date(dateRange.value[0]).toISOString().slice(0, 10)
      params.end = new Date(dateRange.value[1]).toISOString().slice(0, 10)
    }
    const res = await getHistory(params)
    records.value = res.records ?? []
    total.value = res.total ?? 0
  } catch {
    message.error('获取历史记录失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  fetchHistory()
}

function handleReset() {
  filterCode.value = ''
  filterTrend.value = ''
  dateRange.value = null
  page.value = 1
  fetchHistory()
}

function handlePageChange(p: number) {
  page.value = p
  fetchHistory()
}

function handlePageSizeChange(s: number) {
  size.value = s
  page.value = 1
  fetchHistory()
}

async function handleDelete(id: number) {
  try {
    await deleteHistory(id)
    message.success('删除成功')
    fetchHistory()
  } catch {
    message.error('删除失败')
  }
}

async function handleClearAll() {
  try {
    await clearHistory()
    message.success('已清空全部记录')
    page.value = 1
    fetchHistory()
  } catch {
    message.error('清空失败')
  }
}

async function handleViewTrend(record: HistoryRecord) {
  trendCode.value = record.code
  trendName.value = record.name ?? record.code
  trendData.value = []
  drawerVisible.value = true
  trendLoading.value = true
  try {
    const data = await getScoreTrend(record.code, 30)
    trendData.value = data ?? []
  } catch {
    message.error('获取趋势数据失败')
  } finally {
    trendLoading.value = false
  }
}

const chartOption = computed(() => {
  if (!trendData.value.length) return null

  const dates = trendData.value.map((d) => d.date)
  const scores = trendData.value.map((d) => d.score)

  return {
    tooltip: {
      trigger: 'axis' as const,
      formatter(params: any) {
        if (!Array.isArray(params) || !params.length) return ''
        const p = params[0]
        return `${p.axisValue}<br/>评分: <b>${p.value}</b>`
      },
    },
    grid: {
      left: 50,
      right: 30,
      top: 40,
      bottom: 30,
    },
    xAxis: {
      type: 'category' as const,
      data: dates,
      axisLabel: {
        fontSize: 11,
        color: '#6b7280',
        rotate: dates.length > 15 ? 45 : 0,
      },
      axisLine: { lineStyle: { color: '#e5e7eb' } },
    },
    yAxis: {
      type: 'value' as const,
      min: 0,
      max: 100,
      splitLine: { lineStyle: { color: '#f3f4f6', type: 'dashed' as const } },
      axisLabel: { fontSize: 11, color: '#6b7280' },
    },
    series: [
      {
        type: 'line' as const,
        data: scores,
        smooth: true,
        symbol: 'circle' as const,
        symbolSize: 6,
        lineStyle: { color: '#2563eb', width: 2 },
        itemStyle: { color: '#2563eb' },
        areaStyle: {
          color: {
            type: 'linear' as const,
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(37, 99, 235, 0.25)' },
              { offset: 1, color: 'rgba(37, 99, 235, 0.02)' },
            ],
          },
        },
        markLine: {
          silent: true,
          symbol: 'none' as const,
          lineStyle: { type: 'dashed' as const, width: 1 },
          label: {
            position: 'insideEndTop' as const,
            fontSize: 11,
            color: '#6b7280',
          },
          data: [
            {
              yAxis: 75,
              lineStyle: { color: '#dc2626' },
              label: { formatter: '强势上涨 75' },
            },
            {
              yAxis: 60,
              lineStyle: { color: '#ea580c' },
              label: { formatter: '上涨趋势 60' },
            },
            {
              yAxis: 40,
              lineStyle: { color: '#2563eb' },
              label: { formatter: '下跌趋势 40' },
            },
            {
              yAxis: 25,
              lineStyle: { color: '#059669' },
              label: { formatter: '强势下跌 25' },
            },
          ],
        },
      },
    ],
  }
})

const columns = [
  {
    title: '代码',
    key: 'code',
    width: 100,
    ellipsis: { tooltip: true },
  },
  {
    title: '名称',
    key: 'name',
    width: 100,
    ellipsis: { tooltip: true },
    render(row: HistoryRecord) {
      return row.name ?? '--'
    },
  },
  {
    title: '评分',
    key: 'score',
    width: 80,
    align: 'center' as const,
    render(row: HistoryRecord) {
      if (row.score == null) return '--'
      return h(
        'span',
        {
          style: {
            color: getScoreColor(row.score),
            fontWeight: 700,
            fontSize: '15px',
          },
        },
        String(row.score),
      )
    },
  },
  {
    title: '趋势',
    key: 'trend',
    width: 110,
    align: 'center' as const,
    render(row: HistoryRecord) {
      if (!row.trend) return '--'
      return h(
        NTag,
        {
          size: 'small',
          round: true,
          bordered: false,
          color: { color: getTrendColor(row.trend), textColor: '#fff' },
        },
        { default: () => row.trend },
      )
    },
  },
  {
    title: '现价',
    key: 'current_price',
    width: 100,
    align: 'right' as const,
    render(row: HistoryRecord) {
      return h('span', {}, formatPrice(row.current_price))
    },
  },
  {
    title: '涨跌幅',
    key: 'change_pct',
    width: 100,
    align: 'right' as const,
    render(row: HistoryRecord) {
      return h('span', { style: { color: getPctColor(row.change_pct), fontWeight: 500 } }, formatPct(row.change_pct))
    },
  },
  {
    title: '分析时间',
    key: 'analysis_time',
    width: 170,
    render(row: HistoryRecord) {
      return h('span', { style: { fontSize: '13px', color: '#6b7280' } }, formatTime(row.analysis_time))
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 170,
    fixed: 'right' as const,
    render(row: HistoryRecord) {
      return h('div', { style: { display: 'flex', gap: '8px', alignItems: 'center' } }, [
        h(
          NButton,
          {
            size: 'small',
            type: 'primary',
            secondary: true,
            onClick: () => handleViewTrend(row),
          },
          { default: () => '趋势' },
        ),
        h(
          NPopconfirm,
          { onPositiveClick: () => handleDelete(row.id) },
          {
            trigger: () => h(NButton, { size: 'small', type: 'error', secondary: true }, { default: () => '删除' }),
            default: () => '确定删除该记录？',
          },
        ),
      ])
    },
  },
]

const exporting = ref(false)

function downloadCSV(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

async function handleExportHistory() {
  exporting.value = true
  try {
    const params: Record<string, any> = {}
    if (filterCode.value.trim()) {
      params.code = filterCode.value.trim()
    }
    if (filterTrend.value) {
      params.trend = filterTrend.value
    }
    if (dateRange.value) {
      params.start = new Date(dateRange.value[0]).toISOString().slice(0, 10)
      params.end = new Date(dateRange.value[1]).toISOString().slice(0, 10)
    }
    const blob = await exportHistoryCSV(params)
    const now = new Date()
    const dateStr = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`
    downloadCSV(blob, `历史记录_${dateStr}.csv`)
    message.success('导出成功')
  } catch {
    message.error('导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  fetchHistory()
})
</script>

<template>
  <div class="history-page">
    <div class="page-header">
      <h1 class="page-title">历史记录</h1>
      <NSpace :size="8">
        <NButton type="info" size="small" secondary :loading="exporting" @click="handleExportHistory">
          导出历史
        </NButton>
        <NPopconfirm @positive-click="handleClearAll">
          <template #trigger>
            <NButton type="error" size="small" secondary>清空全部</NButton>
          </template>
          <span>确定清空全部历史记录？此操作不可恢复。</span>
        </NPopconfirm>
      </NSpace>
    </div>

    <div class="content-section">
      <div class="filter-row">
        <NInput
          v-model:value="filterCode"
          placeholder="股票代码"
          clearable
          class="filter-input"
          @keyup.enter="handleSearch"
        />
        <NSelect
          v-model:value="filterTrend"
          :options="trendOptions"
          placeholder="趋势筛选"
          clearable
          class="filter-select"
        />
        <NDatePicker
          v-model:value="dateRange"
          type="daterange"
          clearable
          :default-time="['00:00:00', '23:59:59']"
          class="filter-date"
        />
        <NButton type="primary" @click="handleSearch" class="search-button">搜索</NButton>
        <NButton @click="handleReset" class="reset-button">重置</NButton>
      </div>
    </div>

    <div class="content-section">
      <NDataTable
        :columns="columns"
        :data="records"
        :loading="loading"
        :row-key="(row: HistoryRecord) => row.id"
        :scroll-x="920"
        :pagination="{
          page: page,
          pageSize: size,
          itemCount: total,
          pageSizes: [10, 20, 50],
          showSizePicker: true,
          showQuickJumper: true,
          prefix: ({ itemCount }: { itemCount: number }) => `共 ${itemCount} 条`,
          onChange: (p: number) => handlePageChange(p),
          onUpdatePageSize: (s: number) => handlePageSizeChange(s),
        }"
        size="small"
        class="history-table"
      />
    </div>

    <NDrawer v-model:show="drawerVisible" :width="680" placement="right">
      <NDrawerContent :title="`${trendName} - 评分趋势`" closable>
        <div v-if="trendLoading" class="trend-loading">
          <NSpin />
          <span>加载中...</span>
        </div>
        <div v-else-if="!trendData.length" class="trend-empty">暂无趋势数据</div>
        <VChart v-else :option="chartOption" autoresize style="width: 100%; height: 400px" />
      </NDrawerContent>
    </NDrawer>
  </div>
</template>

<style scoped>
.history-page {
  max-width: 1300px;
  margin: 0 auto;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.page-title {
  font-size: 32px;
  font-weight: 700;
  color: #111827;
  margin: 0;
  letter-spacing: -0.02em;
}

.content-section {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #f3f4f6;
  padding: 24px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-input {
  width: 160px;
}

.filter-select {
  width: 140px;
}

.filter-date {
  width: 280px;
}

.search-button {
  font-weight: 500;
}

.reset-button {
  font-weight: 500;
}

.history-table {
  border-radius: 8px;
}

.trend-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  gap: 16px;
  color: #6b7280;
  font-size: 14px;
}

.trend-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: #6b7280;
  font-size: 14px;
}

@media (max-width: 768px) {
  .history-page {
    padding: 20px 16px;
    gap: 20px;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .page-title {
    font-size: 24px;
  }

  .filter-row {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-input,
  .filter-select,
  .filter-date {
    width: 100% !important;
  }
}
</style>
