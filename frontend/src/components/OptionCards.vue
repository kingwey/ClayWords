<template>
  <main class="options-panel">
    <div class="options-header">
      <h2>可烧制方案</h2>
      <div class="options-meta">
        <span class="meta-tag">共 {{ options.length }} 个</span>
        <span class="meta-tag muted">点击选中 → 查看 3D → 一键下单</span>
      </div>
    </div>

    <transition-group name="cards" tag="div" class="options-grid">
      <div
        v-for="(opt, idx) in options"
        :key="opt.id"
        class="option-card"
        :class="{
          selected: selectedOptionId === opt.id,
          loading: opt.loading
        }"
        :style="{ animationDelay: `${idx * 0.12}s` }"
        @click="emit('select', opt)"
      >
        <div class="option-thumbnail">
          <!-- SVG 陶瓷示意图 -->
          <svg v-if="!opt.loading" viewBox="0 0 300 380" class="option-svg">
            <defs>
              <linearGradient :id="`body-${opt.id}`" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" :stop-color="opt.colors?.light || '#f5f0e8'" />
                <stop offset="50%" :stop-color="opt.colors?.mid || '#ece0d0'" />
                <stop offset="100%" :stop-color="opt.colors?.dark || '#b8a08a'" />
              </linearGradient>
              <radialGradient :id="`hl-${opt.id}`" cx="30%" cy="25%" r="50%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.8" />
                <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
              </radialGradient>
            </defs>
            <!-- 阴影 -->
            <ellipse cx="150" cy="350" rx="80" ry="8" fill="rgba(42,36,32,0.15)" />
            <!-- 根据方案类型渲染不同造型 -->
            <g v-if="opt.type === 'rabbit'">
              <!-- 兔身 -->
              <ellipse cx="150" cy="280" rx="55" ry="45" :fill="`url(#body-${opt.id})`" stroke="rgba(42,36,32,0.12)" stroke-width="1" />
              <!-- 兔头 -->
              <ellipse cx="150" cy="220" rx="32" ry="28" :fill="`url(#body-${opt.id})`" stroke="rgba(42,36,32,0.12)" stroke-width="1" />
              <!-- 长耳 -->
              <ellipse cx="132" cy="155" rx="8" ry="32" :fill="`url(#body-${opt.id})`" transform="rotate(-6 132 155)" stroke="rgba(42,36,32,0.12)" stroke-width="1" />
              <ellipse cx="168" cy="155" rx="8" ry="32" :fill="`url(#body-${opt.id})`" transform="rotate(6 168 155)" stroke="rgba(42,36,32,0.12)" stroke-width="1" />
              <ellipse cx="132" cy="160" rx="3" ry="22" fill="rgba(201,123,90,0.3)" transform="rotate(-6 132 160)" />
              <ellipse cx="168" cy="160" rx="3" ry="22" fill="rgba(201,123,90,0.3)" transform="rotate(6 168 160)" />
              <!-- 眼睛 -->
              <circle cx="140" cy="218" r="2.5" fill="#2a2420" />
              <circle cx="160" cy="218" r="2.5" fill="#2a2420" />
              <!-- 腮红 -->
              <circle cx="132" cy="228" r="4" fill="#e8a598" opacity="0.5" />
              <circle cx="168" cy="228" r="4" fill="#e8a598" opacity="0.5" />
              <!-- 月亮 -->
              <ellipse cx="150" cy="280" rx="30" ry="12" fill="rgba(212,165,116,0.18)" />
              <!-- 桂花点缀 -->
              <circle cx="105" cy="270" r="3" fill="#d4a574" opacity="0.8" />
              <circle cx="195" cy="275" r="3" fill="#d4a574" opacity="0.8" />
              <circle cx="125" cy="310" r="2.5" fill="#d4a574" opacity="0.6" />
              <circle cx="180" cy="320" r="2.5" fill="#d4a574" opacity="0.6" />
            </g>
            <g v-else-if="opt.type === 'moon-vase'">
              <!-- 瓶身 -->
              <path
                d="M 150 80 Q 125 85 120 120 Q 100 150 95 200 Q 90 280 120 340 Q 140 360 150 362 Q 160 362 180 340 Q 210 280 205 200 Q 200 150 180 120 Q 175 85 150 80 Z"
                :fill="`url(#body-${opt.id})`" stroke="rgba(42,36,32,0.15)" stroke-width="1"
              />
              <!-- 瓶口 -->
              <ellipse cx="150" cy="82" rx="24" ry="6" fill="#fffdf9" stroke="rgba(42,36,32,0.2)" stroke-width="1" />
              <!-- 高光 -->
              <ellipse cx="125" cy="200" rx="10" ry="80" :fill="`url(#hl-${opt.id})`" />
              <!-- 装饰线 -->
              <path d="M 120 280 Q 150 285 180 280" fill="none" stroke="rgba(45,74,72,0.25)" stroke-width="1.5" />
            </g>
            <g v-else-if="opt.type === 'incense-holder'">
              <!-- 圆盘底座 -->
              <ellipse cx="150" cy="320" rx="95" ry="18" :fill="`url(#body-${opt.id})`" stroke="rgba(42,36,32,0.15)" stroke-width="1" />
              <ellipse cx="150" cy="315" rx="85" ry="12" fill="rgba(42,36,32,0.05)" />
              <!-- 主体 -->
              <path d="M 120 315 Q 115 200 150 160 Q 185 200 180 315 Z" :fill="`url(#body-${opt.id})`" stroke="rgba(42,36,32,0.15)" stroke-width="1" />
              <!-- 三个孔 -->
              <circle cx="150" cy="200" r="6" fill="rgba(42,36,32,0.3)" />
              <circle cx="130" cy="230" r="5" fill="rgba(42,36,32,0.25)" />
              <circle cx="170" cy="230" r="5" fill="rgba(42,36,32,0.25)" />
            </g>
            <g v-else>
              <!-- 默认花瓶 -->
              <path
                d="M 150 90 Q 130 95 128 130 Q 100 170 98 220 Q 95 300 130 355 Q 145 365 150 365 Q 155 365 170 355 Q 205 300 202 220 Q 200 170 172 130 Q 170 95 150 90 Z"
                :fill="`url(#body-${opt.id})`" stroke="rgba(42,36,32,0.15)" stroke-width="1"
              />
              <ellipse cx="150" cy="92" rx="22" ry="5" fill="#fffdf9" stroke="rgba(42,36,32,0.2)" stroke-width="1" />
              <ellipse cx="130" cy="220" rx="8" ry="60" :fill="`url(#hl-${opt.id})`" />
            </g>
          </svg>
          <div v-else class="option-skeleton">
            <div class="skeleton-ring"></div>
            <div class="skeleton-text">陶艺生成中...</div>
          </div>

          <div class="option-glaze-tag">{{ opt.glaze }}</div>
        </div>

        <div class="option-info">
          <div class="option-head">
            <span class="option-idx">{{ opt.idx }}.</span>
            <span class="option-name">{{ opt.name }}</span>
          </div>
          <p class="option-desc">{{ opt.desc }}</p>

          <div class="option-tags">
            <span class="tag" v-for="t in opt.tags" :key="t">{{ t }}</span>
          </div>

          <div class="option-meta">
            <div class="meta-item">
              <span class="meta-label">尺寸</span>
              <span class="meta-value">{{ opt.size }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">工期</span>
              <span class="meta-value">{{ opt.days }} 天</span>
            </div>
            <div class="meta-item price">
              <span class="meta-label">报价</span>
              <span class="meta-value">¥{{ opt.price }}</span>
            </div>
          </div>

          <div class="option-actions">
            <button class="btn btn-ghost" @click.stop="emit('select', opt)">
              {{ selectedOptionId === opt.id ? '已选中' : '查看 3D' }}
            </button>
            <button class="btn btn-primary" @click.stop="emit('order', opt)">
              下单
            </button>
          </div>
        </div>
      </div>
    </transition-group>
  </main>
</template>

<script setup lang="ts">
import type { Option } from '@/types/design'

defineProps<{
  options: Option[]
  selectedOptionId: string | null
}>()

const emit = defineEmits<{
  (e: 'select', opt: Option): void
  (e: 'order', opt: Option): void
}>()
</script>

<style scoped>
/* ========= 方案面板 ========= */
.options-panel {
  padding: 32px;
  overflow-y: auto;
  overflow-x: hidden;
  height: 100%;
  background: var(--color-background);
}

.options-header {
  margin-bottom: 28px;
}
.options-header h2 {
  font-size: 22px;
  font-family: var(--font-family-display);
  color: var(--color-text-primary);
  margin: 0 0 8px;
  letter-spacing: 2px;
  font-weight: 700;
}
.options-meta {
  display: flex;
  gap: 12px;
  align-items: center;
}
.meta-tag {
  font-size: 12px;
  color: var(--color-accent-dark);
  font-family: var(--font-family-mono);
  letter-spacing: 1px;
}
.meta-tag.muted {
  color: var(--color-text-tertiary);
}

.options-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.cards-enter-active {
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.cards-leave-active {
  transition: all 0.3s ease-out;
}
.cards-move {
  transition: transform 0.3s;
}

.option-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-2xl);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  animation: card-rise 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  position: relative;
}

@keyframes card-rise {
  from { opacity: 0; transform: translateY(20px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.option-card:hover {
  transform: translateY(-4px);
  border-color: var(--color-accent-light);
  box-shadow: 0 16px 40px rgba(42, 36, 32, 0.1);
}

.option-card.selected {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(45, 74, 72, 0.1), 0 16px 40px rgba(42, 36, 32, 0.12);
}

.option-thumbnail {
  height: 220px;
  background: linear-gradient(180deg, #faf6f0 0%, #f3ebe0 100%);
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.option-svg {
  width: 80%;
  height: 90%;
  filter: drop-shadow(0 8px 16px rgba(42, 36, 32, 0.15));
  animation: float 4s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}

.option-skeleton {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: var(--color-text-tertiary);
}

.skeleton-ring {
  width: 80px;
  height: 80px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.skeleton-text {
  font-size: 12px;
  font-family: var(--font-family-mono);
  letter-spacing: 1px;
}

.option-glaze-tag {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 4px 10px;
  background: rgba(255, 253, 249, 0.9);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-full);
  font-size: 11px;
  color: var(--color-text-secondary);
  font-family: var(--font-family-mono);
  letter-spacing: 1px;
  backdrop-filter: blur(6px);
}

.option-info {
  padding: 20px;
}

.option-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 8px;
}
.option-idx {
  font-family: var(--font-family-display);
  color: var(--color-accent);
  font-size: 18px;
  font-weight: 700;
}
.option-name {
  font-size: 17px;
  font-weight: 700;
  color: var(--color-text-primary);
  font-family: var(--font-family-display);
  letter-spacing: 1px;
}
.option-desc {
  font-size: 12.5px;
  line-height: 1.8;
  color: var(--color-text-secondary);
  margin: 0 0 12px;
}

.option-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 14px;
}
.option-tags .tag {
  font-size: 10.5px;
  padding: 3px 8px;
  background: rgba(45, 74, 72, 0.06);
  color: var(--color-primary-dark);
  border-radius: var(--radius-full);
  letter-spacing: 0.5px;
  font-family: var(--font-family-mono);
}

.option-meta {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
  padding: 12px;
  background: var(--color-bg2);
  border-radius: var(--radius-lg);
  margin-bottom: 14px;
}
.meta-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.meta-item.price .meta-value {
  color: var(--color-accent-dark);
  font-weight: 700;
}
.meta-label {
  font-size: 10px;
  color: var(--color-text-tertiary);
  font-family: var(--font-family-mono);
  letter-spacing: 1px;
}
.meta-value {
  font-size: 13px;
  color: var(--color-text-primary);
  font-weight: 500;
}

.option-actions {
  display: flex;
  gap: 8px;
}

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
.btn-ghost {
  background: transparent;
  border-color: var(--color-border);
  color: var(--color-text-secondary);
}
.btn-ghost:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
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

/* Scrollbar */
.options-panel::-webkit-scrollbar {
  width: 6px;
}
.options-panel::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 3px;
}

/* 响应式：窄屏堆叠时取消固定高度与边框 */
@media (max-width: 1100px) {
  .options-panel {
    height: auto;
    border: none;
    border-bottom: 1px solid var(--color-border);
  }
}
</style>
