import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { AnalysisResult } from '../types'
import { analyzeStock } from '../api'

export const useAnalysisStore = defineStore('analysis', () => {
  const result = ref<AnalysisResult | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function analyze(code: string, market = 'auto', assetType = 'stock', days = 60) {
    loading.value = true
    error.value = null
    try {
      result.value = await analyzeStock(code, market, assetType, days)
    } catch (e: any) {
      error.value = e.message || '分析失败'
      result.value = null
    } finally {
      loading.value = false
    }
  }

  function clear() {
    result.value = null
    error.value = null
  }

  return { result, loading, error, analyze, clear }
})
