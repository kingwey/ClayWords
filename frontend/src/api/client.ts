import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const client = axios.create({
  baseURL: '/',
  timeout: 30000
})

// Request interceptor
client.interceptors.request.use(
  config => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

// Response interceptor
client.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      router.push('/login')
    }
    ElMessage.error(error.response?.data?.detail || '请求失败')
    return Promise.reject(error)
  }
)

export default client
