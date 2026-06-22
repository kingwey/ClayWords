import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { LoginResponse } from '@/types'

type Role = 'user' | 'studio' | 'admin' | ''

/**
 * 认证状态管理
 * - token 与 role 持久化到 localStorage
 * - 路由守卫与导航依据 role 做权限区分
 */
export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string>(localStorage.getItem('access_token') || '')
  const refreshToken = ref<string>(localStorage.getItem('refresh_token') || '')
  const role = ref<Role>((localStorage.getItem('role') as Role) || '')

  const isAuthenticated = computed(() => !!accessToken.value)
  const isStudio = computed(() => role.value === 'studio')
  const isAdmin = computed(() => role.value === 'admin')

  function setAuth(data: LoginResponse) {
    accessToken.value = data.access_token
    refreshToken.value = data.refresh_token
    role.value = data.role
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    localStorage.setItem('role', data.role)
  }

  function clearAuth() {
    accessToken.value = ''
    refreshToken.value = ''
    role.value = ''
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('role')
  }

  /** 登录后默认跳转路径 */
  function defaultRoute(): string {
    if (role.value === 'admin') return '/admin'
    if (role.value === 'studio') return '/studio'
    return '/'
  }

  return {
    accessToken,
    refreshToken,
    role,
    isAuthenticated,
    isStudio,
    isAdmin,
    setAuth,
    clearAuth,
    defaultRoute
  }
})
