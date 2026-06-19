<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="title">陶语</h1>
      <p class="subtitle">AI 陶瓷定制平台</p>

      <el-form @submit.prevent="handleLogin">
        <el-form-item>
          <el-input
            v-model="phone"
            placeholder="手机号"
            size="large"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="code"
            placeholder="验证码"
            size="large"
          >
            <template #append>
              <el-button @click="sendCode" :disabled="countdown > 0">
                {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
              </el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" native-type="submit" :loading="loading" style="width: 100%">
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="demo-accounts">
        <p class="demo-title">演示账号快速登录</p>
        <div class="demo-buttons">
          <el-button @click="quickLogin('user')">演示用户 A</el-button>
          <el-button @click="quickLogin('studio')">工作室主</el-button>
          <el-button @click="quickLogin('admin')">平台管理员</el-button>
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
    await axios.post('/api/v1/auth/login', { phone: phone.value, code: code.value })
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
    await axios.post('/api/v1/auth/login', { phone: phone.value, code: code.value })
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
  background: linear-gradient(135deg, var(--color-background) 0%, var(--color-surface) 100%);
}

.login-card {
  width: 100%;
  max-width: 400px;
  padding: var(--spacing-8);
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
}

.title {
  font-family: var(--font-family-display);
  font-size: var(--font-size-3xl);
  text-align: center;
  color: var(--color-text-primary);
}

.subtitle {
  text-align: center;
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-6);
}

.demo-accounts {
  margin-top: var(--spacing-6);
  padding-top: var(--spacing-6);
  border-top: 1px solid var(--color-border);
}

.demo-title {
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-4);
}

.demo-buttons {
  display: flex;
  gap: var(--spacing-2);
  justify-content: center;
}
</style>
