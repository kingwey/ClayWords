<template>
  <nav class="studio-nav">
    <div class="nav-inner">
      <div class="nav-brand">陶语 · 工作室工作台</div>
      <div class="nav-links">
        <router-link to="/studio">订单</router-link>
      </div>
      <el-button text @click="handleLogout">退出登录</el-button>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

function handleLogout() {
  auth.clearAuth()
  router.push('/login')
}
</script>

<style scoped>
.studio-nav {
  background: var(--color-primary, #2c3e2d);
  color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.nav-inner {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 24px;
  height: 56px;
  display: flex;
  align-items: center;
  gap: 32px;
}

.nav-brand {
  font-weight: 600;
  font-size: 16px;
}

.nav-links {
  display: flex;
  gap: 20px;
  flex: 1;
}

.nav-links a {
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  font-size: 14px;
  padding: 4px 0;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.nav-links a:hover {
  color: #fff;
}

.nav-links a.router-link-exact-active {
  color: #fff;
  border-bottom-color: var(--color-accent, #d98e5a);
}
</style>
