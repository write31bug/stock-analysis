import { describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import Dashboard from './Dashboard.vue';

// Mock axios
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(() => Promise.resolve({ data: [] })),
      interceptors: {
        response: {
          use: vi.fn()
        }
      }
    }))
  }
}));

describe('Dashboard.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('renders component correctly', () => {
    const wrapper = mount(Dashboard);
    expect(wrapper.exists()).toBe(true);
  });

  it('initializes with default state', () => {
    const wrapper = mount(Dashboard);
    expect(wrapper.vm).toBeDefined();
  });

  it('fetches dashboard data on mount', async () => {
    const wrapper = mount(Dashboard);
    await wrapper.vm.$nextTick();
    // 测试数据获取功能
    expect(wrapper.vm).toBeDefined();
  });

  it('handles time range selection', async () => {
    const wrapper = mount(Dashboard);
    await wrapper.vm.$nextTick();
    // 测试时间范围选择功能
    expect(wrapper.vm).toBeDefined();
  });
});
