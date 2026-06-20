<template>
  <div class="login-page">
    <div class="login-particles">
      <div v-for="i in 15" :key="i" class="particle" :style="getParticleStyle(i)"></div>
    </div>
    <div class="login-card">
      <div class="card-glow"></div>
      <div class="title-wrapper">
        <h1 class="title">
          <span class="char" style="--delay: 0">陶</span><span class="char" style="--delay: 1">语</span>
        </h1>
        <div class="title-underline"></div>
      </div>
      <p class="subtitle">AI 陶瓷定制平台</p>

      <el-form @submit.prevent="handleLogin" class="login-form">
        <el-form-item>
          <el-input
            v-model="phone"
            placeholder="手机号"
            size="large"
            class="input-field"
          >
            <template #prefix>
              <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
              </svg>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="code"
            placeholder="验证码"
            size="large"
            class="input-field"
          >
            <template #prefix>
              <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
            </template>
            <template #append>
              <el-button @click="sendCode" :disabled="countdown > 0" class="code-btn">
                {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
              </el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" native-type="submit" :loading="loading" class="submit-btn">
            <span v-if="!loading">登 录</span>
            <span v-else>登录中...</span>
          </el-button>
        </el-form-item>
      </el-form>

      <div class="demo-accounts">
        <p class="demo-title">演示账号快速登录</p>
        <div class="demo-buttons">
          <el-button @click="quickLogin('user')" class="demo-btn">
            <svg class="demo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
            <span>演示用户</span>
          </el-button>
          <el-button @click="quickLogin('studio')" class="demo-btn">
            <svg class="demo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
              <polyline points="9 22 9 12 15 12 15 22"/>
            </svg>
            <span>工作室主</span>
          </el-button>
          <el-button @click="quickLogin('admin')" class="demo-btn">
            <svg class="demo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
            <span>管理员</span>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from '@/api/client'

const router = useRouter()
const phone = ref('')
const code = ref('')
const loading = ref(false)
const countdown = ref(0)

function getParticleStyle(_i: number) {
  const size = Math.random() * 6 + 3
  const left = Math.random() * 100
  const delay = Math.random() * 5
  const duration = Math.random() * 15 + 10
  const opacity = Math.random() * 0.4 + 0.1
  return {
    width: `${size}px`,
    height: `${size}px`,
    left: `${left}%`,
    animationDelay: `${delay}s`,
    animationDuration: `${duration}s`,
    opacity
  }
}

async function sendCode() {
  if (!phone.value) {
    ElMessage.warning('请输入手机号')
    return
  }
  countdown.value = 60
  const timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) clearInterval(timer)
  }, 1000)
  ElMessage.success('验证码已发送')
}

async function handleLogin() {
  if (!phone.value || !code.value) {
    ElMessage.warning('请输入手机号和验证码')
    return
  }
  loading.value = true
  try {
    const { data } = await axios.post('/api/v1/auth/login', { phone: phone.value, code: code.value })
    // 保存 JWT，下游所有鉴权接口都依赖这两条
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    ElMessage.success('登录成功')
    router.push('/design')
  } catch {
    ElMessage.error('登录失败')
  } finally {
    loading.value = false
  }
}

async function quickLogin(type: string) {
  loading.value = true
  try {
    const phoneMap: Record<string, string> = {
      user: '13800000001',
      studio: '13800000002',
      admin: '13800000003'
    }
    phone.value = phoneMap[type]
    code.value = '123456'
    const { data } = await axios.post('/api/v1/auth/login', { phone: phone.value, code: code.value })
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    ElMessage.success('登录成功')
    router.push('/design')
  } catch {
    ElMessage.error('登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-background) 0%, var(--color-bg2) 100%);
  position: relative;
  overflow: hidden;
}

.login-particles {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.particle {
  position: absolute;
  bottom: -10px;
  background: radial-gradient(circle, var(--color-primary) 0%, transparent 70%);
  border-radius: 50%;
  animation: particle-rise linear infinite;
}

@keyframes particle-rise {
  0% {
    transform: translateY(0) scale(1);
    opacity: 0;
  }
  10% {
    opacity: var(--opacity, 0.3);
  }
  90% {
    opacity: var(--opacity, 0.3);
  }
  100% {
    transform: translateY(-100vh) scale(0.3);
    opacity: 0;
  }
}

.login-card {
  width: 100%;
  max-width: 420px;
  padding: var(--spacing-10);
  background: var(--color-surface);
  border-radius: var(--radius-2xl);
  box-shadow: 0 25px 50px rgba(42, 36, 32, 0.12);
  position: relative;
  z-index: 1;
  animation: card-enter 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

@keyframes card-enter {
  from {
    opacity: 0;
    transform: translateY(40px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.card-glow {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(201, 123, 90, 0.1) 0%, transparent 50%);
  pointer-events: none;
  animation: glow-pulse 4s ease-in-out infinite;
}

@keyframes glow-pulse {
  0%, 100% { opacity: 0.5; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.05); }
}

.title-wrapper {
  text-align: center;
  margin-bottom: var(--spacing-2);
}

.title {
  font-size: 48px;
  font-weight: 800;
  text-align: center;
  color: var(--color-text-primary);
  letter-spacing: 6px;
  margin-bottom: var(--spacing-2);
}

.char {
  display: inline-block;
  animation: char-enter 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  animation-delay: calc(var(--delay) * 0.15s);
  opacity: 0;
  transform: translateY(20px) rotate(-10deg);
}

@keyframes char-enter {
  to {
    opacity: 1;
    transform: translateY(0) rotate(0deg);
  }
}

.title-underline {
  width: 60px;
  height: 3px;
  background: linear-gradient(90deg, var(--color-primary), var(--color-accent));
  margin: 0 auto;
  border-radius: 2px;
  animation: underline-expand 0.5s ease-out 0.4s forwards;
  transform-origin: center;
  transform: scaleX(0);
}

@keyframes underline-expand {
  to { transform: scaleX(1); }
}

.subtitle {
  text-align: center;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-8);
  animation: fade-in 0.5s ease-out 0.3s backwards;
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* Form styling */
.login-form {
  animation: form-enter 0.5s ease-out 0.4s backwards;
}

@keyframes form-enter {
  from {
    opacity: 0;
    transform: translateY(15px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.login-card :deep(.el-form-item) {
  margin-bottom: var(--spacing-5);
}

.login-card :deep(.el-input__wrapper) {
  padding: var(--spacing-3) var(--spacing-4);
  padding-left: var(--spacing-3);
  border-radius: var(--radius-lg);
  box-shadow: none;
  border: 2px solid var(--color-border);
  transition: all 0.3s ease;
  background: var(--color-bg2);
}

.login-card :deep(.el-input__wrapper:hover),
.login-card :deep(.el-input__wrapper.is-focus) {
  border-color: var(--color-primary);
  background: var(--color-surface);
  box-shadow: 0 0 0 3px rgba(201, 123, 90, 0.1);
}

.login-card :deep(.el-input__inner) {
  font-size: var(--font-size-base);
}

.login-card :deep(.el-input__inner::placeholder) {
  color: var(--color-text-tertiary);
}

.input-icon {
  width: 16px;
  height: 16px;
  color: var(--color-text-secondary);
}

.code-btn {
  background: transparent !important;
  border: none !important;
  color: var(--color-primary) !important;
  font-weight: 600;
  padding: 0 var(--spacing-3) !important;
  transition: all 0.3s ease;
}

.code-btn:hover:not(:disabled) {
  color: var(--color-accent) !important;
}

.code-btn:disabled {
  color: var(--color-text-tertiary) !important;
}

.submit-btn {
  width: 100%;
  background: linear-gradient(135deg, var(--color-accent) 0%, #1d3635 100%) !important;
  border: none !important;
  padding: 14px 24px;
  font-size: 16px;
  font-weight: 600;
  border-radius: var(--radius-lg) !important;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
  position: relative;
  overflow: hidden;
}

.submit-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
  transition: left 0.5s;
}

.submit-btn:hover::before {
  left: 100%;
}

.submit-btn:hover {
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 8px 25px rgba(45, 74, 72, 0.3) !important;
}

.submit-btn:active {
  transform: translateY(0) scale(0.98);
}

/* Demo accounts section */
.demo-accounts {
  margin-top: var(--spacing-8);
  padding-top: var(--spacing-6);
  border-top: 1px dashed var(--color-border);
  animation: demo-enter 0.5s ease-out 0.6s backwards;
}

@keyframes demo-enter {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.demo-title {
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 2px;
  margin-bottom: var(--spacing-4);
}

.demo-buttons {
  display: flex;
  gap: var(--spacing-2);
  justify-content: center;
}

.demo-btn {
  display: flex !important;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-3) var(--spacing-4) !important;
  font-size: var(--font-size-sm);
  border-radius: var(--radius-lg) !important;
  background: var(--color-bg2) !important;
  border: 2px solid transparent !important;
  color: var(--color-text-primary);
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.demo-btn:hover {
  background: var(--color-surface) !important;
  border-color: var(--color-primary) !important;
  color: var(--color-primary);
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(42, 36, 32, 0.1);
}

.demo-icon {
  width: 24px;
  height: 24px;
  transition: transform 0.3s ease;
}

.demo-btn:hover .demo-icon {
  transform: scale(1.1);
}
</style>
