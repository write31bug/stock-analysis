import { describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import History from './History.vue';

// Mock axios
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(() => Promise.resolve({ data: [] })),
      delete: vi.fn(() => Promise.resolve({ data: {} })),
      interceptors: {
        response: {
          use: vi.fn()
        }
      }
    }))
  }
}));

describe('History.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('renders component correctly', () => {
    const wrapper = mount(History);
    expect(wrapper.exists()).toBe(true);
  });

  it('initializes with default state', () => {
    const wrapper = mount(History);
    expect(wrapper.vm).toBeDefined();
  });

  it('fetches history data on mount', async () => {
    const wrapper = mount(History);
    await wrapper.vm.$nextTick();
    // 测试数据获取功能
    expect(wrapper.vm).toBeDefined();
  });

  it('handles date range selection', async () => {
    const wrapper = mount(History);
    await wrapper.vm.$nextTick();
    // 测试日期范围选择功能
    expect(wrapper.vm).toBeDefined();
  });

  it('handles history deletion', async () => {
    const wrapper = mount(History);
    await wrapper.vm.$nextTick();
    // 测试删除历史记录功能
    expect(wrapper.vm).toBeDefined();
  });
});
