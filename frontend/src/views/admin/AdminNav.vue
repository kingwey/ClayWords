<template>
  <nav class="admin-nav">
    <div class="nav-inner">
      <div class="nav-brand">陶语 · 管理后台</div>
      <div class="nav-links">
        <router-link to="/admin">总览</router-link>
        <router-link to="/admin/studios">工作室</router-link>
        <router-link to="/admin/orders">订单</router-link>
      </div>
      <div class="nav-user">
        <span v-if="auth.displayName" class="user-name">{{ auth.displayName }}</span>
        <el-button text @click="handleLogout" style="color: #fff">退出登录</el-button>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

onMounted(() => {
  auth.fetchUser()
})

async function handleLogout() {
  await auth.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.admin-nav {
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

.nav-user {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-name {
  font-family: monospace;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
}
</style>
