<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import {
  NCard,
  NPageHeader,
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

// ---------- Message ----------

const message = useMessage()

// ---------- Form State ----------

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

// ---------- Table State ----------

const loading = ref(false)
const alerts = ref<PriceAlert[]>([])
const checking = ref(false)

// ---------- Condition Label Map ----------

const conditionLabelMap: Record<string, string> = {
  above: '价格高于',
  below: '价格低于',
  pct_change_above: '涨幅高于',
  pct_change_below: '跌幅低于',
}

// ---------- Fetch Alerts ----------

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

// ---------- Create Alert ----------

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

// ---------- Delete Alert ----------

async function handleDeleteAlert(id: number) {
  try {
    await deleteAlert(id)
    message.success('预警已删除')
    await fetchAlerts()
  } catch {
    message.error('删除失败')
  }
}

// ---------- Check Alerts ----------

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

// ---------- Format Time ----------

function formatTime(time: string | null): string {
  if (!time) return '--'
  return time.replace('T', ' ').slice(0, 19)
}

// ---------- Table Columns ----------

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
      return h('span', { style: { fontSize: '13px', color: '#bbb' } }, formatTime(row.created_at))
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

// ---------- Lifecycle ----------

onMounted(() => {
  fetchAlerts()
})
</script>

<template>
  <div class="alerts-page">
    <!-- ==================== Page Header ==================== -->
    <NCard :bordered="false" class="header-card">
      <NPageHeader title="价格预警" subtitle="设置价格条件，自动监控预警" />
    </NCard>

    <!-- ==================== Create Alert Form ==================== -->
    <NCard title="新建预警" :bordered="false">
      <NForm label-placement="left" label-width="80" :show-feedback="false" inline>
        <NFormItem label="股票代码">
          <NInput
            v-model:value="formCode"
            placeholder="如 600519"
            clearable
            style="width: 140px"
          />
        </NFormItem>
        <NFormItem label="名称">
          <NInput
            v-model:value="formName"
            placeholder="可选"
            clearable
            style="width: 140px"
          />
        </NFormItem>
        <NFormItem label="条件类型">
          <NSelect
            v-model:value="formConditionType"
            :options="conditionTypeOptions"
            style="width: 140px"
          />
        </NFormItem>
        <NFormItem label="目标值">
          <NInput
            v-model:value="formTargetValue"
            placeholder="目标值"
            type="number"
            clearable
            style="width: 120px"
          />
        </NFormItem>
        <NFormItem label=" ">
          <NButton type="primary" @click="handleCreateAlert"> 添加预警 </NButton>
        </NFormItem>
      </NForm>
    </NCard>

    <!-- ==================== Alert List ==================== -->
    <NCard title="预警列表" :bordered="false">
      <NSpace vertical :size="12">
        <NSpace :size="8" align="center">
          <NButton
            type="warning"
            :loading="checking"
            :disabled="alerts.length === 0"
            @click="handleCheckAlerts"
          >
            检查预警
          </NButton>
        </NSpace>

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
          />
          <NEmpty v-else description="暂无预警，请添加" style="padding: 32px 0" />
        </NSpin>
      </NSpace>
    </NCard>
  </div>
</template>

<style scoped>
.alerts-page {
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

/* ---------- Responsive ---------- */
@media (max-width: 768px) {
  .alerts-page {
    padding: 8px;
    gap: 10px;
  }
}
</style>
