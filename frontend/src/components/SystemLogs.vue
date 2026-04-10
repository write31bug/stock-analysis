<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NCard, NDataTable, NSpace, NButton, NSelect, NPopconfirm, NSpin, NEmpty, NTag, useMessage } from 'naive-ui'
import { getLogs, clearLogs } from '../api'
import type { LogItem } from '../types'
import { formatDateTime } from '../utils/format'

const message = useMessage()

const logs = ref<LogItem[]>([])
const logsLoading = ref(false)
const logLevelFilter = ref<string | null>(null)

async function fetchLogs() {
  logsLoading.value = true
  try {
    logs.value = await getLogs({ level: logLevelFilter.value || undefined, limit: 200 })
  } catch { /* ignore */ }
  finally {
    logsLoading.value = false
  }
}

async function handleClearLogs() {
  try {
    const res = await clearLogs()
    message.success(res.message)
    logs.value = []
  } catch {
    message.error('清空日志失败')
  }
}

const logColumns = [
  { title: '时间', key: 'created_at', width: 160, render(row: LogItem) {
    return formatDateTime(row.created_at)
  }},
  { title: '级别', key: 'level', width: 80, render(row: LogItem) {
    const typeMap: Record<string, string> = { ERROR: 'error', WARNING: 'warning' }
    const tagType = typeMap[row.level] || 'info'
    return h(NTag, { size: 'small', type: tagType, bordered: false }, () => row.level)
  }},
  { title: '模块', key: 'module', width: 120, ellipsis: { tooltip: true }, render(row: LogItem) { return row.module || '--' } },
  { title: '内容', key: 'message', ellipsis: { tooltip: true } },
]

onMounted(() => {
  fetchLogs()
})

defineExpose({ fetchLogs })
</script>

<template>
  <NCard title="📋 系统日志" :bordered="false">
    <template #header-extra>
      <NSpace :size="8" align="center">
        <NSelect
          v-model:value="logLevelFilter"
          :options="[
            { label: '全部', value: null },
            { label: 'WARNING', value: 'WARNING' },
            { label: 'ERROR', value: 'ERROR' },
          ]"
          size="small"
          style="width: 120px"
          @update:value="fetchLogs"
        />
        <NButton size="small" @click="fetchLogs" :loading="logsLoading">刷新</NButton>
        <NPopconfirm @positive-click="handleClearLogs">
          <template #trigger>
            <NButton size="small" type="error" secondary>清空</NButton>
          </template>
          确定清空所有日志？
        </NPopconfirm>
      </NSpace>
    </template>
    <NSpin :show="logsLoading">
      <NDataTable
        :columns="logColumns"
        :data="logs"
        :bordered="false"
        :single-line="false"
        size="small"
        :row-key="(row: LogItem) => row.id"
        :max-height="400"
        :scroll-x="800"
      />
      <NEmpty v-if="!logsLoading && logs.length === 0" description="暂无日志" />
    </NSpin>
  </NCard>
</template>
