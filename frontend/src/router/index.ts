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
    component: () => import('@/views/DesignView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/orders',
    name: 'orders',
    component: () => import('@/views/OrdersView.vue'),
    meta: { requiresAuth: true }
  },
  // ============ 工作室端 ============
  {
    path: '/studio',
    name: 'studio',
    component: () => import('@/views/studio/StudioOrdersView.vue'),
    meta: { requiresAuth: true, role: 'studio' }
  },
  {
    path: '/studio/orders/:orderId',
    name: 'studio-order-detail',
    component: () => import('@/views/studio/StudioOrderDetailView.vue'),
    meta: { requiresAuth: true, role: 'studio' }
  },
  // ============ 管理后台 ============
  {
    path: '/admin',
    name: 'admin',
    component: () => import('@/views/admin/AdminDashboardView.vue'),
    meta: { requiresAuth: true, role: 'admin' }
  },
  {
    path: '/admin/studios',
    name: 'admin-studios',
    component: () => import('@/views/admin/AdminStudiosView.vue'),
    meta: { requiresAuth: true, role: 'admin' }
  },
  {
    path: '/admin/orders',
    name: 'admin-orders',
    component: () => import('@/views/admin/AdminOrdersView.vue'),
    meta: { requiresAuth: true, role: 'admin' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局路由守卫：登录校验 + 角色权限
router.beforeEach((to, _from, next) => {
  const role = localStorage.getItem('role') || ''

  // 需要登录但未登录（role 为空表示未登录）→ 跳转登录页
  if (to.meta.requiresAuth && !role) {
    next({ name: 'login', query: { redirect: to.fullPath } })
    return
  }

  // 角色不匹配 → 跳转到对应角色首页
  if (to.meta.role && to.meta.role !== role) {
    if (role === 'admin') next({ name: 'admin' })
    else if (role === 'studio') next({ name: 'studio' })
    else next({ name: 'home' })
    return
  }

  next()
})

export default router
