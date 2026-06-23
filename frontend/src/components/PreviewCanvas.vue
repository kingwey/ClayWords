<template>
  <aside class="preview-panel">
    <div class="preview-header">
      <h2>3D 预览</h2>
      <div class="preview-subtitle">{{ currentOption?.name || '等待方案' }}</div>
    </div>

    <div class="preview-stage-wrapper">
      <div class="preview-stage" ref="stageEl">
        <!-- 陶瓷 3D 视觉（CSS 旋转） -->
        <div class="ceramic-3d" :style="{ transform: `rotateY(${rotateY}deg) rotateX(${rotateX}deg)` }">
          <div class="ceramic-body" :style="ceramicBodyStyle">
            <div class="ceramic-gloss"></div>
            <div class="ceramic-shadow"></div>
          </div>
          <div class="ceramic-base"></div>
        </div>

        <!-- 光晕与底座 -->
        <div class="stage-floor"></div>
        <div class="stage-glow" :style="{ background: `radial-gradient(ellipse at center, ${currentOption?.colors?.light || 'rgba(201,123,90,0.12)'} 0%, transparent 70%)` }"></div>
      </div>

      <!-- 手动旋转控制 -->
      <div class="rotate-controls">
        <button class="rotate-btn" @click="emit('rotate', -30)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 12a9 9 0 1 0 9-9" />
            <path d="M3 12l4-4M3 12l4 4" />
          </svg>
        </button>
        <div class="rotate-info">
          <span>Y: {{ Math.round(rotateY % 360) }}°</span>
          <span>X: {{ Math.round(rotateX) }}°</span>
        </div>
        <button class="rotate-btn" @click="emit('rotate', 30)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 1 1-9-9" />
            <path d="M21 12l-4-4M21 12l-4 4" />
          </svg>
        </button>
        <button class="auto-rotate-btn" :class="{ active: autoRotate }" @click="emit('toggle-auto-rotate')">
          {{ autoRotate ? '停止旋转' : '自动旋转' }}
        </button>
        <button class="auto-rotate-btn" @click="emit('reset-view')">
          重置视角
        </button>
      </div>
    </div>

    <!-- 釉色选择 -->
    <div class="glaze-selector">
      <div class="selector-label">
        <span class="label-title">釉色</span>
        <span class="label-sub">点击切换釉色，实时更新</span>
      </div>
      <div class="glaze-options">
        <button
          v-for="g in glazeOptions"
          :key="g.name"
          :class="['glaze-btn', { active: currentGlaze === g.name }]"
          :style="{ background: g.bg }"
          :title="g.name"
          @click="emit('change-glaze', g.name)"
        >
          <span class="glaze-name">{{ g.name }}</span>
        </button>
      </div>
    </div>

    <!-- P8.4.1 · 方案版本树 -->
    <div class="version-tree" v-if="currentOption">
      <button class="version-toggle" @click="emit('update:showVersionTree', !showVersionTree)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;">
          <path d="M6 3v12M18 9v12M6 15a3 3 0 0 0 3 3h6a3 3 0 0 0 3-3" />
          <circle cx="6" cy="3" r="2"/>
          <circle cx="18" cy="9" r="2"/>
          <circle cx="18" cy="21" r="2"/>
        </svg>
        <span>版本树（{{ versions.length }}）</span>
        <span class="toggle-arrow" :class="{ open: showVersionTree }">▾</span>
      </button>
      <transition name="vt-slide">
        <div v-if="showVersionTree" class="version-list">
          <div
            v-for="v in versions.slice().reverse()"
            :key="v.versionNo + '-' + v.createdAt"
            class="version-node"
            @click="emit('rollback', v)"
          >
            <div class="vn-dot" :style="{ background: v.colors.mid }"></div>
            <div class="vn-line"></div>
            <div class="vn-card">
              <div class="vn-head">
                <span class="vn-no">v{{ v.versionNo }}</span>
                <span class="vn-glaze">{{ v.glaze }}</span>
              </div>
              <div class="vn-label">{{ v.label }}</div>
              <div class="vn-meta">{{ new Date(v.createdAt).toLocaleTimeString() }} · 点击回滚</div>
            </div>
          </div>
          <div v-if="versions.length === 0" class="vn-empty">
            选中方案后开始记录版本…
          </div>
        </div>
      </transition>
    </div>

    <!-- 方案摘要 -->
    <div class="preview-summary" v-if="currentOption">
      <h4>工艺参数</h4>
      <div class="summary-grid">
        <div class="summary-item" v-for="(v, k) in craftParams" :key="k">
          <span class="s-label">{{ k }}</span>
          <span class="s-value">{{ v }}</span>
        </div>
      </div>

      <button class="btn btn-primary summary-cta" @click="emit('order', currentOption)">
        <span>确认方案 · 下单烧制</span>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M5 12h14M13 5l7 7-7 7" />
        </svg>
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { Option, GlazeOption } from '@/types/design'
import type { DesignVersion } from '@/composables/useDesignVersions'

defineProps<{
  currentOption: Option | null
  rotateX: number
  rotateY: number
  autoRotate: boolean
  ceramicBodyStyle: string
  glazeOptions: GlazeOption[]
  currentGlaze: string
  versions: DesignVersion[]
  showVersionTree: boolean
  craftParams: Record<string, string | number>
}>()

const emit = defineEmits<{
  (e: 'rotate', delta: number): void
  (e: 'toggle-auto-rotate'): void
  (e: 'reset-view'): void
  (e: 'change-glaze', name: string): void
  (e: 'order', opt: Option): void
  (e: 'rollback', v: DesignVersion): void
  (e: 'update:showVersionTree', value: boolean): void
}>()

// 3D 舞台 DOM：交给父组件的 usePreviewRotation 绑定拖拽事件
const stageEl = ref<HTMLElement | null>(null)
defineExpose({ stageEl })
</script>

<style scoped>
/* ========= 3D 预览面板 ========= */
.preview-panel {
  border-left: 1px solid var(--color-border);
  background: var(--color-surface);
  display: flex;
  flex-direction: column;
  height: calc(100vh - 72px);
}

.preview-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border-light);
}
.preview-header h2 {
  font-size: 18px;
  font-family: var(--font-family-display);
  color: var(--color-text-primary);
  margin: 0 0 4px;
  letter-spacing: 1.5px;
  font-weight: 700;
}
.preview-subtitle {
  font-size: 12px;
  color: var(--color-text-tertiary);
  font-family: var(--font-family-mono);
}

.preview-stage-wrapper {
  padding: 24px;
  border-bottom: 1px solid var(--color-border-light);
}

.preview-stage {
  position: relative;
  width: 100%;
  height: 340px;
  background: radial-gradient(ellipse at 50% 30%, #faf6f0 0%, #ece0d0 100%);
  border-radius: var(--radius-2xl);
  display: flex;
  align-items: center;
  justify-content: center;
  perspective: 1000px;
  overflow: hidden;
  cursor: grab;
  border: 1px solid var(--color-border-light);
}

.preview-stage:active {
  cursor: grabbing;
}

.stage-floor {
  position: absolute;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  width: 80%;
  height: 30px;
  background: radial-gradient(ellipse at center, rgba(42,36,32,0.18) 0%, transparent 70%);
  filter: blur(6px);
}

.stage-glow {
  position: absolute;
  top: 20%;
  left: 50%;
  transform: translateX(-50%);
  width: 70%;
  height: 70%;
  pointer-events: none;
}

.ceramic-3d {
  position: relative;
  transform-style: preserve-3d;
  transition: transform 0.05s linear;
  z-index: 2;
}

.ceramic-body {
  position: relative;
  box-shadow:
    inset -15px -20px 40px rgba(0, 0, 0, 0.12),
    inset 8px 8px 20px rgba(255, 255, 255, 0.4),
    0 20px 40px rgba(42, 36, 32, 0.2);
}

.ceramic-body::before {
  content: '';
  position: absolute;
  top: 10%;
  left: 20%;
  width: 20%;
  height: 40%;
  background: linear-gradient(180deg, rgba(255,255,255,0.5) 0%, transparent 100%);
  border-radius: 50%;
  filter: blur(4px);
}

.ceramic-body::after {
  content: '';
  position: absolute;
  top: 10%;
  left: 50%;
  width: 60%;
  height: 80%;
  background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.2) 50%, transparent 100%);
  transform: translateX(-50%);
}

.ceramic-gloss {
  position: absolute;
  top: 8%;
  left: 15%;
  width: 30%;
  height: 35%;
  background: radial-gradient(ellipse at center, rgba(255,255,255,0.7) 0%, transparent 60%);
  border-radius: 50%;
  filter: blur(2px);
}

.ceramic-shadow {
  position: absolute;
  bottom: -30px;
  left: 50%;
  transform: translateX(-50%);
  width: 80%;
  height: 20px;
  background: radial-gradient(ellipse at center, rgba(42,36,32,0.3) 0%, transparent 70%);
  filter: blur(6px);
}

.ceramic-base {
  position: absolute;
  bottom: -10px;
  left: 50%;
  transform: translateX(-50%);
  width: 60%;
  height: 10px;
  background: rgba(42, 36, 32, 0.15);
  border-radius: 50%;
}

.rotate-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 16px;
  flex-wrap: wrap;
}

.rotate-btn {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.rotate-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.rotate-btn svg {
  width: 16px;
  height: 16px;
}

.rotate-info {
  display: flex;
  gap: 10px;
  font-family: var(--font-family-mono);
  font-size: 11px;
  color: var(--color-text-tertiary);
  padding: 0 6px;
}

.auto-rotate-btn {
  padding: 8px 14px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}
.auto-rotate-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent-dark);
}
.auto-rotate-btn.active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

/* ========= 釉色选择 ========= */
.glaze-selector {
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border-light);
}
.selector-label {
  margin-bottom: 12px;
}
.label-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-right: 8px;
}
.label-sub {
  font-size: 11px;
  color: var(--color-text-tertiary);
  font-family: var(--font-family-mono);
}

.glaze-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.glaze-btn {
  padding: 10px 8px;
  border: 2px solid transparent;
  border-radius: var(--radius-lg);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08), inset 0 1px 2px rgba(255,255,255,0.4);
  position: relative;
}
.glaze-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.12), inset 0 1px 2px rgba(255,255,255,0.4);
}
.glaze-btn.active {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(45, 74, 72, 0.15), 0 4px 12px rgba(0,0,0,0.1);
}
.glaze-btn.active::after {
  content: '✓';
  position: absolute;
  top: 2px;
  right: 4px;
  font-size: 10px;
  color: var(--color-primary);
  font-weight: 700;
}
.glaze-name {
  font-size: 11px;
  color: #2a2420;
  font-family: var(--font-family-display);
  font-weight: 600;
  letter-spacing: 1px;
  text-shadow: 0 1px 2px rgba(255,255,255,0.3);
}

/* ========= 方案摘要 ========= */
.preview-summary {
  padding: 20px 24px 24px;
  flex: 1;
  display: flex;
  flex-direction: column;
}
.preview-summary h4 {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 12px;
  font-family: var(--font-family-display);
  letter-spacing: 1px;
}

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 16px;
}
.summary-item {
  padding: 10px 12px;
  background: var(--color-bg2);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.s-label {
  font-size: 10px;
  color: var(--color-text-tertiary);
  font-family: var(--font-family-mono);
  letter-spacing: 1px;
}
.s-value {
  font-size: 12.5px;
  color: var(--color-text-primary);
  font-weight: 500;
}

.summary-cta {
  margin-top: auto;
  padding: 14px 18px;
  font-size: 14px;
  font-weight: 600;
  border-radius: var(--radius-xl);
}
.summary-cta svg {
  width: 16px;
  height: 16px;
}

/* 摘要 CTA 复用的按钮基样式 */
.btn {
  flex: 1;
  padding: 10px 14px;
  border-radius: var(--radius-full);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-family: inherit;
}
.btn svg {
  width: 14px;
  height: 14px;
}
.btn-primary {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  color: #fff;
  border-color: transparent;
  box-shadow: 0 4px 12px rgba(45, 74, 72, 0.25);
}
.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(45, 74, 72, 0.35);
}

/* ============================================================
   P8.4.1 · 方案版本树
   ============================================================ */
.version-tree {
  margin-top: var(--spacing-4);
  padding: var(--spacing-3) var(--spacing-4);
  background: var(--color-bg-warm);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
}
.version-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: 4px 0;
  background: transparent;
  border: none;
  cursor: pointer;
  font-family: var(--font-family-display);
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  letter-spacing: 1px;
}
.version-toggle:hover { color: var(--color-accent); }
.version-toggle .toggle-arrow {
  margin-left: auto;
  font-size: 12px;
  color: var(--color-text-tertiary);
  transition: transform var(--transition-fast);
}
.version-toggle .toggle-arrow.open { transform: rotate(180deg); }

.version-list {
  margin-top: var(--spacing-3);
  padding-top: var(--spacing-2);
  border-top: 1px dashed var(--color-border-light);
  max-height: 280px;
  overflow-y: auto;
}
.version-node {
  position: relative;
  display: grid;
  grid-template-columns: 16px 1fr;
  gap: var(--spacing-3);
  padding: var(--spacing-2) 0;
  cursor: pointer;
  transition: transform var(--transition-fast);
}
.version-node:hover { transform: translateX(2px); }
.version-node:hover .vn-card { border-color: var(--color-accent-light); }
.vn-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid var(--color-surface);
  box-shadow: 0 0 0 1px var(--color-border);
  margin-top: 8px;
  z-index: 2;
  position: relative;
}
.vn-line {
  position: absolute;
  left: 5px;
  top: 18px;
  bottom: -8px;
  width: 1px;
  background: var(--color-border);
}
.version-node:last-child .vn-line { display: none; }
.vn-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: 8px 12px;
  font-size: var(--font-size-xs);
  transition: border-color var(--transition-fast);
}
.vn-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 2px;
}
.vn-no {
  font-family: var(--font-family-mono);
  color: var(--color-accent-dark);
  font-weight: 700;
  letter-spacing: 1px;
}
.vn-glaze {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  font-family: var(--font-family-display);
  letter-spacing: 2px;
}
.vn-label {
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  margin-bottom: 2px;
}
.vn-meta {
  font-family: var(--font-family-mono);
  color: var(--color-text-tertiary);
  font-size: 11px;
  letter-spacing: 0.5px;
}
.vn-empty {
  text-align: center;
  padding: var(--spacing-4);
  color: var(--color-text-tertiary);
  font-size: var(--font-size-xs);
  font-family: var(--font-family-mono);
}
.vt-slide-enter-active,
.vt-slide-leave-active {
  transition: all var(--transition-normal);
  overflow: hidden;
}
.vt-slide-enter-from,
.vt-slide-leave-to {
  opacity: 0;
  max-height: 0;
}
.vt-slide-enter-to,
.vt-slide-leave-from {
  opacity: 1;
  max-height: 320px;
}

/* 响应式：窄屏堆叠时取消固定高度与左边框 */
@media (max-width: 1100px) {
  .preview-panel {
    height: auto;
    border: none;
    border-bottom: 1px solid var(--color-border);
  }
}
</style>
