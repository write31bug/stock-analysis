<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { GridComponent, TooltipComponent, DataZoomComponent, MarkLineComponent } from 'echarts/components'
import { LineChart, BarChart } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'
import { NEmpty } from 'naive-ui'
import type { SeriesPoint } from '../types'

use([GridComponent, TooltipComponent, DataZoomComponent, MarkLineComponent, LineChart, BarChart, CanvasRenderer])

interface Props {
  indicatorSeries: Record<string, SeriesPoint[]>
  height?: number
}

const props = withDefaults(defineProps<Props>(), {
  height: 400,
})

/* ------------------------------------------------------------------ */
/*  辅助：判断某个指标组是否存在                                        */
/* ------------------------------------------------------------------ */

const hasMACD = computed(() => {
  const s = props.indicatorSeries
  return (s.DIF && s.DIF.length > 0) || (s.DEA && s.DEA.length > 0) || (s.MACD && s.MACD.length > 0)
})

const hasRSI = computed(() => {
  const s = props.indicatorSeries
  return (s.RSI6 && s.RSI6.length > 0) || (s.RSI12 && s.RSI12.length > 0) || (s.RSI24 && s.RSI24.length > 0)
})

const hasKDJ = computed(() => {
  const s = props.indicatorSeries
  return (s.K && s.K.length > 0) || (s.D && s.D.length > 0) || (s.J && s.J.length > 0)
})

const hasOBV = computed(() => {
  const s = props.indicatorSeries
  return s.OBV && s.OBV.length > 0
})

const hasAnyData = computed(() => hasMACD.value || hasRSI.value || hasKDJ.value || hasOBV.value)

/* ------------------------------------------------------------------ */
/*  提取日期轴（取所有指标中日期最长的序列）                              */
/* ------------------------------------------------------------------ */

const dates = computed<string[]>(() => {
  let longest: SeriesPoint[] = []
  for (const key of Object.keys(props.indicatorSeries)) {
    const arr = props.indicatorSeries[key]
    if (arr && arr.length > longest.length) {
      longest = arr
    }
  }
  return longest.map((p) => p.date)
})

/* ------------------------------------------------------------------ */
/*  将 SeriesPoint[] 转为 ECharts 需要的 [date, value][] 格式          */
/* ------------------------------------------------------------------ */

function toPairArray(series: SeriesPoint[]): [string, number | null][] {
  return series.map((p) => [p.date, p.value])
}

/* ------------------------------------------------------------------ */
/*  可见子图数量 & 各子图高度比例                                       */
/* ------------------------------------------------------------------ */

const visibleChartCount = computed(() => {
  let count = 0
  if (hasMACD.value) count++
  if (hasRSI.value) count++
  if (hasKDJ.value) count++
  if (hasOBV.value) count++
  return count
})

/* ------------------------------------------------------------------ */
/*  构建 ECharts option                                                */
/* ------------------------------------------------------------------ */

const chartOption = computed(() => {
  if (!hasAnyData.value) return null

  const count = visibleChartCount.value
  if (count === 0) return null

  const totalHeight = props.height
  const dataZoomHeight = 30
  const gap = 20
  const chartAreaHeight = totalHeight - dataZoomHeight - gap * (count - 1)
  const eachHeight = Math.max(40, Math.floor(chartAreaHeight / count))

  const grids: any[] = []
  const xAxes: any[] = []
  const yAxes: any[] = []
  const series: any[] = []

  let gridIndex = 0
  let yAxisIndex = 0
  let topOffset = 10

  /* ---------- MACD ---------- */
  if (hasMACD.value) {
    grids.push({
      left: 60,
      right: 20,
      top: topOffset,
      height: eachHeight,
    })

    xAxes.push({
      type: 'category',
      gridIndex,
      data: dates.value,
      show: false,
      boundaryGap: true,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: false },
    })

    yAxes.push({
      type: 'value',
      gridIndex,
      name: 'MACD',
      nameLocation: 'end',
      nameTextStyle: { color: '#999', fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#333', type: 'dashed' } },
      axisLabel: { color: '#999', fontSize: 10 },
    })

    // DIF line
    if (props.indicatorSeries.DIF?.length) {
      series.push({
        name: 'DIF',
        type: 'line',
        xAxisIndex: gridIndex,
        yAxisIndex,
        data: toPairArray(props.indicatorSeries.DIF),
        symbol: 'none',
        lineStyle: { color: '#FF9500', width: 1 },
        z: 2,
      })
    }

    // DEA line
    if (props.indicatorSeries.DEA?.length) {
      series.push({
        name: 'DEA',
        type: 'line',
        xAxisIndex: gridIndex,
        yAxisIndex,
        data: toPairArray(props.indicatorSeries.DEA),
        symbol: 'none',
        lineStyle: { color: '#5B8FF9', width: 1 },
        z: 2,
      })
    }

    // MACD histogram
    if (props.indicatorSeries.MACD?.length) {
      const macdData = props.indicatorSeries.MACD.map((p) => ({
        value: [p.date, p.value],
        itemStyle: {
          color: p.value !== null && p.value >= 0 ? '#ef5350' : '#26a69a',
        },
      }))
      series.push({
        name: 'MACD',
        type: 'bar',
        xAxisIndex: gridIndex,
        yAxisIndex,
        data: macdData,
        barMaxWidth: 6,
        z: 1,
      })
    }

    topOffset += eachHeight + gap
    gridIndex++
    yAxisIndex++
  }

  /* ---------- RSI ---------- */
  if (hasRSI.value) {
    grids.push({
      left: 60,
      right: 20,
      top: topOffset,
      height: eachHeight,
    })

    xAxes.push({
      type: 'category',
      gridIndex,
      data: dates.value,
      show: false,
      boundaryGap: true,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: false },
    })

    yAxes.push({
      type: 'value',
      gridIndex,
      name: 'RSI',
      nameLocation: 'end',
      nameTextStyle: { color: '#999', fontSize: 11 },
      min: 0,
      max: 100,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#333', type: 'dashed' } },
      axisLabel: { color: '#999', fontSize: 10 },
    })

    const rsiMarkLine = {
      silent: true,
      symbol: 'none',
      lineStyle: { color: '#666', type: 'dashed', width: 1 },
      label: { show: false },
      data: [{ yAxis: 70 }, { yAxis: 30 }],
    }

    if (props.indicatorSeries.RSI6?.length) {
      series.push({
        name: 'RSI6',
        type: 'line',
        xAxisIndex: gridIndex,
        yAxisIndex,
        data: toPairArray(props.indicatorSeries.RSI6),
        symbol: 'none',
        lineStyle: { color: '#FF9500', width: 1 },
        markLine: rsiMarkLine,
        z: 2,
      })
    }

    if (props.indicatorSeries.RSI12?.length) {
      series.push({
        name: 'RSI12',
        type: 'line',
        xAxisIndex: gridIndex,
        yAxisIndex,
        data: toPairArray(props.indicatorSeries.RSI12),
        symbol: 'none',
        lineStyle: { color: '#5B8FF9', width: 1 },
        z: 2,
      })
    }

    if (props.indicatorSeries.RSI24?.length) {
      series.push({
        name: 'RSI24',
        type: 'line',
        xAxisIndex: gridIndex,
        yAxisIndex,
        data: toPairArray(props.indicatorSeries.RSI24),
        symbol: 'none',
        lineStyle: { color: '#F6903D', width: 1 },
        z: 2,
      })
    }

    topOffset += eachHeight + gap
    gridIndex++
    yAxisIndex++
  }

  /* ---------- KDJ ---------- */
  if (hasKDJ.value) {
    grids.push({
      left: 60,
      right: 20,
      top: topOffset,
      height: eachHeight,
    })

    xAxes.push({
      type: 'category',
      gridIndex,
      data: dates.value,
      show: gridIndex === count - 1, // 仅最后一个子图显示 x 轴标签
      boundaryGap: true,
      axisLine: { lineStyle: { color: '#555' } },
      axisTick: { show: false },
      axisLabel: { color: '#999', fontSize: 10 },
    })

    yAxes.push({
      type: 'value',
      gridIndex,
      name: 'KDJ',
      nameLocation: 'end',
      nameTextStyle: { color: '#999', fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#333', type: 'dashed' } },
      axisLabel: { color: '#999', fontSize: 10 },
    })

    const kdjMarkLine = {
      silent: true,
      symbol: 'none',
      lineStyle: { color: '#666', type: 'dashed', width: 1 },
      label: { show: false },
      data: [{ yAxis: 80 }, { yAxis: 20 }],
    }

    if (props.indicatorSeries.K?.length) {
      series.push({
        name: 'K',
        type: 'line',
        xAxisIndex: gridIndex,
        yAxisIndex,
        data: toPairArray(props.indicatorSeries.K),
        symbol: 'none',
        lineStyle: { color: '#5B8FF9', width: 1 },
        markLine: kdjMarkLine,
        z: 2,
      })
    }

    if (props.indicatorSeries.D?.length) {
      series.push({
        name: 'D',
        type: 'line',
        xAxisIndex: gridIndex,
        yAxisIndex,
        data: toPairArray(props.indicatorSeries.D),
        symbol: 'none',
        lineStyle: { color: '#F6903D', width: 1 },
        z: 2,
      })
    }

    if (props.indicatorSeries.J?.length) {
      series.push({
        name: 'J',
        type: 'line',
        xAxisIndex: gridIndex,
        yAxisIndex,
        data: toPairArray(props.indicatorSeries.J),
        symbol: 'none',
        lineStyle: { color: '#61DDAA', width: 1 },
        z: 2,
      })
    }

    topOffset += eachHeight + gap
    gridIndex++
    yAxisIndex++
  }

  /* ---------- OBV ---------- */
  if (hasOBV.value) {
    grids.push({
      left: 60,
      right: 20,
      top: topOffset,
      height: eachHeight,
    })

    xAxes.push({
      type: 'category',
      gridIndex,
      data: dates.value,
      show: gridIndex === count - 1, // only last sub-chart shows x-axis labels
      boundaryGap: true,
      axisLine: { lineStyle: { color: '#555' } },
      axisTick: { show: false },
      axisLabel: { color: '#999', fontSize: 10 },
    })

    yAxes.push({
      type: 'value',
      gridIndex,
      name: 'OBV',
      nameLocation: 'end',
      nameTextStyle: { color: '#999', fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#333', type: 'dashed' } },
      axisLabel: { color: '#999', fontSize: 10 },
    })

    series.push({
      name: 'OBV',
      type: 'bar',
      xAxisIndex: gridIndex,
      yAxisIndex,
      data: props.indicatorSeries.OBV.map((p) => ({
        value: [p.date, p.value],
        itemStyle: {
          color: p.value !== null && p.value >= 0 ? '#ef5350' : '#26a69a',
        },
      })),
      barMaxWidth: 6,
      z: 1,
    })
  }

  /* ---------- DataZoom ---------- */
  const dataZoom: any[] = [
    {
      type: 'slider',
      xAxisIndex: xAxes.map((_, i) => i),
      bottom: 5,
      height: dataZoomHeight,
      borderColor: '#444',
      backgroundColor: '#1a1a2e',
      fillerColor: 'rgba(91,143,249,0.15)',
      handleStyle: { color: '#5B8FF9' },
      textStyle: { color: '#999' },
      dataBackground: {
        lineStyle: { color: '#5B8FF9' },
        areaStyle: { color: 'rgba(91,143,249,0.1)' },
      },
      selectedDataBackground: {
        lineStyle: { color: '#5B8FF9' },
        areaStyle: { color: 'rgba(91,143,249,0.2)' },
      },
    },
  ]

  /* ---------- 组装 option ---------- */
  return {
    backgroundColor: 'transparent',
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        crossStyle: { color: '#666' },
        lineStyle: { color: '#666', type: 'dashed' },
      },
      backgroundColor: 'rgba(20, 20, 40, 0.9)',
      borderColor: '#444',
      textStyle: { color: '#ddd', fontSize: 12 },
      formatter(params: any[]): string {
        if (!params || params.length === 0) return ''
        const date = params[0].axisValue
        let html = `<div style="margin-bottom:4px;font-weight:bold">${date}</div>`
        // 按指标分组
        const groups: Record<string, any[]> = {}
        for (const p of params) {
          const seriesName = p.seriesName as string
          if (seriesName === 'MACD_bar') continue
          if (!groups[seriesName]) groups[seriesName] = []
          groups[seriesName].push(p)
        }
        for (const [name, items] of Object.entries(groups)) {
          const val = items[0].value
          const displayVal = Array.isArray(val) ? val[1] : val
          if (displayVal == null) continue
          const color = items[0].color
          html += `<div style="display:flex;align-items:center;gap:6px;margin:2px 0">`
          html += `<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${color}"></span>`
          html += `<span>${name}:</span>`
          html += `<span style="font-weight:bold;margin-left:auto">${Number(displayVal).toFixed(3)}</span>`
          html += `</div>`
        }
        return html
      },
    },
    grid: grids,
    xAxis: xAxes,
    yAxis: yAxes,
    dataZoom,
    series,
  }
})

/* ------------------------------------------------------------------ */
/*  自动调整大小                                                       */
/* ------------------------------------------------------------------ */

const autoresize = true
</script>

<template>
  <div class="indicator-charts-wrapper">
    <NEmpty v-if="!hasAnyData" description="暂无数据" style="padding: 60px 0" />
    <VChart
      v-else
      class="indicator-charts"
      :option="chartOption"
      :autoresize="autoresize"
      :style="{ height: `${height}px`, width: '100%' }"
    />
  </div>
</template>

<style scoped>
.indicator-charts-wrapper {
  width: 100%;
}

.indicator-charts {
  width: 100%;
  min-height: 200px;
}
</style>
