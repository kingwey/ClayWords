<template>
  <div class="dispatch-panel-root">
    <!-- 派单可视化弹窗 -->
    <el-dialog
      :model-value="visible"
      title=""
      width="680px"
      class="dispatch-dialog"
      :close-on-click-modal="false"
      @update:model-value="emit('update:visible', $event)"
    >
      <div class="dispatch-body">
        <div class="dispatch-hero">
          <div class="hero-left">
            <div class="hero-badge">智能派单</div>
            <h3>正在为您匹配最合适的工作室</h3>
            <p>综合工艺匹配度、产能负载、地理位置距离与用户评分四维加权，自动推荐最合适的承接方。</p>
          </div>
          <div class="hero-icon">
            <svg viewBox="0 0 64 64" fill="none">
              <circle cx="32" cy="32" r="28" fill="rgba(201,123,90,0.12)" />
              <circle cx="32" cy="32" r="20" fill="rgba(201,123,90,0.2)" />
              <circle cx="32" cy="32" r="12" fill="#c97b5a" />
              <circle cx="32" cy="32" r="4" fill="#fffdf9" />
            </svg>
          </div>
        </div>
        <DispatchVisualization :studios="studios" />
      </div>
      <template #footer>
        <div class="dispatch-footer">
          <el-button @click="emit('update:visible', false)">稍后查看</el-button>
          <el-button type="primary" @click="emit('confirm')">
            <span>确认派单至 {{ topStudioName }}</span>
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- P8.4.3 · 工作室接单 Toast -->
    <transition name="accept-toast">
      <div v-if="studioAccepted" class="studio-accept-toast" @click="emit('update:studioAccepted', false)">
        <div class="accept-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">
            <path d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <div class="accept-body">
          <div class="accept-title">师傅已接单</div>
          <div class="accept-sub">{{ acceptedStudioName }} · 已开始排窑</div>
        </div>
        <div class="accept-pulse"></div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import DispatchVisualization from './DispatchVisualization.vue'
import type { Studio } from '@/types/design'

defineProps<{
  visible: boolean
  studios: Studio[]
  topStudioName: string
  studioAccepted: boolean
  acceptedStudioName: string
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'update:studioAccepted', value: boolean): void
  (e: 'confirm'): void
}>()
</script>

<style scoped>
/* ========= Dialog 样式 ========= */
:deep(.dispatch-dialog .el-dialog) {
  border-radius: var(--radius-2xl);
  overflow: hidden;
  padding: 0;
}
:deep(.dispatch-dialog .el-dialog__header) {
  display: none;
}
:deep(.dispatch-dialog .el-dialog__body) {
  padding: 0;
}
.dispatch-body {
  padding: 32px;
}
.dispatch-hero {
  display: flex;
  gap: 24px;
  align-items: flex-start;
  margin-bottom: 24px;
  padding: 20px;
  background: linear-gradient(135deg, rgba(201,123,90,0.08) 0%, rgba(45,74,72,0.04) 100%);
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-border-light);
}
.hero-badge {
  display: inline-block;
  padding: 4px 12px;
  background: var(--color-accent);
  color: #fff;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 2px;
  margin-bottom: 10px;
  font-family: var(--font-family-mono);
}
.hero-left h3 {
  font-size: 18px;
  font-family: var(--font-family-display);
  color: var(--color-text-primary);
  margin: 0 0 8px;
  letter-spacing: 1px;
}
.hero-left p {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.8;
  margin: 0;
}
.hero-icon svg {
  width: 80px;
  height: 80px;
}
.dispatch-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--color-border-light);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
.dispatch-footer .el-button {
  border-radius: var(--radius-full) !important;
  padding: 10px 22px !important;
}

/* ============================================================
   P8.4.3 · 工作室接单 Toast
   ============================================================ */
.studio-accept-toast {
  position: fixed;
  bottom: 32px;
  right: 32px;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 22px 16px 18px;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  border-radius: var(--radius-xl);
  color: #fff;
  box-shadow: var(--shadow-xl), 0 0 0 1px rgba(212, 165, 116, 0.4);
  z-index: var(--z-toast);
  cursor: pointer;
  min-width: 280px;
  overflow: hidden;
}
.accept-icon {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--color-secondary);
  color: var(--color-primary-dark);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.accept-icon svg { width: 22px; height: 22px; }
.accept-body { flex: 1; }
.accept-title {
  font-family: var(--font-family-display);
  font-size: var(--font-size-lg);
  font-weight: 700;
  letter-spacing: 3px;
  margin-bottom: 2px;
}
.accept-sub {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-xs);
  color: rgba(245, 240, 232, 0.8);
  letter-spacing: 1px;
}
.accept-pulse {
  position: absolute;
  inset: -2px;
  border-radius: var(--radius-xl);
  border: 2px solid rgba(212, 165, 116, 0.7);
  animation: acceptPulse 1.6s ease-out infinite;
  pointer-events: none;
}
@keyframes acceptPulse {
  0% { transform: scale(1); opacity: 0.8; }
  70% { transform: scale(1.04); opacity: 0; }
  100% { transform: scale(1.04); opacity: 0; }
}
.accept-toast-enter-active {
  animation: acceptIn 0.5s var(--easing-spring) both;
}
.accept-toast-leave-active {
  animation: acceptIn 0.3s var(--easing-exit) reverse both;
}
@keyframes acceptIn {
  0% {
    opacity: 0;
    transform: translateX(40px) translateY(10px) scale(0.92);
  }
  100% {
    opacity: 1;
    transform: translateX(0) translateY(0) scale(1);
  }
}
</style>
