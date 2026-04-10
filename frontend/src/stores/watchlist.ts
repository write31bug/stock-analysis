import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { WatchlistItem } from '../types'
import { getWatchlist, addToWatchlist as apiAdd, removeFromWatchlist as apiRemove, getWatchlistGroups, createGroup as apiCreateGroup, deleteGroup as apiDeleteGroup } from '../api'

export const useWatchlistStore = defineStore('watchlist', () => {
  const items = ref<WatchlistItem[]>([])
  const loading = ref(false)
  const groups = ref<string[]>([])
  const currentGroup = ref<string | null>(null)

  const filteredItems = computed(() => {
    if (!currentGroup.value) return items.value
    return items.value.filter((item) => item.group === currentGroup.value)
  })

  async function fetch() {
    loading.value = true
    try {
      items.value = await getWatchlist()
    } finally {
      loading.value = false
    }
  }

  async function add(code: string, name = '', group?: string) {
    await apiAdd(code, name, group)
    await fetch()
  }

  async function remove(code: string) {
    await apiRemove(code)
    await fetch()
  }

  async function fetchGroups() {
    try {
      groups.value = await getWatchlistGroups()
    } catch {
      groups.value = []
    }
  }

  async function addGroup(name: string) {
    await apiCreateGroup(name)
    await fetchGroups()
  }

  async function removeGroup(name: string) {
    await apiDeleteGroup(name)
    if (currentGroup.value === name) {
      currentGroup.value = null
    }
    await fetchGroups()
    await fetch()
  }

  return { items, loading, groups, currentGroup, filteredItems, fetch, add, remove, fetchGroups, addGroup, removeGroup }
})
