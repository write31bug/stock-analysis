<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import {
  NCard,
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NSelect,
  NButton,
  NTag,
  NSpace,
  NPopconfirm,
  NSpin,
  NEmpty,
  NText,
  useMessage,
} from 'naive-ui'
import { getAlerts, createAlert, deleteAlert, checkAlerts } from '../api'
import type { PriceAlert } from '../types'

const message = useMessage()

const formCode = ref('')
const formName = ref('')
const formConditionType = ref<'above' | 'below' | 'pct_change_above' | 'pct_change_below'>('above')
const formTargetValue = ref<number | null>(null)

const conditionTypeOptions = [
  { label: '价格高于', value: 'above' },
  { label: '价格低于', value: 'below' },
  { label: '涨幅高于', value: 'pct_change_above' },
  { label: '跌幅低于', value: 'pct_change_below' },
]

const loading = ref(false)
const alerts = ref<PriceAlert[]>([])
const checking = ref(false)

const conditionLabelMap: Record<string, string> = {
  above: '价格高于',
  below: '价格低于',
  pct_change_above: '涨幅高于',
  pct_change_below: '跌幅低于',
}

async function fetchAlerts() {
  loading.value = true
  try {
    alerts.value = await getAlerts()
  } catch {
    message.error('获取预警列表失败')
  } finally {
    loading.value = false
  }
}

async function handleCreateAlert() {
  const code = formCode.value.trim()
  if (!code) {
    message.warning('请输入股票代码')
    return
  }
  if (formTargetValue.value == null || isNaN(formTargetValue.value)) {
    message.warning('请输入目标值')
    return
  }

  try {
    await createAlert({
      code,
      name: formName.value.trim(),
      condition_type: formConditionType.value,
      target_value: formTargetValue.value,
    })
    message.success('预警创建成功')
    formCode.value = ''
    formName.value = ''
    formConditionType.value = 'above'
    formTargetValue.value = null
    await fetchAlerts()
  } catch {
    message.error('创建预警失败')
  }
}

async function handleDeleteAlert(id: number) {
  try {
    await deleteAlert(id)
    message.success('预警已删除')
    await fetchAlerts()
  } catch {
    message.error('删除失败')
  }
}

async function handleCheckAlerts() {
  checking.value = true
  try {
    const result = await checkAlerts()
    const triggered = result?.triggered ?? result?.count ?? 0
    if (triggered > 0) {
      message.success(`检查完成，触发 ${triggered} 条预警`)
    } else {
      message.info('检查完成，暂无触发预警')
    }
    await fetchAlerts()
  } catch {
    message.error('检查预警失败')
  } finally {
    checking.value = false
  }
}

function formatTime(time: string | null): string {
  if (!time) return '--'
  return time.replace('T', ' ').slice(0, 19)
}

const columns = [
  {
    title: '代码',
    key: 'code',
    width: 100,
    render(row: PriceAlert) {
      return h(NText, { strong: true }, () => row.code)
    },
  },
  {
    title: '名称',
    key: 'name',
    width: 100,
    ellipsis: { tooltip: true },
    render(row: PriceAlert) {
      return row.name || '--'
    },
  },
  {
    title: '条件',
    key: 'condition_type',
    width: 120,
    render(row: PriceAlert) {
      return h(NTag, { size: 'small', type: 'info', bordered: false }, () => conditionLabelMap[row.condition_type] ?? row.condition_type)
    },
  },
  {
    title: '目标值',
    key: 'target_value',
    width: 100,
    align: 'right' as const,
    render(row: PriceAlert) {
      const suffix = row.condition_type.startsWith('pct') ? '%' : ''
      return h(NText, {}, () => `${row.target_value}${suffix}`)
    },
  },
  {
    title: '当前价',
    key: 'current_price',
    width: 100,
    align: 'right' as const,
    render(row: PriceAlert) {
      if (row.current_price == null) return '--'
      return h(NText, {}, () => row.current_price.toFixed(2))
    },
  },
  {
    title: '状态',
    key: 'triggered',
    width: 80,
    align: 'center' as const,
    render(row: PriceAlert) {
      return h(
        NTag,
        {
          size: 'small',
          type: row.triggered ? 'success' : 'warning',
          round: true,
          bordered: false,
        },
        () => (row.triggered ? '已触发' : '待触发'),
      )
    },
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 170,
    render(row: PriceAlert) {
      return h('span', { style: { fontSize: '13px', color: '#6b7280' } }, formatTime(row.created_at))
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    render(row: PriceAlert) {
      return h(
        NPopconfirm,
        { onPositiveClick: () => handleDeleteAlert(row.id) },
        {
          trigger: () =>
            h(NButton, { size: 'small', type: 'error', secondary: true }, () => '删除'),
          default: () => '确定删除该预警？',
        },
      )
    },
  },
]

onMounted(() => {
  fetchAlerts()
})
</script>

<template>
  <div class="alerts-page">
    <div class="page-header">
      <h1 class="page-title">价格预警</h1>
      <p class="page-subtitle">设置价格条件，自动监控预警</p>
    </div>

    <div class="content-section">
      <div class="section-header">
        <h2 class="section-title">新建预警</h2>
      </div>
      <NForm label-placement="left" label-width="80" :show-feedback="false" inline class="alert-form">
        <NFormItem label="股票代码">
          <NInput
            v-model:value="formCode"
            placeholder="如 600519"
            clearable
            class="form-input"
          />
        </NFormItem>
        <NFormItem label="名称">
          <NInput
            v-model:value="formName"
            placeholder="可选"
            clearable
            class="form-input"
          />
        </NFormItem>
        <NFormItem label="条件类型">
          <NSelect
            v-model:value="formConditionType"
            :options="conditionTypeOptions"
            class="form-select"
          />
        </NFormItem>
        <NFormItem label="目标值">
          <NInput
            v-model:value="formTargetValue"
            placeholder="目标值"
            type="number"
            clearable
            class="form-input"
          />
        </NFormItem>
        <NFormItem label=" ">
          <NButton type="primary" @click="handleCreateAlert" class="add-button">添加预警</NButton>
        </NFormItem>
      </NForm>
    </div>

    <div class="content-section">
      <div class="section-header">
        <h2 class="section-title">预警列表</h2>
        <NButton
          type="warning"
          :loading="checking"
          :disabled="alerts.length === 0"
          @click="handleCheckAlerts"
          class="check-button"
        >
          检查预警
        </NButton>
      </div>

      <NSpin :show="loading">
        <NDataTable
          v-if="alerts.length > 0"
          :columns="columns"
          :data="alerts"
          :bordered="false"
          :single-line="false"
          size="small"
          :row-key="(row: PriceAlert) => row.id"
          :scroll-x="920"
          class="alert-table"
        />
        <div v-else class="empty-state">
          <NEmpty description="暂无预警，请添加" />
        </div>
      </NSpin>
    </div>
  </div>
</template>

<style scoped>
.alerts-page {
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

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.alert-form {
  flex-wrap: wrap;
  gap: 12px;
}

.form-input {
  width: 140px;
}

.form-select {
  width: 140px;
}

.add-button {
  font-weight: 500;
}

.check-button {
  font-weight: 500;
}

.alert-table {
  border-radius: 8px;
}

.empty-state {
  padding: 48px 0;
}

@media (max-width: 768px) {
  .alerts-page {
    padding: 20px 16px;
    gap: 20px;
  }

  .page-title {
    font-size: 24px;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .alert-form {
    flex-direction: column;
    align-items: stretch;
  }

  .form-input,
  .form-select {
    width: 100% !important;
  }
}
</style>
