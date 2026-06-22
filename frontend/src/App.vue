<template>
  <div id="app" class="app-root">
    <!-- 顶部导航（登录页隐藏） -->
    <nav class="app-nav" v-if="showNav">
      <div class="nav-inner">
        <router-link to="/" class="logo">
          <span class="logo-seal">陶</span>
          <span class="logo-text">陶语 <em>ClayWords</em></span>
        </router-link>
        <div class="nav-links">
          <router-link to="/" exact>
            <span class="nav-zh">首页</span>
          </router-link>
          <router-link to="/design">
            <span class="nav-zh">开始设计</span>
          </router-link>
          <router-link to="/orders">
            <span class="nav-zh">我的订单</span>
          </router-link>
          <router-link to="/login" class="nav-cta">
            <span class="nav-zh">登录</span>
          </router-link>
        </div>
      </div>
    </nav>

    <!-- 路由内容 -->
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

// 用户端全局导航仅用于 C 端页面（首页/设计/订单等）。
// 登录页、工作室端（/studio*）、管理后台（/admin*）都有各自的导航壳，
// 不应叠加这条 C 端导航，否则顶部会出现对当前角色无意义的链接。
const showNav = computed(() => {
  const p = route.path
  if (p === '/login') return false
  if (p.startsWith('/studio')) return false
  if (p.startsWith('/admin')) return false
  return true
})
</script>

<style>
/* ======= 全局页面过渡 ======= */
.page-enter-active,
.page-leave-active {
  transition: opacity var(--transition-normal), transform var(--transition-normal);
}
.page-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ======= 顶部导航栏 ======= */
.app-nav {
  position: sticky;
  top: 0;
  z-index: var(--z-modal);
  background: rgba(250, 246, 240, 0.85);
  backdrop-filter: blur(12px) saturate(1.1);
  -webkit-backdrop-filter: blur(12px) saturate(1.1);
  border-bottom: 1px solid var(--color-border-light);
}

.nav-inner {
  max-width: var(--container-xl);
  margin: 0 auto;
  padding: var(--spacing-4) var(--spacing-8);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  text-decoration: none;
  transition: transform var(--transition-fast);
}
.logo:hover { transform: translateY(-1px); }

.logo-seal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  color: var(--glaze-white);
  font-family: var(--font-family-display);
  font-size: var(--font-size-lg);
  font-weight: 700;
  border-radius: var(--radius-md);
  letter-spacing: 0;
  box-shadow: 0 2px 8px rgba(45, 74, 72, 0.3);
}

.logo-text {
  font-family: var(--font-family-display);
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-primary);
  letter-spacing: 3px;
}

.logo-text em {
  font-style: normal;
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  margin-left: var(--spacing-2);
  letter-spacing: 1px;
  font-weight: 400;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: var(--spacing-8);
}

.nav-links a {
  display: inline-block;
  padding: var(--spacing-2) var(--spacing-3);
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  text-decoration: none;
  border-radius: var(--radius-full);
  transition: all var(--transition-fast);
  font-family: var(--font-family-base);
}

.nav-links a:hover {
  color: var(--color-accent);
  background: rgba(201, 123, 90, 0.06);
}

.nav-links a.router-link-active {
  color: var(--color-primary);
  background: rgba(45, 74, 72, 0.06);
}

.nav-links a.nav-cta {
  background: var(--color-primary);
  color: #fff;
  padding: var(--spacing-2) var(--spacing-5);
  border-radius: var(--radius-full);
}
.nav-links a.nav-cta:hover {
  background: var(--color-primary-dark);
  color: #fff;
}

/* ======= 主内容区 ======= */
.app-main {
  min-height: calc(100vh - 72px);
}

/* ======= Element Plus 主题覆盖 ======= */
.el-button--primary {
  --el-button-bg-color: var(--color-primary);
  --el-button-border-color: var(--color-primary);
  --el-button-hover-bg-color: var(--color-primary-dark);
  --el-button-hover-border-color: var(--color-primary-dark);
  --el-button-active-bg-color: var(--color-primary-dark);
  --el-button-active-border-color: var(--color-primary-dark);
  font-weight: 500;
  border-radius: var(--radius-full) !important;
  padding: 10px 22px !important;
  height: auto !important;
}

.el-button {
  border-radius: var(--radius-full) !important;
  padding: 10px 18px !important;
  height: auto !important;
  transition: all var(--transition-fast) !important;
}

.el-button:hover:not(.el-button--primary):not(.is-plain) {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.el-input__wrapper {
  border-radius: var(--radius-lg) !important;
  box-shadow: 0 0 0 1px var(--color-border) inset !important;
  padding: 10px 16px !important;
  background: var(--color-surface) !important;
  transition: all var(--transition-fast) !important;
}
.el-input__wrapper:hover {
  box-shadow: 0 0 0 1px var(--color-primary-light) inset !important;
}
.el-input.is-focus .el-input__wrapper {
  box-shadow: 0 0 0 1px var(--color-primary) inset !important;
}

.el-textarea__inner {
  border-radius: var(--radius-lg) !important;
  border: 1px solid var(--color-border) !important;
  transition: border-color var(--transition-fast) !important;
  font-family: var(--font-family-base) !important;
  padding: 12px 16px !important;
}
.el-textarea__inner:focus {
  border-color: var(--color-primary) !important;
}

.el-tag {
  border-radius: var(--radius-full) !important;
  padding: 2px 12px !important;
  height: 24px !important;
  line-height: 20px !important;
  font-size: var(--font-size-xs) !important;
  border: 1px solid transparent !important;
  font-weight: 500;
}
.el-tag--success {
  --el-tag-bg-color: rgba(91, 138, 114, 0.12);
  --el-tag-border-color: rgba(91, 138, 114, 0.3);
  --el-tag-text-color: var(--color-success);
}
.el-tag--warning {
  --el-tag-bg-color: rgba(201, 123, 90, 0.14);
  --el-tag-border-color: rgba(201, 123, 90, 0.3);
  --el-tag-text-color: var(--color-accent);
}
.el-tag--danger {
  --el-tag-bg-color: rgba(199, 91, 91, 0.12);
  --el-tag-border-color: rgba(199, 91, 91, 0.3);
  --el-tag-text-color: var(--color-error);
}
.el-tag--info {
  --el-tag-bg-color: rgba(45, 74, 72, 0.08);
  --el-tag-border-color: rgba(45, 74, 72, 0.2);
  --el-tag-text-color: var(--color-primary);
}

.el-dialog {
  border-radius: var(--radius-2xl) !important;
  overflow: hidden;
  box-shadow: var(--shadow-2xl) !important;
}
.el-dialog__header {
  padding: var(--spacing-6) var(--spacing-8) var(--spacing-4) !important;
  margin: 0 !important;
  border-bottom: 1px solid var(--color-border-light);
}
.el-dialog__body {
  padding: var(--spacing-6) var(--spacing-8) !important;
}
.el-dialog__footer {
  padding: var(--spacing-4) var(--spacing-8) var(--spacing-6) !important;
  border-top: 1px solid var(--color-border-light);
}
.el-dialog__title {
  font-family: var(--font-family-display) !important;
  color: var(--color-primary) !important;
  font-size: var(--font-size-2xl) !important;
  font-weight: 700 !important;
  letter-spacing: 2px;
}

.el-radio-button__inner {
  border-radius: var(--radius-full) !important;
  padding: 8px 20px !important;
  border: 1px solid var(--color-border) !important;
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.el-radio-button.is-active .el-radio-button__inner {
  background: var(--color-primary);
  border-color: var(--color-primary) !important;
  color: #fff;
}

.el-skeleton__item {
  background: linear-gradient(
    90deg,
    var(--color-bg2) 25%,
    var(--color-border-light) 37%,
    var(--color-bg2) 63%
  ) !important;
  background-size: 400% 100% !important;
  animation: glazeFlow 1.6s ease-in-out infinite !important;
}

.el-card {
  border-radius: var(--radius-2xl) !important;
  border: 1px solid var(--color-border-light) !important;
  background: var(--color-surface) !important;
  box-shadow: var(--shadow-sm) !important;
}
</style>

