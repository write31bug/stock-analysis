<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  NCard,
  NInputGroup,
  NInput,
  NButton,
  NSelect,
  NSpin,
  NAlert,
  NStatistic,
  NTag,
  NGrid,
  NGridItem,
  NSpace,
  NDescriptions,
  NDescriptionsItem,
  NEmpty,
  useMessage,
} from 'naive-ui'
import CandlestickChart from '../components/CandlestickChart.vue'
import IndicatorCharts from '../components/IndicatorCharts.vue'
import { useAnalysisStore } from '../stores/analysis'
import { saveHistory } from '../api'
import type { SeriesPoint } from '../types'

const route = useRoute()
const store = useAnalysisStore()
const message = useMessage()

const searchCode = ref('')
const market = ref('auto')
const assetType = ref('stock')
const days = ref(60)

const marketOptions = [
  { label: '自动识别', value: 'auto' },
  { label: 'A股', value: 'cn' },
  { label: '港股', value: 'hk' },
  { label: '美股', value: 'us' },
]

const assetTypeOptions = [
  { label: '股票', value: 'stock' },
  { label: 'ETF', value: 'etf' },
  { label: '基金', value: 'fund' },
]

const daysOptions = [
  { label: '30天', value: 30 },
  { label: '60天', value: 60 },
  { label: '90天', value: 90 },
  { label: '120天', value: 120 },
  { label: '250天', value: 250 },
]

function validateStockCode(code: string): string | null {
  const trimmedCode = code.trim()
  if (!trimmedCode) {
    return '请输入股票代码'
  }
  
  // 检查代码长度
  if (trimmedCode.length > 20) {
    return '股票代码长度不能超过20个字符'
  }
  
  // 检查代码格式
  const validPattern = /^[A-Za-z0-9.]+$/
  if (!validPattern.test(trimmedCode)) {
    return '股票代码只能包含字母、数字和点'
  }
  
  return null
}

async function handleAnalyze() {
  const code = searchCode.value
  const error = validateStockCode(code)
  if (error) {
    message.warning(error)
    return
  }
  await store.analyze(code.trim(), market.value, assetType.value, days.value)
}

onMounted(() => {
  const code = (route.params.code as string) || ''
  if (code) {
    searchCode.value = code
    const queryType = route.query.type as string
    if (queryType && ['stock', 'fund'].includes(queryType)) {
      assetType.value = queryType
    }
    handleAnalyze()
  }
})

watch(
  () => route.params.code,
  (newCode) => {
    const code = (newCode as string) || ''
    if (code && code !== searchCode.value) {
      searchCode.value = code
      handleAnalyze()
    }
  },
)

const result = computed(() => store.result)
const loading = computed(() => store.loading)
const error = computed(() => store.error)

const trendColorMap: Record<string, string> = {
  '强势上涨': '#dc2626',
  '上涨趋势': '#ea580c',
  '震荡整理': '#2563eb',
  '下跌趋势': '#059669',
  '强势下跌': '#10b981',
}

function getTrendColor(trend: string): string {
  return trendColorMap[trend] ?? '#6b7280'
}

function getScoreColor(score: number): string {
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

const maSeries = computed<Record<string, SeriesPoint[]>>(() => {
  if (!result.value?.indicator_series) return {}
  const series: Record<string, SeriesPoint[]> = {}
  for (const key of Object.keys(result.value.indicator_series)) {
    if (key.startsWith('MA')) {
      series[key] = result.value.indicator_series[key]
    }
  }
  return series
})

const indicators = computed(() => result.value?.technical_indicators ?? {})

const maSignal = computed(() => {
  const ti = indicators.value
  const ma5 = ti.ma?.MA5
  const ma20 = ti.ma?.MA20
  if (ma5 != null && ma20 != null) {
    return ma5 > ma20 ? '多头排列' : '空头排列'
  }
  return '--'
})

const macdSignal = computed(() => {
  const ti = indicators.value
  const dif = ti.macd?.DIF
  const dea = ti.macd?.DEA
  const sig = ti.macd?.signal
  if (sig && sig !== '中性') return sig
  if (dif != null && dea != null) {
    return dif > dea ? '多头' : '空头'
  }
  return '中性'
})

const rsiStatus = computed(() => {
  const ti = indicators.value
  const rsi6 = ti.rsi?.RSI6
  const rsi12 = ti.rsi?.RSI12
  if (rsi6 != null && rsi6 > 80) return '超买'
  if (rsi12 != null && rsi12 < 20) return '超卖'
  if (rsi6 != null && rsi6 > 70) return '偏超买'
  if (rsi12 != null && rsi12 < 30) return '偏超卖'
  return '中性'
})

const kdjSignal = computed(() => {
  const ti = indicators.value
  const k = ti.kdj?.K
  const d = ti.kdj?.D
  const j = ti.kdj?.J
  const sig = ti.kdj?.signal
  if (sig && sig !== '中性' && sig !== '数据不足') return sig
  if (k == null || d == null) return '--'
  if (j != null && j > 100) return '超买'
  if (j != null && j < 0) return '超卖'
  if (k > d) return '多头'
  return '空头'
})

const bollPosition = computed(() => {
  const ti = indicators.value
  return ti.bollinger?.position ?? '--'
})

const bollSqueeze = computed(() => {
  const ti = indicators.value
  return ti.bollinger?.squeeze ? '收窄' : '扩张'
})

const volumeSignal = computed(() => {
  const ti = indicators.value
  return ti.volume_analysis?.volume_signal ?? '--'
})

const obvTrend = computed(() => {
  const ti = indicators.value
  const obv = ti.obv?.OBV
  const obvPrev = ti.obv?.OBV_prev5
  if (obv == null || obvPrev == null) return '--'
  return obv > obvPrev ? '上升' : '下降'
})

const cciStatus = computed(() => {
  const ti = indicators.value
  const cci = ti.cci?.CCI
  if (cci == null) return '--'
  if (cci > 100) return '超买'
  if (cci < -100) return '超卖'
  return '中性'
})

const wrStatus = computed(() => {
  const ti = indicators.value
  const wr = ti.wr?.WR
  if (wr == null) return '--'
  if (wr > -20) return '超买'
  if (wr < -80) return '超卖'
  return '中性'
})

const keyLevels = computed(() => result.value?.key_levels ?? {})

function fmt(val: number | null | undefined, digits = 2): string {
  if (val == null) return '--'
  return Number(val).toFixed(digits)
}

const saving = ref(false)
async function onSave() {
  if (!result.value) return
  saving.value = true
  try {
    await saveHistory(result.value)
    message.success('保存成功')
  } catch {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="analysis-page">
    <div class="page-header">
      <h1 class="page-title">股票分析</h1>
      <p class="page-subtitle">技术指标 · K线图表 · 深度分析</p>
    </div>

    <div class="content-section">
      <div class="search-bar">
        <NInputGroup class="search-input-group">
          <NInput
            v-model:value="searchCode"
            placeholder="输入股票代码，如 600519 / 00700 / AAPL"
            clearable
            class="code-search-input"
            @keyup.enter="handleAnalyze"
          />
          <NButton type="primary" :loading="loading" @click="handleAnalyze" class="search-button">分析</NButton>
        </NInputGroup>
        <NSpace :size="12" :wrap="true" class="search-options">
          <NSelect v-model:value="market" :options="marketOptions" size="small" class="option-select" />
          <NSelect v-model:value="assetType" :options="assetTypeOptions" size="small" class="option-select" />
          <NSelect v-model:value="days" :options="daysOptions" size="small" class="option-select" />
        </NSpace>
      </div>
    </div>

    <div v-if="loading" class="loading-wrapper">
      <NSpin size="large" />
      <span class="loading-text">正在分析中...</span>
    </div>

    <NAlert v-if="error && !loading" type="error" :title="error" class="error-alert" />

    <template v-if="result && !loading">
      <div class="content-section">
        <div class="stock-header">
          <div class="stock-header-left">
            <div class="stock-name-row">
              <span class="stock-name">{{ result.stock_info.name }}</span>
              <NTag size="small" bordered type="info" class="code-tag">
                {{ result.stock_info.code }}
              </NTag>
            </div>
            <div class="price-row">
              <span class="current-price" :style="{ color: getPctColor(result.stock_info.change_pct) }">
                {{ formatPrice(result.stock_info.current_price) }}
              </span>
              <span class="change-pct" :style="{ color: getPctColor(result.stock_info.change_pct) }">
                {{ formatPct(result.stock_info.change_pct) }}
              </span>
            </div>
            <div v-if="result.stock_info?.update_time" class="update-time">
              更新时间：{{ result.stock_info.update_time }}
            </div>
          </div>

          <div class="stock-header-right">
            <div class="score-section">
              <div class="score-value" :style="{ color: getScoreColor(result.analysis.score) }">{{ result.analysis.score }}</div>
              <div class="score-label">评分</div>
              <NTag
                :style="{ backgroundColor: getTrendColor(result.analysis.trend), color: '#fff' }"
                size="medium"
                round
                bordered
                class="trend-tag"
              >
                {{ result.analysis.trend }}
              </NTag>
            </div>
            <div class="recommendation">{{ result.analysis.recommendation }}</div>
            <NButton size="small" :loading="saving" @click="onSave" class="save-button">保存记录</NButton>
          </div>
        </div>
      </div>

      <div v-if="result.analysis?.summary" class="content-section">
        <div class="section-header">
          <h2 class="section-title">分析摘要</h2>
        </div>
        <p class="summary-text">{{ result.analysis.summary }}</p>
      </div>

      <div class="content-section">
        <div class="section-header">
          <h2 class="section-title">K线图</h2>
        </div>
        <CandlestickChart :ohlcv="result.ohlcv" :ma-series="maSeries" :height="450" />
      </div>

      <div class="content-section">
        <div class="section-header">
          <h2 class="section-title">技术指标图</h2>
        </div>
        <IndicatorCharts :indicator-series="result.indicator_series" :height="380" />
      </div>

      <div class="content-section">
        <div class="section-header">
          <h2 class="section-title">技术指标详情</h2>
        </div>
        <NGrid :x-gap="16" :y-gap="16" responsive="screen" item-responsive :cols="{ s: 1, m: 2, l: 3 }">
          <NGridItem span="1 m:1 l:1">
            <div class="indicator-card">
              <div class="indicator-card-title">MA 均线</div>
              <NDescriptions :column="1" label-placement="left" size="small" bordered>
                <NDescriptionsItem label="MA5">{{ fmt(indicators.ma?.MA5) }}</NDescriptionsItem>
                <NDescriptionsItem label="MA10">{{ fmt(indicators.ma?.MA10) }}</NDescriptionsItem>
                <NDescriptionsItem label="MA20">{{ fmt(indicators.ma?.MA20) }}</NDescriptionsItem>
                <NDescriptionsItem label="MA60">{{ fmt(indicators.ma?.MA60) }}</NDescriptionsItem>
              </NDescriptions>
              <div class="indicator-signal-row">
                <span class="signal-label">信号:</span>
                <NTag :type="maSignal === '多头排列' ? 'error' : 'success'" size="small" round>
                  {{ maSignal }}
                </NTag>
              </div>
            </div>
          </NGridItem>

          <NGridItem span="1 m:1 l:1">
            <div class="indicator-card">
              <div class="indicator-card-title">MACD</div>
              <NDescriptions :column="1" label-placement="left" size="small" bordered>
                <NDescriptionsItem label="DIF">{{ fmt(indicators.macd?.DIF, 3) }}</NDescriptionsItem>
                <NDescriptionsItem label="DEA">{{ fmt(indicators.macd?.DEA, 3) }}</NDescriptionsItem>
                <NDescriptionsItem label="MACD">{{ fmt(indicators.macd?.MACD, 3) }}</NDescriptionsItem>
              </NDescriptions>
              <div class="indicator-signal-row">
                <span class="signal-label">信号:</span>
                <NTag
                  :type="macdSignal === '金叉' ? 'error' : macdSignal === '死叉' ? 'success' : 'info'"
                  size="small"
                  round
                >
                  {{ macdSignal }}
                </NTag>
                <span v-if="indicators.macd?.divergence" class="divergence-text">
                  {{ indicators.macd.divergence }}
                </span>
              </div>
            </div>
          </NGridItem>

          <NGridItem span="1 m:1 l:1">
            <div class="indicator-card">
              <div class="indicator-card-title">RSI</div>
              <NDescriptions :column="1" label-placement="left" size="small" bordered>
                <NDescriptionsItem label="RSI6">{{ fmt(indicators.rsi?.RSI6, 2) }}</NDescriptionsItem>
                <NDescriptionsItem label="RSI12">{{ fmt(indicators.rsi?.RSI12, 2) }}</NDescriptionsItem>
                <NDescriptionsItem label="RSI24">{{ fmt(indicators.rsi?.RSI24, 2) }}</NDescriptionsItem>
              </NDescriptions>
              <div class="indicator-signal-row">
                <span class="signal-label">状态:</span>
                <NTag
                  :type="
                    rsiStatus === '超买'
                      ? 'error'
                      : rsiStatus === '超卖'
                        ? 'success'
                        : rsiStatus === '偏超买'
                          ? 'warning'
                          : rsiStatus === '偏超卖'
                            ? 'info'
                            : 'default'
                  "
                  size="small"
                  round
                >
                  {{ rsiStatus }}
                </NTag>
              </div>
            </div>
          </NGridItem>

          <NGridItem span="1 m:1 l:1">
            <div class="indicator-card">
              <div class="indicator-card-title">KDJ</div>
              <NDescriptions :column="1" label-placement="left" size="small" bordered>
                <NDescriptionsItem label="K">{{ fmt(indicators.kdj?.K, 2) }}</NDescriptionsItem>
                <NDescriptionsItem label="D">{{ fmt(indicators.kdj?.D, 2) }}</NDescriptionsItem>
                <NDescriptionsItem label="J">{{ fmt(indicators.kdj?.J, 2) }}</NDescriptionsItem>
              </NDescriptions>
              <div class="indicator-signal-row">
                <span class="signal-label">信号:</span>
                <NTag
                  :type="
                    kdjSignal === '多头'
                      ? 'error'
                      : kdjSignal === '空头'
                        ? 'success'
                        : kdjSignal === '超买'
                          ? 'warning'
                          : kdjSignal === '超卖'
                            ? 'info'
                            : 'default'
                  "
                  size="small"
                  round
                >
                  {{ kdjSignal }}
                </NTag>
              </div>
            </div>
          </NGridItem>

          <NGridItem span="1 m:1 l:1">
            <div class="indicator-card">
              <div class="indicator-card-title">BOLL 布林带</div>
              <NDescriptions :column="1" label-placement="left" size="small" bordered>
                <NDescriptionsItem label="上轨">{{ fmt(indicators.bollinger?.upper) }}</NDescriptionsItem>
                <NDescriptionsItem label="中轨">{{ fmt(indicators.bollinger?.middle) }}</NDescriptionsItem>
                <NDescriptionsItem label="下轨">{{ fmt(indicators.bollinger?.lower) }}</NDescriptionsItem>
              </NDescriptions>
              <div class="indicator-signal-row">
                <span class="signal-label">位置:</span>
                <NTag size="small" round type="default">{{ bollPosition }}</NTag>
                <NTag :type="bollSqueeze === '收窄' ? 'warning' : 'default'" size="small" round>
                  {{ bollSqueeze }}
                </NTag>
              </div>
            </div>
          </NGridItem>

          <NGridItem span="1 m:1 l:1">
            <div class="indicator-card">
              <div class="indicator-card-title">成交量</div>
              <NDescriptions :column="1" label-placement="left" size="small" bordered>
                <NDescriptionsItem label="VMA5">
                  {{
                    indicators.volume_analysis?.VMA5 != null
                      ? Number(indicators.volume_analysis.VMA5).toLocaleString()
                      : '--'
                  }}
                </NDescriptionsItem>
                <NDescriptionsItem label="VMA10">
                  {{
                    indicators.volume_analysis?.VMA10 != null
                      ? Number(indicators.volume_analysis.VMA10).toLocaleString()
                      : '--'
                  }}
                </NDescriptionsItem>
                <NDescriptionsItem label="量比">{{ fmt(indicators.volume_analysis?.volume_ratio, 2) }}</NDescriptionsItem>
              </NDescriptions>
              <div class="indicator-signal-row">
                <span class="signal-label">信号:</span>
                <NTag
                  :type="
                    volumeSignal === '放量' || volumeSignal === '温和放量'
                      ? 'error'
                      : volumeSignal === '缩量'
                        ? 'success'
                        : 'default'
                  "
                  size="small"
                  round
                >
                  {{ volumeSignal }}
                </NTag>
              </div>
            </div>
          </NGridItem>

          <NGridItem span="1 m:1 l:1">
            <div class="indicator-card">
              <div class="indicator-card-title">ATR 波动率</div>
              <NDescriptions :column="1" label-placement="left" size="small" bordered>
                <NDescriptionsItem label="ATR">{{ fmt(indicators.atr?.ATR) }}</NDescriptionsItem>
                <NDescriptionsItem label="ATR%"> {{ fmt(indicators.atr?.ATR_percent, 2) }}% </NDescriptionsItem>
              </NDescriptions>
            </div>
          </NGridItem>

          <NGridItem span="1 m:1 l:1">
            <div class="indicator-card">
              <div class="indicator-card-title">OBV 能量潮</div>
              <NDescriptions :column="1" label-placement="left" size="small" bordered>
                <NDescriptionsItem label="OBV">
                  {{ indicators.obv?.OBV != null ? Number(indicators.obv.OBV).toLocaleString() : '--' }}
                </NDescriptionsItem>
              </NDescriptions>
              <div class="indicator-signal-row">
                <span class="signal-label">趋势:</span>
                <NTag
                  :type="obvTrend === '上升' ? 'error' : obvTrend === '下降' ? 'success' : 'default'"
                  size="small"
                  round
                >
                  {{ obvTrend }}
                </NTag>
              </div>
            </div>
          </NGridItem>

          <NGridItem span="1 m:1 l:1">
            <div class="indicator-card">
              <div class="indicator-card-title">CCI 顺势指标</div>
              <NDescriptions :column="1" label-placement="left" size="small" bordered>
                <NDescriptionsItem label="CCI">{{ fmt(indicators.cci?.CCI, 2) }}</NDescriptionsItem>
              </NDescriptions>
              <div class="indicator-signal-row">
                <span class="signal-label">状态:</span>
                <NTag
                  :type="
                    cciStatus === '超买'
                      ? 'error'
                      : cciStatus === '超卖'
                        ? 'success'
                        : 'default'
                  "
                  size="small"
                  round
                >
                  {{ cciStatus }}
                </NTag>
              </div>
            </div>
          </NGridItem>

          <NGridItem span="1 m:1 l:1">
            <div class="indicator-card">
              <div class="indicator-card-title">WR 威廉指标</div>
              <NDescriptions :column="1" label-placement="left" size="small" bordered>
                <NDescriptionsItem label="WR">{{ fmt(indicators.wr?.WR, 2) }}</NDescriptionsItem>
              </NDescriptions>
              <div class="indicator-signal-row">
                <span class="signal-label">状态:</span>
                <NTag
                  :type="
                    wrStatus === '超买'
                      ? 'error'
                      : wrStatus === '超卖'
                        ? 'success'
                        : 'default'
                  "
                  size="small"
                  round
                >
                  {{ wrStatus }}
                </NTag>
              </div>
            </div>
          </NGridItem>
        </NGrid>
      </div>

      <div class="content-section">
        <div class="section-header">
          <h2 class="section-title">关键价位</h2>
        </div>
        <NGrid :x-gap="24" :y-gap="16" responsive="screen" item-responsive>
          <NGridItem span="1 m:1 l:1">
            <div class="levels-section">
              <div class="levels-title support-title">支撑位</div>
              <NSpace vertical :size="6">
                <div v-for="(level, idx) in keyLevels.support_levels" :key="'support-' + idx" class="level-item">
                  <span class="level-index">S{{ idx + 1 }}</span>
                  <span class="level-value">{{ fmt(level) }}</span>
                </div>
                <div v-if="!keyLevels.support_levels?.length" class="level-empty">暂无数据</div>
              </NSpace>
            </div>
          </NGridItem>
          <NGridItem span="1 m:1 l:1">
            <div class="levels-section">
              <div class="levels-title resistance-title">压力位</div>
              <NSpace vertical :size="6">
                <div v-for="(level, idx) in keyLevels.resistance_levels" :key="'resistance-' + idx" class="level-item">
                  <span class="level-index">R{{ idx + 1 }}</span>
                  <span class="level-value">{{ fmt(level) }}</span>
                </div>
                <div v-if="!keyLevels.resistance_levels?.length" class="level-empty">暂无数据</div>
              </NSpace>
            </div>
          </NGridItem>
        </NGrid>
      </div>
    </template>

    <div v-if="!result && !loading && !error" class="content-section">
      <div class="empty-state">
        <NEmpty description="请输入股票代码开始分析" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.analysis-page {
  max-width: 1300px;
  margin: 0 auto;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
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

.search-bar {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.search-input-group {
  max-width: 600px;
  margin: 0 auto;
}

.code-search-input {
  min-width: 200px;
}

.search-button {
  font-weight: 500;
}

.search-options {
  justify-content: center;
}

.option-select {
  width: 120px;
}

.loading-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  gap: 16px;
}

.loading-text {
  color: #6b7280;
  font-size: 14px;
}

.error-alert {
  margin-top: 8px;
}

.section-header {
  margin-bottom: 20px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.stock-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  flex-wrap: wrap;
}

.stock-header-left {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stock-name-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stock-name {
  font-size: 22px;
  font-weight: 700;
  color: #111827;
}

.code-tag {
  font-size: 12px;
}

.price-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.current-price {
  font-size: 36px;
  font-weight: 700;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.change-pct {
  font-size: 18px;
  font-weight: 600;
}

.update-time {
  font-size: 13px;
  color: #6b7280;
}

.stock-header-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}

.score-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.score-value {
  font-size: 36px;
  font-weight: 700;
  line-height: 1;
}

.score-label {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.trend-tag {
  font-weight: 600;
}

.recommendation {
  font-size: 14px;
  color: #4b5563;
  max-width: 280px;
  text-align: right;
  line-height: 1.6;
}

.save-button {
  font-weight: 500;
}

.summary-text {
  font-size: 14px;
  line-height: 1.8;
  color: #4b5563;
  margin: 0;
  white-space: pre-wrap;
}

.indicator-card {
  background: #f9fafb;
  border: 1px solid #f3f4f6;
  border-radius: 10px;
  padding: 16px;
  height: 100%;
}

.indicator-card-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e5e7eb;
}

.indicator-signal-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #e5e7eb;
}

.signal-label {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.divergence-text {
  font-size: 13px;
  color: #ea580c;
  font-weight: 500;
}

.levels-section {
  padding: 8px 0;
}

.levels-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid;
}

.support-title {
  color: #059669;
  border-color: #059669;
}

.resistance-title {
  color: #dc2626;
  border-color: #dc2626;
}

.level-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.level-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 24px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  background: #2563eb;
}

.level-value {
  font-size: 15px;
  font-weight: 500;
  color: #111827;
  font-variant-numeric: tabular-nums;
}

.level-empty {
  font-size: 13px;
  color: #6b7280;
}

.empty-state {
  padding: 60px 0;
}

@media (max-width: 768px) {
  .analysis-page {
    padding: 20px 16px;
    gap: 20px;
  }

  .page-title {
    font-size: 24px;
  }

  .stock-header {
    flex-direction: column;
    gap: 20px;
  }

  .stock-header-right {
    align-items: flex-start;
  }

  .recommendation {
    text-align: left;
  }

  .current-price {
    font-size: 28px;
  }

  .score-value {
    font-size: 28px;
  }
}
</style>
