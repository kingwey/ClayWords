import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue')
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue')
  },
  {
    path: '/design',
    name: 'design',
    component: () => import('@/views/DesignView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
