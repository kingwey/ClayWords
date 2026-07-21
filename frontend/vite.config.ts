import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      // 管理后台指标接口（后端暴露在 /metrics，不在 /api 前缀下）
      '/metrics': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
