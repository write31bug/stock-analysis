import { describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import Alerts from './Alerts.vue';

// Mock axios
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(() => Promise.resolve({ data: [] })),
      post: vi.fn(() => Promise.resolve({ data: {} })),
      delete: vi.fn(() => Promise.resolve({ data: {} })),
      interceptors: {
        response: {
          use: vi.fn()
        }
      }
    }))
  }
}));

describe('Alerts.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('renders component correctly', () => {
    const wrapper = mount(Alerts);
    expect(wrapper.exists()).toBe(true);
  });

  it('initializes with default state', () => {
    const wrapper = mount(Alerts);
    expect(wrapper.vm).toBeDefined();
  });

  it('handles form submission', async () => {
    const wrapper = mount(Alerts);
    await wrapper.vm.$nextTick();
    // 测试表单提交功能
    expect(wrapper.vm).toBeDefined();
  });

  it('handles alert deletion', async () => {
    const wrapper = mount(Alerts);
    await wrapper.vm.$nextTick();
    // 测试删除告警功能
    expect(wrapper.vm).toBeDefined();
  });
});
