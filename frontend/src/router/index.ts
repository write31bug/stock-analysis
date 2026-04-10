import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('../views/Dashboard.vue'),
    },
    {
      path: '/analysis',
      name: 'analysis',
      component: () => import('../views/Analysis.vue'),
    },
    {
      path: '/analysis/:code',
      name: 'analysis-code',
      component: () => import('../views/Analysis.vue'),
      props: true,
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('../views/History.vue'),
    },
    {
      path: '/alerts',
      name: 'alerts',
      component: () => import('../views/Alerts.vue'),
    },
  ],
})

export default router
