<template>
  <n-config-provider :theme="darkTheme" :locale="zhCN" :date-locale="dateZhCN">
    <n-message-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <n-layout style="min-height: 100vh">
            <n-layout-header
              bordered
              style="padding: 0 24px; display: flex; align-items: center; height: 56px; gap: 24px"
            >
              <div class="app-logo" @click="router.push('/')">
                <span class="logo-icon">📈</span>
                <span class="logo-text">Stock Analysis</span>
              </div>
              <n-menu mode="horizontal" :value="activeMenu" :options="menuOptions" @update:value="handleMenuSelect" />
            </n-layout-header>
            <n-layout-content content-style="padding: 0;">
              <router-view />
            </n-layout-content>
          </n-layout>
        </n-notification-provider>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { darkTheme, zhCN, dateZhCN } from 'naive-ui'
import {
  NConfigProvider,
  NMessageProvider,
  NDialogProvider,
  NNotificationProvider,
  NLayout,
  NLayoutHeader,
  NLayoutContent,
  NMenu,
} from 'naive-ui'
import type { MenuOption } from 'naive-ui'

const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => {
  const path = route.path
  if (path === '/') return 'dashboard'
  if (path.startsWith('/analysis')) return 'analysis'
  if (path.startsWith('/history')) return 'history'
  if (path.startsWith('/alerts')) return 'alerts'
  return 'dashboard'
})

const menuOptions: MenuOption[] = [
  { label: '仪表盘', key: 'dashboard' },
  { label: '个股分析', key: 'analysis' },
  { label: '历史记录', key: 'history' },
  { label: '价格预警', key: 'alerts' },
]

function handleMenuSelect(key: string) {
  if (key === 'dashboard') router.push('/')
  else if (key === 'analysis') router.push('/analysis')
  else if (key === 'history') router.push('/history')
  else if (key === 'alerts') router.push('/alerts')
}
</script>

<style scoped>
.app-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  flex-shrink: 0;
}

.logo-icon {
  font-size: 24px;
}

.logo-text {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-color-1, #fff);
  letter-spacing: 0.5px;
}
</style>
