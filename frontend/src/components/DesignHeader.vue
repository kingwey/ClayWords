<template>
  <header class="design-header">
    <div class="design-header-inner">
      <div class="header-left">
        <router-link to="/" class="logo-seal" title="返回首页">陶</router-link>
        <div class="header-title">
          <h1>对话式设计台</h1>
          <p>描述你想要的陶瓷，AI 实时生成可烧制方案</p>
        </div>
      </div>
      <div class="header-right">
        <router-link to="/" class="nav-link">首页</router-link>
        <router-link to="/orders" class="nav-link">我的订单</router-link>
        <el-dropdown
          v-if="auth.isAuthenticated"
          trigger="click"
          placement="bottom-end"
          @command="emit('command', $event)"
        >
          <button type="button" class="user-chip" aria-label="用户菜单">
            <span class="avatar">{{ avatarLetter }}</span>
            <span class="user-name">{{ auth.displayName }}</span>
            <span class="caret">▾</span>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-if="auth.isAdmin" command="admin">管理后台</el-dropdown-item>
              <el-dropdown-item v-if="auth.isStudio" command="studio">工作室订单</el-dropdown-item>
              <el-dropdown-item command="orders">我的订单</el-dropdown-item>
              <el-dropdown-item command="profile">个人资料</el-dropdown-item>
              <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

const emit = defineEmits<{ command: [cmd: string] }>()
const auth = useAuthStore()

const avatarLetter = computed(() => {
  if (auth.nickname) return auth.nickname.slice(0, 1).toUpperCase()
  const digits = auth.phone.replace(/\D/g, '')
  if (digits.length > 0) return digits.slice(-1)
  return auth.displayName ? auth.displayName.slice(0, 1).toUpperCase() : '陶'
})
</script>

<style scoped>
.design-header {
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
  flex-shrink: 0;
  z-index: 20;
}
.design-header-inner {
  max-width: 1920px;
  margin: 0 auto;
  padding: 14px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.logo-seal {
  width: 44px;
  height: 44px;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  color: var(--glaze-white);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-family-display);
  font-size: 20px;
  font-weight: 700;
  border-radius: var(--radius-lg);
  box-shadow: 0 4px 12px rgba(45, 74, 72, 0.25);
  text-decoration: none;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}
.logo-seal:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(45, 74, 72, 0.32);
}
.header-title h1 {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-primary);
  font-family: var(--font-family-display);
  margin: 0;
  letter-spacing: 1px;
}
.header-title p {
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin: 2px 0 0;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 24px;
}
.nav-link {
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: 14px;
  transition: color 0.2s;
}
.nav-link:hover { color: var(--color-primary); }
.user-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 5px 12px 5px 5px;
  background: rgba(45, 74, 72, 0.06);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-full, 999px);
  cursor: pointer;
  font-family: inherit;
  outline: none;
  transition: all 0.2s;
}
.user-chip:hover { background: rgba(45, 74, 72, 0.1); border-color: var(--color-primary-light, #6b8a72); }
.user-chip:focus-visible { box-shadow: 0 0 0 3px rgba(45, 74, 72, 0.15); }
.user-chip .avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  font-family: var(--font-family-mono, monospace);
}
.user-chip .user-name {
  font-size: 13px;
  color: var(--color-text-secondary);
  font-family: var(--font-family-mono, monospace);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.user-chip .caret { font-size: 10px; color: var(--color-text-tertiary); }
</style>
