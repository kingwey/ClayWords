import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { useAuthStore } from '@/stores/auth'

const client = axios.create({
  baseURL: '/',
  timeout: 30000,
  withCredentials: true  // 让浏览器自动携带 HttpOnly cookie
})

// Response interceptor - 401 自动刷新 token
client.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config

    // 401 且未重试过 → 尝试刷新 token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        // 调用 refresh 端点（cookie 自动携带 refresh_token）
        await axios.post('/api/v1/auth/refresh', {}, { withCredentials: true })
        // 刷新成功，重试原请求
        return client(originalRequest)
      } catch (refreshError) {
        // refresh 也失败 → 清除登录态，跳转登录页
        const auth = useAuthStore()
        auth.clearAuth()
        router.push('/login')
        return Promise.reject(refreshError)
      }
    }

    ElMessage.error(error.response?.data?.detail || '请求失败')
    return Promise.reject(error)
  }
)

export default client
