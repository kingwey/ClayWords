import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

type Role = 'user' | 'studio' | 'admin' | ''

/**
 * 认证状态管理
 * - token 通过 HttpOnly cookie 传输，JavaScript 无法读取（防 XSS）
 * - role 持久化到 localStorage 用于路由守卫与导航
 */
export const useAuthStore = defineStore('auth', () => {
  const role = ref<Role>((localStorage.getItem('role') as Role) || '')

  // token 在 cookie 中，前端无法直接读取，通过 role 判断登录态
  const isAuthenticated = computed(() => !!role.value)
  const isStudio = computed(() => role.value === 'studio')
  const isAdmin = computed(() => role.value === 'admin')

  function setAuth(data: { role: string }) {
    role.value = data.role as Role
    localStorage.setItem('role', data.role)
  }

  function clearAuth() {
    role.value = ''
    localStorage.removeItem('role')
  }

  /** 登录后默认跳转路径 */
  function defaultRoute(): string {
    if (role.value === 'admin') return '/admin'
    if (role.value === 'studio') return '/studio'
    return '/'
  }

  return {
    role,
    isAuthenticated,
    isStudio,
    isAdmin,
    setAuth,
    clearAuth,
    defaultRoute
  }
})
