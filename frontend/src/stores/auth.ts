import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/modules'

type Role = 'user' | 'studio' | 'admin' | ''

/**
 * 认证状态管理
 * - token 通过 HttpOnly cookie 传输，JavaScript 无法读取（防 XSS）
 * - role 持久化到 localStorage 用于路由守卫与导航
 * - 用户资料 (脱敏手机号当作昵称) 不持久化, 每次会话首次访问时通过
 *   /api/v1/auth/user 拉取一次，避免 localStorage 暴露 PII
 */
export const useAuthStore = defineStore('auth', () => {
  const role = ref<Role>((localStorage.getItem('role') as Role) || '')
  const userId = ref<string>('')
  const phone = ref<string>('')           // 脱敏: 139****1234
  const studioId = ref<string | null>(null)
  const userLoaded = ref(false)            // 防止反复请求 /auth/user

  // token 在 cookie 中，前端无法直接读取，通过 role 判断登录态
  const isAuthenticated = computed(() => !!role.value)
  const isStudio = computed(() => role.value === 'studio')
  const isAdmin = computed(() => role.value === 'admin')

  /** 显示用昵称: 优先脱敏手机号, 退化到 user_id 前 8 位; 未登录返回空串 */
  const displayName = computed(() => {
    if (phone.value) return phone.value
    if (userId.value) return userId.value.slice(0, 8)
    return ''
  })

  /** 角色中文标签 (用于导航徽标) */
  const roleLabel = computed(() => {
    if (role.value === 'admin') return '管理员'
    if (role.value === 'studio') return '工作室'
    if (role.value === 'user') return '用户'
    return ''
  })

  function setAuth(data: { role: string }) {
    role.value = data.role as Role
    localStorage.setItem('role', data.role)
    // 角色变了 → 强制重拉用户资料
    userLoaded.value = false
  }

  function clearAuth() {
    role.value = ''
    userId.value = ''
    phone.value = ''
    studioId.value = null
    userLoaded.value = false
    localStorage.removeItem('role')
  }

  /** 拉取当前用户资料; 401/网络错误自动 clearAuth 让导航回到未登录 */
  async function fetchUser(force = false) {
    if (!isAuthenticated.value) return
    if (userLoaded.value && !force) return
    try {
      const { data } = await authApi.getCurrentUser()
      userId.value = data.user_id
      phone.value = data.phone || ''
      studioId.value = data.studio_id
      role.value = data.role as Role
      userLoaded.value = true
    } catch {
      // 401 / 网络挂掉 → 视作未登录, 让 UI 显示登录按钮
      clearAuth()
    }
  }

  /** 退出登录: 调后端清 cookie + 清本地 store */
  async function logout() {
    try {
      await authApi.logout()
    } catch {
      // 后端 500/网络挂 也要继续清本地态, 否则用户可能被卡在"假登录"
    }
    clearAuth()
  }

  /** 登录后默认跳转路径 */
  function defaultRoute(): string {
    if (role.value === 'admin') return '/admin'
    if (role.value === 'studio') return '/studio'
    return '/'
  }

  return {
    role,
    userId,
    phone,
    studioId,
    isAuthenticated,
    isStudio,
    isAdmin,
    displayName,
    roleLabel,
    setAuth,
    clearAuth,
    fetchUser,
    logout,
    defaultRoute
  }
})
