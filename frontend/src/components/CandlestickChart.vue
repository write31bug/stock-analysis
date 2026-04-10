<script setup lang="ts">
import { computed, watch } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CandlestickChart as CandlestickSeries, LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, DataZoomComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { OHLCVItem, SeriesPoint } from '../types'

use([
  CandlestickSeries,
  LineChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  LegendComponent,
  CanvasRenderer,
])

// ---------- A 股配色常量 ----------
const COLOR_UP = '#ef5350' // 涨 - 红色
const COLOR_DOWN = '#26a69a' // 跌 - 绿色
const COLOR_UP_ALPHA = 'rgba(239,83,80,0.85)'
const COLOR_DOWN_ALPHA = 'rgba(38,166,154,0.85)'

// MA 均线配色
const MA_COLORS: Record<string, string> = {
  MA5: '#FF9500',
  MA10: '#5B8FF9',
  MA20: '#F6903D',
  MA60: '#61DDAA',
}

// ---------- Props ----------
interface Props {
  ohlcv: OHLCVItem[]
  maSeries?: Record<string, SeriesPoint[]>
  height?: number
}

const props = withDefaults(defineProps<Props>(), {
  maSeries: () => ({}),
  height: 500,
})

// ---------- ECharts Option ----------
const chartOption = computed(() => {
  const { ohlcv, maSeries } = props

  if (!ohlcv || ohlcv.length === 0) {
    return null
  }

  const dates = ohlcv.map((item) => item.date)
  const candlestickData = ohlcv.map((item) => [item.open, item.close, item.low, item.high])
  const volumeData = ohlcv.map((item) => ({
    value: item.volume,
    itemStyle: {
      color: item.close >= item.open ? COLOR_UP_ALPHA : COLOR_DOWN_ALPHA,
    },
  }))

  // 构建 MA 均线 series
  const maSeriesList = Object.entries(maSeries).map(([name, points]) => {
    const color = MA_COLORS[name] ?? '#999'
    const data = dates.map((date) => {
      const point = points.find((p) => p.date === date)
      return point?.value ?? null
    })
    return {
      name,
      type: 'line' as const,
      xAxisIndex: 0,
      yAxisIndex: 0,
      data,
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 1 },
      itemStyle: { color },
    }
  })

  return {
    animation: false, // 关闭动画以提高性能
    animationDuration: 0,
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        crossStyle: { color: '#999' },
        lineStyle: { color: '#666', type: 'dashed' },
      },
      backgroundColor: 'rgba(32,33,36,0.92)',
      borderColor: '#555',
      textStyle: { color: '#eee', fontSize: 12 },
      formatter(params: any[]) {
        if (!params || params.length === 0) return ''
        const candleParam = params.find((p) => p.seriesType === 'candlestick')
        const volumeParam = params.find((p) => p.seriesType === 'bar')
        if (!candleParam) return ''

        const d = candleParam.data
        const date = candleParam.axisValue
        const o = d[1]
        const c = d[2]
        const l = d[3]
        const h = d[4]
        const change = c - o
        const changePct = o !== 0 ? ((change / o) * 100).toFixed(2) : '0.00'
        const sign = change >= 0 ? '+' : ''
        const color = change >= 0 ? COLOR_UP : COLOR_DOWN

        let html = `<div style="margin-bottom:4px;font-weight:bold">${date}</div>`
        html += `<div>开盘: <span style="color:${color}">${o.toFixed(2)}</span></div>`
        html += `<div>收盘: <span style="color:${color}">${c.toFixed(2)}</span></div>`
        html += `<div>最高: <span style="color:${color}">${h.toFixed(2)}</span></div>`
        html += `<div>最低: <span style="color:${color}">${l.toFixed(2)}</span></div>`
        html += `<div>涨跌: <span style="color:${color}">${sign}${change.toFixed(2)} (${sign}${changePct}%)</span></div>`

        if (volumeParam) {
          const vol = volumeParam.data?.value ?? volumeParam.data
          html += `<div>成交量: ${(Number(vol) / 10000).toFixed(0)} 万</div>`
        }

        // MA 值
        const maParams = params.filter((p) => p.seriesType === 'line' && p.data != null)
        for (const mp of maParams) {
          html += `<div>${mp.seriesName}: <span style="color:${mp.color}">${Number(mp.data).toFixed(2)}</span></div>`
        }

        return html
      },
    },
    legend: {
      data: ['K线', '成交量', ...Object.keys(maSeries)],
      top: 0,
      left: 'center',
      textStyle: { color: '#ccc', fontSize: 11 },
      itemWidth: 14,
      itemHeight: 10,
    },
    grid: [
      {
        left: '8%',
        right: '4%',
        top: 40,
        height: '60%',
      },
      {
        left: '8%',
        right: '4%',
        top: '76%',
        height: '14%',
      },
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        boundaryGap: true,
        axisLine: { lineStyle: { color: '#555' } },
        axisLabel: { color: '#aaa', fontSize: 11 },
        splitLine: { show: false },
        axisTick: { show: false },
      },
      {
        type: 'category',
        gridIndex: 1,
        data: dates,
        boundaryGap: true,
        axisLine: { lineStyle: { color: '#555' } },
        axisLabel: { show: false },
        splitLine: { show: false },
        axisTick: { show: false },
      },
    ],
    yAxis: [
      {
        scale: true,
        position: 'left',
        axisLine: { show: false },
        axisLabel: { color: '#aaa', fontSize: 11 },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        axisTick: { show: false },
      },
      {
        scale: true,
        gridIndex: 1,
        position: 'left',
        axisLine: { show: false },
        axisLabel: {
          color: '#aaa',
          fontSize: 10,
          formatter: (val: number) => {
            if (val >= 1e8) return (val / 1e8).toFixed(1) + '亿'
            if (val >= 1e4) return (val / 1e4).toFixed(0) + '万'
            return String(val)
          },
        },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        axisTick: { show: false },
      },
    ],
    dataZoom: [
      {
        type: 'slider',
        xAxisIndex: [0, 1],
        bottom: '2%',
        height: 24,
        start: 0,
        end: 100,
        borderColor: '#444',
        backgroundColor: 'rgba(40,42,48,0.8)',
        fillerColor: 'rgba(80,160,240,0.2)',
        handleStyle: { color: '#5B8FF9', borderColor: '#5B8FF9' },
        moveHandleStyle: { color: '#5B8FF9' },
        textStyle: { color: '#aaa' },
        dataBackground: {
          lineStyle: { color: '#555' },
          areaStyle: { color: 'rgba(80,160,240,0.1)' },
        },
        selectedDataBackground: {
          lineStyle: { color: '#5B8FF9' },
          areaStyle: { color: 'rgba(80,160,240,0.2)' },
        },
      },
      {
        type: 'inside',
        xAxisIndex: [0, 1],
      },
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: candlestickData,
        itemStyle: {
          color: COLOR_UP, // 涨 - 填充色（阳线）
          color0: COLOR_DOWN, // 跌 - 填充色（阴线）
          borderColor: COLOR_UP, // 涨 - 边框色
          borderColor0: COLOR_DOWN, // 跌 - 边框色
        },
      },
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumeData,
      },
      ...maSeriesList,
    ],
  }
})

// ---------- 响应式更新 ----------
// 移除深度监听，因为chartOption是computed，会自动响应变化
// 当数据变化时，computed会重新计算，VChart会自动更新
</script>

<template>
  <div class="candlestick-chart-wrapper">
    <template v-if="ohlcv && ohlcv.length > 0">
      <VChart class="candlestick-chart" :option="chartOption" :autoresize="true" :style="{ height: `${height}px` }" />
    </template>
    <div v-else class="candlestick-chart-empty">
      <span>暂无数据</span>
    </div>
  </div>
</template>

<style scoped>
.candlestick-chart-wrapper {
  width: 100%;
  position: relative;
}

.candlestick-chart {
  width: 100%;
  min-height: 300px;
}

.candlestick-chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 300px;
  color: var(--text-color-3, #999);
  font-size: 14px;
  background-color: var(--card-color, #1e1e1e);
  border-radius: 4px;
}
</style>
