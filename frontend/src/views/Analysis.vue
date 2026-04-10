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

// ---------- Route & Store ----------

const route = useRoute()
const store = useAnalysisStore()
const message = useMessage()

// ---------- Search Form State ----------

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

// ---------- Actions ----------

async function handleAnalyze() {
  const code = searchCode.value.trim()
  if (!code) {
    message.warning('请输入股票代码')
    return
  }
  await store.analyze(code, market.value, assetType.value, days.value)
}

// ---------- Auto-trigger from route ----------

onMounted(() => {
  const code = (route.params.code as string) || ''
  if (code) {
    searchCode.value = code
    // 从 query 参数读取资产类型
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

// ---------- Computed: Analysis Result ----------

const result = computed(() => store.result)
const loading = computed(() => store.loading)
const error = computed(() => store.error)

// ---------- Trend Color Mapping ----------

const trendColorMap: Record<string, string> = {
  强势上涨: '#ef5350',
  上涨趋势: '#FF9500',
  震荡整理: '#5B8FF9',
  下跌趋势: '#26a69a',
  强势下跌: '#61DDAA',
}

function getTrendColor(trend: string): string {
  return trendColorMap[trend] ?? '#999'
}

function getScoreColor(score: number): string {
  if (score >= 75) return '#ef5350'
  if (score >= 60) return '#FF9500'
  if (score >= 40) return '#5B8FF9'
  if (score >= 25) return '#26a69a'
  return '#61DDAA'
}

// ---------- Price Display ----------

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
  if (pct == null) return '#999'
  return pct >= 0 ? '#ef5350' : '#26a69a'
}

// ---------- MA Series Extraction ----------

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

// ---------- Technical Indicators ----------

const indicators = computed(() => result.value?.technical_indicators ?? {})

// MA signal
const maSignal = computed(() => {
  const ti = indicators.value
  const ma5 = ti.ma?.MA5
  const ma20 = ti.ma?.MA20
  if (ma5 != null && ma20 != null) {
    return ma5 > ma20 ? '多头排列' : '空头排列'
  }
  return '--'
})

// MACD signal
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

// RSI status
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

// KDJ signal
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

// BOLL position
const bollPosition = computed(() => {
  const ti = indicators.value
  return ti.bollinger?.position ?? '--'
})

const bollSqueeze = computed(() => {
  const ti = indicators.value
  return ti.bollinger?.squeeze ? '收窄' : '扩张'
})

// Volume signal
const volumeSignal = computed(() => {
  const ti = indicators.value
  return ti.volume_analysis?.volume_signal ?? '--'
})

// OBV trend
const obvTrend = computed(() => {
  const ti = indicators.value
  const obv = ti.obv?.OBV
  const obvPrev = ti.obv?.OBV_prev5
  if (obv == null || obvPrev == null) return '--'
  return obv > obvPrev ? '上升' : '下降'
})

// CCI status
const cciStatus = computed(() => {
  const ti = indicators.value
  const cci = ti.cci?.CCI
  if (cci == null) return '--'
  if (cci > 100) return '超买'
  if (cci < -100) return '超卖'
  return '中性'
})

// WR status
const wrStatus = computed(() => {
  const ti = indicators.value
  const wr = ti.wr?.WR
  if (wr == null) return '--'
  if (wr > -20) return '超买'
  if (wr < -80) return '超卖'
  return '中性'
})

// ---------- Key Levels ----------

const keyLevels = computed(() => result.value?.key_levels ?? {})

// ---------- Helper: safe number display ----------

function fmt(val: number | null | undefined, digits = 2): string {
  if (val == null) return '--'
  return Number(val).toFixed(digits)
}

// ---------- Saving state ----------

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
    <!-- ==================== Search Bar ==================== -->
    <NCard class="search-card" :bordered="false">
      <NSpace vertical :size="12">
        <NInputGroup>
          <NInput
            v-model:value="searchCode"
            placeholder="输入股票代码，如 600519 / 00700 / AAPL"
            clearable
            style="flex: 1; min-width: 200px"
            @keyup.enter="handleAnalyze"
          />
          <NButton type="primary" :loading="loading" @click="handleAnalyze"> 分析 </NButton>
        </NInputGroup>
        <NSpace :size="12" :wrap="true">
          <NSelect v-model:value="market" :options="marketOptions" style="width: 130px" size="small" />
          <NSelect v-model:value="assetType" :options="assetTypeOptions" style="width: 110px" size="small" />
          <NSelect v-model:value="days" :options="daysOptions" style="width: 100px" size="small" />
        </NSpace>
      </NSpace>
    </NCard>

    <!-- ==================== Loading ==================== -->
    <div v-if="loading" class="loading-wrapper">
      <NSpin size="large" />
      <span class="loading-text">正在分析中...</span>
    </div>

    <!-- ==================== Error ==================== -->
    <NAlert v-if="error && !loading" type="error" :title="error" class="error-alert" />

    <!-- ==================== Result Sections ==================== -->
    <template v-if="result && !loading">
      <!-- Stock Info Header -->
      <NCard class="stock-header-card" :bordered="false">
        <div class="stock-header">
          <div class="stock-header-left">
            <div class="stock-name-row">
              <span class="stock-name">{{ result.stock_info.name }}</span>
              <NTag size="small" :bordered="false" type="info">
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
              <NStatistic
                :value="result.analysis.score"
                class="score-statistic"
                :style="{
                  '--score-color': getScoreColor(result.analysis.score),
                }"
              >
                <template #prefix>
                  <span class="score-label">评分</span>
                </template>
              </NStatistic>
              <NTag
                :color="{
                  color: getTrendColor(result.analysis.trend),
                  textColor: '#fff',
                }"
                size="medium"
                round
                class="trend-tag"
              >
                {{ result.analysis.trend }}
              </NTag>
            </div>
            <div class="recommendation">
              {{ result.analysis.recommendation }}
            </div>
            <NButton size="small" :loading="saving" @click="onSave"> 保存记录 </NButton>
          </div>
        </div>
      </NCard>

      <!-- Summary -->
      <NCard v-if="result.analysis?.summary" title="分析摘要" :bordered="false" class="section-card">
        <p class="summary-text">{{ result.analysis.summary }}</p>
      </NCard>

      <!-- Charts -->
      <NCard title="K线图" :bordered="false" class="section-card">
        <CandlestickChart :ohlcv="result.ohlcv" :ma-series="maSeries" :height="500" />
      </NCard>

      <NCard title="技术指标图" :bordered="false" class="section-card">
        <IndicatorCharts :indicator-series="result.indicator_series" :height="400" />
      </NCard>

      <!-- Technical Indicators Detail Grid -->
      <NCard title="技术指标详情" :bordered="false" class="section-card">
        <NGrid :x-gap="16" :y-gap="16" responsive="screen" item-responsive :cols="{ s: 1, m: 2, l: 3 }">
          <!-- MA -->
          <NGridItem span="1 m:1 l:1">
            <div class="indicator-card">
              <div class="indicator-card-title">MA 均线</div>
              <NDescriptions :column="1" label-placement="left" size="small" bordered>
                <NDescriptionsItem label="MA5">
                  {{ fmt(indicators.ma?.MA5) }}
                </NDescriptionsItem>
                <NDescriptionsItem label="MA10">
                  {{ fmt(indicators.ma?.MA10) }}
                </NDescriptionsItem>
                <NDescriptionsItem label="MA20">
                  {{ fmt(indicators.ma?.MA20) }}
                </NDescriptionsItem>
                <NDescriptionsItem label="MA60">
                  {{ fmt(indicators.ma?.MA60) }}
                </NDescriptionsItem>
              </NDescriptions>
              <div class="indicator-signal-row">
                <span class="signal-label">信号:</span>
                <NTag :type="maSignal === '多头排列' ? 'error' : 'success'" size="small" round>
                  {{ maSignal }}
                </NTag>
              </div>
            </div>
          </NGridItem>

          <!-- MACD -->
          <NGridItem span="1 m:1 l:1">
            <div class="indicator-card">
              <div class="indicator-card-title">MACD</div>
              <NDescriptions :column="1" label-placement="left" size="small" bordered>
                <NDescriptionsItem label="DIF">
                  {{ fmt(indicators.macd?.DIF, 3) }}
                </NDescriptionsItem>
                <NDescriptionsItem label="DEA">
                  {{ fmt(indicators.macd?.DEA, 3) }}
                </NDescriptionsItem>
                <NDescriptionsItem label="MACD">
                  {{ fmt(indicators.macd?.MACD, 3) }}
                </NDescriptionsItem>
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

          <!-- RSI -->
          <NGridItem span="1 m:1 l:1">
            <div class="indicator-card">
              <div class="indicator-card-title">RSI</div>
              <NDescriptions :column="1" label-placement="left" size="small" bordered>
                <NDescriptionsItem label="RSI6">
                  {{ fmt(indicators.rsi?.RSI6, 2) }}
                </NDescriptionsItem>
                <NDescriptionsItem label="RSI12">
                  {{ fmt(indicators.rsi?.RSI12, 2) }}
                </NDescriptionsItem>
                <NDescriptionsItem label="RSI24">
                  {{ fmt(indicators.rsi?.RSI24, 2) }}
                </NDescriptionsItem>
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

          <!-- KDJ -->
          <NGridItem span="1 m:1 l:1">
            <div class="indicator-card">
              <div class="indicator-card-title">KDJ</div>
              <NDescriptions :column="1" label-placement="left" size="small" bordered>
                <NDescriptionsItem label="K">
                  {{ fmt(indicators.kdj?.K, 2) }}
                </NDescriptionsItem>
                <NDescriptionsItem label="D">
                  {{ fmt(indicators.kdj?.D, 2) }}
                </NDescriptionsItem>
                <NDescriptionsItem label="J">
                  {{ fmt(indicators.kdj?.J, 2) }}
                </NDescriptionsItem>
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

          <!-- BOLL -->
          <NGridItem span="1 m:1 l:1">
            <div class="indicator-card">
              <div class="indicator-card-title">BOLL 布林带</div>
              <NDescriptions :column="1" label-placement="left" size="small" bordered>
                <NDescriptionsItem label="上轨">
                  {{ fmt(indicators.bollinger?.upper) }}
                </NDescriptionsItem>
                <NDescriptionsItem label="中轨">
                  {{ fmt(indicators.bollinger?.middle) }}
                </NDescriptionsItem>
                <NDescriptionsItem label="下轨">
                  {{ fmt(indicators.bollinger?.lower) }}
                </NDescriptionsItem>
              </NDescriptions>
              <div class="indicator-signal-row">
                <span class="signal-label">位置:</span>
                <NTag size="small" round type="default">
                  {{ bollPosition }}
                </NTag>
                <NTag :type="bollSqueeze === '收窄' ? 'warning' : 'default'" size="small" round>
                  {{ bollSqueeze }}
                </NTag>
              </div>
            </div>
          </NGridItem>

          <!-- Volume -->
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
                <NDescriptionsItem label="量比">
                  {{ fmt(indicators.volume_analysis?.volume_ratio, 2) }}
                </NDescriptionsItem>
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

          <!-- ATR -->
          <NGridItem span="1 m:1 l:1">
            <div class="indicator-card">
              <div class="indicator-card-title">ATR 波动率</div>
              <NDescriptions :column="1" label-placement="left" size="small" bordered>
                <NDescriptionsItem label="ATR">
                  {{ fmt(indicators.atr?.ATR) }}
                </NDescriptionsItem>
                <NDescriptionsItem label="ATR%"> {{ fmt(indicators.atr?.ATR_percent, 2) }}% </NDescriptionsItem>
              </NDescriptions>
            </div>
          </NGridItem>

          <!-- OBV -->
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

          <!-- CCI -->
          <NGridItem span="1 m:1 l:1">
            <div class="indicator-card">
              <div class="indicator-card-title">CCI 顺势指标</div>
              <NDescriptions :column="1" label-placement="left" size="small" bordered>
                <NDescriptionsItem label="CCI">
                  {{ fmt(indicators.cci?.CCI, 2) }}
                </NDescriptionsItem>
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

          <!-- WR -->
          <NGridItem span="1 m:1 l:1">
            <div class="indicator-card">
              <div class="indicator-card-title">WR 威廉指标</div>
              <NDescriptions :column="1" label-placement="left" size="small" bordered>
                <NDescriptionsItem label="WR">
                  {{ fmt(indicators.wr?.WR, 2) }}
                </NDescriptionsItem>
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
      </NCard>

      <!-- Key Levels -->
      <NCard title="关键价位" :bordered="false" class="section-card">
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
      </NCard>
    </template>

    <!-- ==================== Empty State ==================== -->
    <NCard v-if="!result && !loading && !error" :bordered="false" class="empty-card">
      <NEmpty description="请输入股票代码开始分析" />
    </NCard>
  </div>
</template>

<style scoped>
.analysis-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ---------- Search Card ---------- */
.search-card {
  position: sticky;
  top: 0;
  z-index: 10;
}

/* ---------- Loading ---------- */
.loading-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  gap: 16px;
}

.loading-text {
  color: var(--text-color-3, #999);
  font-size: 14px;
}

/* ---------- Error ---------- */
.error-alert {
  margin-top: 8px;
}

/* ---------- Section Card ---------- */
.section-card {
  margin-bottom: 0;
}

/* ---------- Stock Header ---------- */
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
  gap: 8px;
}

.stock-name {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-color-1, #fff);
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
}

.change-pct {
  font-size: 18px;
  font-weight: 600;
}

.update-time {
  font-size: 12px;
  color: var(--text-color-3, #999);
}

.stock-header-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

.score-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.score-statistic {
  --score-color: #999;
}

.score-statistic :deep(.n-statistic-value__content) {
  color: var(--score-color);
  font-size: 32px;
  font-weight: 700;
}

.score-label {
  font-size: 13px;
  color: var(--text-color-3, #999);
}

.trend-tag {
  font-weight: 600;
}

.recommendation {
  font-size: 13px;
  color: var(--text-color-2, #bbb);
  max-width: 260px;
  text-align: right;
  line-height: 1.5;
}

/* ---------- Summary ---------- */
.summary-text {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-color-2, #ccc);
  margin: 0;
  white-space: pre-wrap;
}

/* ---------- Indicator Cards ---------- */
.indicator-card {
  background: var(--card-color-2, rgba(255, 255, 255, 0.03));
  border: 1px solid var(--border-color-2, rgba(255, 255, 255, 0.08));
  border-radius: 8px;
  padding: 14px;
  height: 100%;
}

.indicator-card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-color-1, #fff);
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color-2, rgba(255, 255, 255, 0.08));
}

.indicator-signal-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--border-color-2, rgba(255, 255, 255, 0.06));
}

.signal-label {
  font-size: 12px;
  color: var(--text-color-3, #999);
}

.divergence-text {
  font-size: 12px;
  color: var(--warning-color, #ff9500);
}

/* ---------- Key Levels ---------- */
.levels-section {
  padding: 12px 0;
}

.levels-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 2px solid;
}

.support-title {
  color: #26a69a;
  border-color: #26a69a;
}

.resistance-title {
  color: #ef5350;
  border-color: #ef5350;
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
  width: 28px;
  height: 22px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  background: var(--primary-color, #5b8ff9);
}

.level-value {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color-1, #fff);
  font-variant-numeric: tabular-nums;
}

.level-empty {
  font-size: 13px;
  color: var(--text-color-3, #999);
}

/* ---------- Empty State ---------- */
.empty-card {
  padding: 120px 0;
}

/* ---------- Responsive ---------- */
@media (max-width: 768px) {
  .analysis-page {
    padding: 8px;
    gap: 10px;
  }

  .stock-header {
    flex-direction: column;
    gap: 16px;
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

  .score-statistic :deep(.n-statistic-value__content) {
    font-size: 26px;
  }
}
</style>
