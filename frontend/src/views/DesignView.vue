<template>
  <div class="design-page">
    <!-- 顶部导航 -->
    <header class="design-header">
      <div class="design-header-inner">
        <div class="header-left">
          <span class="logo-seal">陶</span>
          <div class="header-title">
            <h1>对话式设计台</h1>
            <p>描述你想要的陶瓷，AI 实时生成可烧制方案</p>
          </div>
        </div>
        <div class="header-right">
          <router-link to="/" class="nav-link">首页</router-link>
          <router-link to="/orders" class="nav-link">我的订单</router-link>
        </div>
      </div>
    </header>

    <!-- 三栏布局 -->
    <div class="design-layout">
      <!-- 左：对话流 -->
      <aside class="chat-panel">
        <div class="chat-panel-header">
          <div class="chat-badge">
            <span class="dot"></span>
            AI · 陶语设计助手
          </div>
          <div class="chat-tip">输入描述，平均 30 秒出方案</div>
        </div>

        <div ref="chatMessages" class="chat-messages">
          <div v-for="(msg, idx) in messages" :key="idx" :class="['msg', `msg-${msg.role}`]">
            <div v-if="msg.role === 'ai'" class="msg-avatar">陶</div>
            <div class="msg-body">
              <div class="msg-content" v-html="msg.content"></div>
              <div v-if="msg.options" class="msg-options-inline">
                <div
                  v-for="opt in msg.options"
                  :key="opt.id"
                  class="option-chip"
                  :class="{ active: selectedOptionId === opt.id }"
                  @click="selectOption(opt)"
                >
                  <span class="chip-idx">{{ opt.idx }}</span>
                  <span class="chip-name">{{ opt.name }}</span>
                </div>
              </div>
              <div v-if="msg.showDispatch" class="dispatch-inline">
                <DispatchVisualization :studios="studios" ref="dispatchRef" />
              </div>
            </div>
          </div>
        </div>

        <!-- 微调面板 -->
        <div v-if="showTweakPanel" class="tweak-panel">
          <div class="tweak-header">
            <span>方案微调</span>
            <el-button text @click="showTweakPanel = false">收起</el-button>
          </div>
          <div class="tweak-chips">
            <button
              v-for="t in tweaks"
              :key="t.text"
              class="tweak-chip"
              @click="applyTweak(t.text)"
            >
              {{ t.text }}
            </button>
          </div>
        </div>

        <!-- 输入栏 -->
        <div class="chat-input">
          <textarea
            v-model="inputText"
            class="input-textarea"
            placeholder="例如：送给妈妈的生日礼物，属兔，喜欢月亮桂花，冷白釉，玄关尺寸..."
            @keydown.enter.ctrl="sendUserMessage"
          ></textarea>
          <button class="send-btn" @click="sendUserMessage" :disabled="sending">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 2L11 13" />
              <path d="M22 2l-7 20-4-9-9-4 20-7z" />
            </svg>
          </button>
        </div>
      </aside>

      <!-- 中：三方案卡片 -->
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
            @click="selectOption(opt)"
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
                <button class="btn btn-ghost" @click.stop="selectOption(opt)">
                  {{ selectedOptionId === opt.id ? '已选中' : '查看 3D' }}
                </button>
                <button class="btn btn-primary" @click.stop="openOrder(opt)">
                  下单
                </button>
              </div>
            </div>
          </div>
        </transition-group>
      </main>

      <!-- 右：3D 预览 -->
      <aside class="preview-panel">
        <div class="preview-header">
          <h2>3D 预览</h2>
          <div class="preview-subtitle">{{ currentOption?.name || '等待方案' }}</div>
        </div>

        <div class="preview-stage-wrapper">
          <div class="preview-stage" ref="stageRef">
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
            <button class="rotate-btn" @click="rotateY -= 30">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 12a9 9 0 1 0 9-9" />
                <path d="M3 12l4-4M3 12l4 4" />
              </svg>
            </button>
            <div class="rotate-info">
              <span>Y: {{ Math.round(rotateY % 360) }}°</span>
              <span>X: {{ Math.round(rotateX) }}°</span>
            </div>
            <button class="rotate-btn" @click="rotateY += 30">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 12a9 9 0 1 1-9-9" />
                <path d="M21 12l-4-4M21 12l-4 4" />
              </svg>
            </button>
            <button class="auto-rotate-btn" :class="{ active: autoRotate }" @click="toggleAutoRotate">
              {{ autoRotate ? '停止旋转' : '自动旋转' }}
            </button>
            <button class="auto-rotate-btn" @click="resetView">
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
              @click="changeGlaze(g.name)"
            >
              <span class="glaze-name">{{ g.name }}</span>
            </button>
          </div>
        </div>

        <!-- P8.4.1 · 方案版本树 -->
        <div class="version-tree" v-if="currentOption">
          <button class="version-toggle" @click="showVersionTree = !showVersionTree">
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
                @click="rollbackToVersion(v)"
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

          <button class="btn btn-primary summary-cta" @click="openOrder(currentOption)">
            <span>确认方案 · 下单烧制</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M5 12h14M13 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </aside>
    </div>

    <!-- 派单可视化弹窗 -->
    <el-dialog v-model="dispatchVisible" title="" width="680px" class="dispatch-dialog" :close-on-click-modal="false">
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
        <DispatchVisualization :studios="studios" ref="dispatchRef" />
      </div>
      <template #footer>
        <div class="dispatch-footer">
          <el-button @click="dispatchVisible = false">稍后查看</el-button>
          <el-button type="primary" @click="confirmOrder">
            <span>确认派单至 {{ topStudioName }}</span>
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 工单弹窗 -->
    <WorkOrderPopup v-model="workorderVisible" :order-info="currentOrderInfo" />

    <!-- P8.4.3 · 工作室接单 Toast -->
    <transition name="accept-toast">
      <div v-if="studioAccepted" class="studio-accept-toast" @click="studioAccepted = false">
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import DispatchVisualization from '../components/DispatchVisualization.vue'
import WorkOrderPopup from '../components/WorkOrderPopup.vue'

interface Message {
  role: 'user' | 'ai'
  content: string
  options?: Option[]
  showDispatch?: boolean
}

interface OptionColors {
  light: string
  mid: string
  dark: string
}

interface Option {
  id: string
  idx: string
  name: string
  desc: string
  glaze: string
  size: string
  days: number
  price: number
  tags: string[]
  type: 'rabbit' | 'moon-vase' | 'incense-holder' | 'vase'
  colors: OptionColors
  loading?: boolean
}

const chatMessages = ref<HTMLElement | null>(null)
const stageRef = ref<HTMLElement | null>(null)
const messages = ref<Message[]>([])
const inputText = ref('')
const sending = ref(false)
const options = ref<Option[]>([])
const selectedOptionId = ref<string | null>(null)
const showTweakPanel = ref(false)
const currentGlaze = ref('冷白釉')
const rotateY = ref(0)
const rotateX = ref(-8)
const autoRotate = ref(true)
const dispatchVisible = ref(false)
const workorderVisible = ref(false)
const dispatchRef = ref<any>(null)

const glazeOptions = [
  { name: '冷白釉', bg: 'linear-gradient(135deg, #f5f0e8 0%, #ece0d0 60%, #b8a08a 100%)' },
  { name: '青瓷釉', bg: 'linear-gradient(135deg, #9ec6d0 0%, #7B9BA8 60%, #4a6e7a 100%)' },
  { name: '胭脂红', bg: 'linear-gradient(135deg, #e8a598 0%, #c75b5b 60%, #8a2a2a 100%)' },
  { name: '天目釉', bg: 'linear-gradient(135deg, #5a4a3a 0%, #2d2926 60%, #1a1513 100%)' },
  { name: '酱黄釉', bg: 'linear-gradient(135deg, #e8c98a 0%, #d4a574 60%, #8a6a3a 100%)' },
  { name: '玉青釉', bg: 'linear-gradient(135deg, #a8d4b8 0%, #5B8A72 60%, #2a5a48 100%)' },
]

// P8.4.2 · 釉色 → 三阶调色板，用于 SVG / CSS 实时同步
const glazePaletteMap: Record<string, OptionColors> = {
  '冷白釉': { light: '#f5f0e8', mid: '#ece0d0', dark: '#b8a08a' },
  '青瓷釉': { light: '#9ec6d0', mid: '#7B9BA8', dark: '#4a6e7a' },
  '胭脂红': { light: '#e8a598', mid: '#c75b5b', dark: '#8a2a2a' },
  '天目釉': { light: '#5a4a3a', mid: '#2d2926', dark: '#1a1513' },
  '酱黄釉': { light: '#e8c98a', mid: '#d4a574', dark: '#8a6a3a' },
  '玉青釉': { light: '#a8d4b8', mid: '#5B8A72', dark: '#2a5a48' },
}

// P8.4.1 · 方案版本树
interface DesignVersion {
  versionNo: number
  label: string
  glaze: string
  colors: OptionColors
  desc: string
  tagsSnapshot: string[]
  createdAt: number
}
const versions = ref<DesignVersion[]>([])
const showVersionTree = ref(false)

function pushVersion(label: string) {
  const opt = currentOption.value
  if (!opt) return
  versions.value.push({
    versionNo: versions.value.length + 1,
    label,
    glaze: opt.glaze,
    colors: { ...opt.colors },
    desc: opt.desc,
    tagsSnapshot: [...opt.tags],
    createdAt: Date.now(),
  })
}

function rollbackToVersion(v: DesignVersion) {
  const opt = currentOption.value
  if (!opt) return
  opt.glaze = v.glaze
  opt.colors = { ...v.colors }
  opt.desc = v.desc
  opt.tags = [...v.tagsSnapshot]
  currentGlaze.value = v.glaze
  options.value = [...options.value]
  // 在最末追加一条"回滚"记录
  versions.value.push({
    ...v,
    versionNo: versions.value.length + 1,
    label: `回滚到 v${v.versionNo}：${v.label}`,
    createdAt: Date.now(),
  })
}

// P8.4.3 · 工作室接单动画状态
const studioAccepted = ref(false)
const acceptedStudioName = ref('')

function triggerStudioAccept() {
  studioAccepted.value = false
  // 派单后 2 秒触发"师傅已接单"
  setTimeout(() => {
    acceptedStudioName.value = topStudioName.value
    studioAccepted.value = true
  }, 2000)
}

const tweaks = [
  { text: '耳朵再长一点' },
  { text: '整体更圆润' },
  { text: '加大底座' },
  { text: '加入桂花纹理' },
  { text: '哑光质感' },
  { text: '缩小一圈' },
  { text: '加高颈部' },
  { text: '加一点墨绿装饰线' },
]

const studios = [
  {
    id: 'st-1',
    name: '景德镇 · 陶溪川 · 林师傅工作室',
    scores: { craft: 0.92, capacity: 0.78, geo: 0.85, rating: 0.95 },
    totalScore: 0.885
  },
  {
    id: 'st-2',
    name: '景德镇 · 三宝村 · 青釉工坊',
    scores: { craft: 0.88, capacity: 0.65, geo: 0.82, rating: 0.9 },
    totalScore: 0.82
  },
  {
    id: 'st-3',
    name: '德化 · 白瓷之都 · 陈氏制瓷',
    scores: { craft: 0.85, capacity: 0.95, geo: 0.62, rating: 0.88 },
    totalScore: 0.83
  },
  {
    id: 'st-4',
    name: '宜兴 · 紫砂陶社 · 竹坞窑',
    scores: { craft: 0.8, capacity: 0.72, geo: 0.58, rating: 0.92 },
    totalScore: 0.77
  },
]

const topStudioName = computed(() => {
  const top = studios.reduce((a, b) => a.totalScore > b.totalScore ? a : b)
  return top.name.split(' · ').slice(-1)[0]
})

const currentOption = computed(() => options.value.find(o => o.id === selectedOptionId.value) || null)

const craftParams = computed(() => {
  if (!currentOption.value) return {}
  return {
    '材质': currentOption.value.glaze,
    '尺寸': currentOption.value.size,
    '壁厚': '4 ± 1 mm',
    '窑温': '1280 ℃',
    '烧制': '还原焰 · 12h',
    '工期': `${currentOption.value.days} 天`,
    '成品率': '约 92%',
  }
})

const ceramicBodyStyle = computed(() => {
  const glaze = glazeOptions.find(g => g.name === currentGlaze.value) || glazeOptions[0]
  let shape = ''
  const opt = currentOption.value
  if (opt?.type === 'rabbit') {
    shape = 'width: 180px; height: 220px; border-radius: 50% 50% 45% 45% / 55% 55% 45% 45%;'
  } else if (opt?.type === 'moon-vase') {
    shape = 'width: 160px; height: 260px; border-radius: 50% 50% 45% 45% / 40% 40% 60% 60%;'
  } else if (opt?.type === 'incense-holder') {
    shape = 'width: 220px; height: 140px; border-radius: 50% 50% 40% 40% / 70% 70% 30% 30%;'
  } else {
    shape = 'width: 170px; height: 260px; border-radius: 45% 45% 40% 40% / 30% 30% 70% 70%;'
  }
  return `${shape} background: ${glaze.bg};`
})

let rotateTimer: any = null

function toggleAutoRotate() {
  autoRotate.value = !autoRotate.value
}

function resetView() {
  rotateY.value = 0
  rotateX.value = -8
}

function changeGlaze(name: string) {
  // P8.4.2 · 釉色实时切换 — 不重新生成 mesh，本地直接刷新
  const prev = currentGlaze.value
  currentGlaze.value = name
  if (currentOption.value) {
    currentOption.value.glaze = name
    // 同步颜色调色板，让 SVG / CSS 立即响应
    const match = glazeOptions.find(g => g.name === name)
    if (match) {
      const palette = glazePaletteMap[name] || glazePaletteMap['冷白釉']
      currentOption.value.colors = { ...palette }
      // 触发响应式刷新
      options.value = [...options.value]
    }
  }
  if (prev !== name) {
    pushVersion(`釉色：${prev} → ${name}`)
  }
}

function selectOption(opt: Option) {
  selectedOptionId.value = opt.id
  showTweakPanel.value = true
  rotateY.value = 0
  // P8.4.1 · 选中即建立 v1 基线（同 option 不重复）
  if (versions.value.findIndex(v => v.label.includes(`基线 · ${opt.name}`)) === -1) {
    versions.value.push({
      versionNo: versions.value.length + 1,
      label: `基线 · ${opt.name}`,
      glaze: opt.glaze,
      colors: { ...opt.colors },
      desc: opt.desc,
      tagsSnapshot: [...opt.tags],
      createdAt: Date.now(),
    })
  }
}

function addAiMessage(content: string, withOptions?: Option[], withDispatch?: boolean) {
  messages.value.push({
    role: 'ai',
    content,
    options: withOptions,
    showDispatch: withDispatch
  })
  scrollToBottom()
}

function addUserMessage(content: string) {
  messages.value.push({
    role: 'user',
    content
  })
  scrollToBottom()
}

function scrollToBottom() {
  setTimeout(() => {
    if (chatMessages.value) {
      chatMessages.value.scrollTop = chatMessages.value.scrollHeight
    }
  }, 30)
}

function generateOptionsFromPrompt(_prompt: string): Option[] {
  return [
    {
      id: 'opt-1',
      idx: '①',
      name: '玉兔捧月',
      desc: '一只憨态可掬的兔子捧着满月，月亮中空可放干花或小信物。冷白釉主体，点缀桂花细节，适合玄关摆放。',
      glaze: currentGlaze.value,
      size: 'H 20 × W 16 cm',
      days: 9,
      price: 386,
      tags: ['叙事造型', '礼物首选', '冷白釉', '可放干花'],
      type: 'rabbit',
      colors: { light: '#f5f0e8', mid: '#ece0d0', dark: '#b8a08a' },
    },
    {
      id: 'opt-2',
      idx: '②',
      name: '月下垂桂',
      desc: '兔耳化作桂枝造型的流线型花瓶，瓶口如月轮。釉面点缀桂花形凹印，注入清水后有光影浮动。',
      glaze: currentGlaze.value === '冷白釉' ? '青瓷釉' : currentGlaze.value,
      size: 'H 24 × W 14 cm',
      days: 10,
      price: 468,
      tags: ['实用花瓶', '桂枝造型', '青瓷釉', '桂花凹印'],
      type: 'moon-vase',
      colors: { light: '#c8dfe5', mid: '#8aaeb8', dark: '#4a6e7a' },
    },
    {
      id: 'opt-3',
      idx: '③',
      name: '望舒',
      desc: '极简月牙形底座摆件。以器型胜，不做多余装饰。适合放在书桌、茶席边，也可做小型香插。',
      glaze: currentGlaze.value === '冷白釉' ? '玉青釉' : currentGlaze.value,
      size: 'H 12 × W 18 cm',
      days: 7,
      price: 268,
      tags: ['极简', '茶席摆件', '可做香插', '工期短'],
      type: 'incense-holder',
      colors: { light: '#d4e8dc', mid: '#8ab89e', dark: '#3a6a52' },
    },
  ]
}

async function sendUserMessage() {
  if (!inputText.value.trim() || sending.value) return
  const prompt = inputText.value.trim()
  inputText.value = ''
  sending.value = true

  addUserMessage(prompt)

  // Step 1: AI 解析
  setTimeout(() => {
    addAiMessage(`<strong>陶语 · 关键词解析</strong><br/>
      🐰 兔子造型 &nbsp;·&nbsp; 🌙 月亮意象 &nbsp;·&nbsp; 🌼 桂花纹样<br/>
      🎨 ${currentGlaze.value} &nbsp;·&nbsp; 📐 玄关尺寸（建议 H 18–24 cm）<br/>
      <em style="color:#8a7d6f;font-size:12px;">正在并行调用三条生成路线（模板派生 / 生成式 / 混合）…</em>`)
  }, 300)

  // Step 2: 加载骨架
  setTimeout(() => {
    options.value = [
      { id: 'opt-1', idx: '①', name: '方案 ①', desc: '', glaze: '', size: '', days: 0, price: 0, tags: [], type: 'vase', colors: { light: '#f5f0e8', mid: '#ece0d0', dark: '#b8a08a' }, loading: true },
      { id: 'opt-2', idx: '②', name: '方案 ②', desc: '', glaze: '', size: '', days: 0, price: 0, tags: [], type: 'vase', colors: { light: '#f5f0e8', mid: '#ece0d0', dark: '#b8a08a' }, loading: true },
      { id: 'opt-3', idx: '③', name: '方案 ③', desc: '', glaze: '', size: '', days: 0, price: 0, tags: [], type: 'vase', colors: { light: '#f5f0e8', mid: '#ece0d0', dark: '#b8a08a' }, loading: true },
    ]
  }, 800)

  // Step 3: 方案出炉
  setTimeout(() => {
    const newOptions = generateOptionsFromPrompt(prompt)
    options.value = newOptions
    selectedOptionId.value = newOptions[0].id

    addAiMessage(
      `<strong>陶语 · 三个方案出炉啦</strong><br/>
      每款方案均已通过工艺校验（壁厚 ≥ 3 mm、悬臂角 ≤ 30°、收缩率按材质 1.08–1.18× 预补偿）。<br/>
      <em style="color:#8a7d6f;font-size:12px;">👉 可点击下方方案查看 3D，或用"微调"按钮修改细节。</em>`,
      newOptions.map(o => ({ ...o, idx: o.idx }))
    )
    sending.value = false
  }, 1800)
}

function applyTweak(text: string) {
  addUserMessage(text)
  setTimeout(() => {
    addAiMessage(`<strong>陶语 · 已应用微调</strong><br/>「${text}」 → 更新方案参数，正在重新渲染 3D…<br/><em style="color:#8a7d6f;font-size:12px;">工艺校验通过，报价与工期保持不变。</em>`)
    if (currentOption.value) {
      const opt = currentOption.value
      if (text.includes('耳朵')) opt.desc = opt.desc + '（已调整：兔耳长度 +15%）'
      if (text.includes('圆润')) { opt.colors.light = '#f8f4ec' }
      if (text.includes('墨绿')) { opt.colors.dark = '#2d4a48'; opt.tags.push('墨绿装饰线') }
      if (text.includes('桂花')) { opt.tags.push('桂花纹理') }
      if (text.includes('哑光')) { opt.tags.push('哑光质感') }
      // 触发更新
      options.value = [...options.value]
      rotateY.value += 0.1
      // P8.4.1 · 微调即记录新版本
      pushVersion(`微调：${text}`)
    }
  }, 300)
}

function openOrder(opt: Option) {
  selectedOptionId.value = opt.id
  dispatchVisible.value = true
}

function confirmOrder() {
  dispatchVisible.value = false
  workorderVisible.value = true
  // P8.4.3 · 触发"师傅已接单"动画
  triggerStudioAccept()
}

const currentOrderInfo = computed(() => {
  const opt = currentOption.value
  const today = new Date()
  const deliveryDate = new Date(today.getTime() + ((opt?.days || 9) + 2) * 86400000)
  return {
    orderId: `CW${today.getFullYear()}${String(today.getMonth() + 1).padStart(2, '0')}${String(today.getDate()).padStart(2, '0')}${Math.floor(Math.random() * 9999).toString().padStart(4, '0')}`,
    studioName: topStudioName.value,
    productName: opt?.name || '定制陶瓷',
    leadTime: opt?.days || 9,
    deliveryDate: `${deliveryDate.getFullYear()}-${String(deliveryDate.getMonth() + 1).padStart(2, '0')}-${String(deliveryDate.getDate()).padStart(2, '0')}`,
    params: [
      opt?.glaze || currentGlaze.value,
      opt?.size || 'H 20 × W 16 cm',
      '壁厚 4±1 mm',
      '窑温 1280 ℃',
      '还原焰 · 12h',
      '成品率 ~92%',
    ],
  }
})

onMounted(() => {
  // 初始欢迎 + 示例流程
  addAiMessage(`<strong>你好呀，我是陶语 👋</strong><br/>
    把你想要的陶瓷用自然语言描述给我，我帮你生成可直接下单烧制的方案。<br/>
    <em style="color:#8a7d6f;font-size:12px;">试试：送给妈妈的生日礼物，她属兔，喜欢月亮和桂花…</em>`)

  // 旋转动画
  rotateTimer = setInterval(() => {
    if (autoRotate.value) {
      rotateY.value += 0.8
    }
  }, 50)

  // 3 秒后给出示例方案：自动注入 prompt 触发演示流
  setTimeout(() => {
    if (!inputText.value.trim()) {
      inputText.value = '送给妈妈的生日礼物，她属兔，喜欢月亮和桂花，希望是冷白釉，放玄关'
    }
    sendUserMessage()
  }, 1500)

  // mouse drag to rotate
  stageRef.value?.addEventListener('mousedown', onStageMouseDown)
})

onUnmounted(() => {
  if (rotateTimer) clearInterval(rotateTimer)
})

let dragging = false
let lastX = 0
let lastY = 0

function onStageMouseDown(e: MouseEvent) {
  dragging = true
  autoRotate.value = false
  lastX = e.clientX
  lastY = e.clientY
  window.addEventListener('mousemove', onStageMouseMove)
  window.addEventListener('mouseup', onStageMouseUp)
}

function onStageMouseMove(e: MouseEvent) {
  if (!dragging) return
  const dx = e.clientX - lastX
  const dy = e.clientY - lastY
  rotateY.value += dx * 0.5
  rotateX.value = Math.max(-25, Math.min(25, rotateX.value - dy * 0.3))
  lastX = e.clientX
  lastY = e.clientY
}

function onStageMouseUp() {
  dragging = false
  window.removeEventListener('mousemove', onStageMouseMove)
  window.removeEventListener('mouseup', onStageMouseUp)
}

watch(selectedOptionId, (id) => {
  if (id) {
    const opt = options.value.find(o => o.id === id)
    if (opt && opt.glaze) {
      const match = glazeOptions.find(g => g.name === opt.glaze)
      if (match) currentGlaze.value = opt.glaze
    }
  }
})
</script>

<style scoped>
.design-page {
  min-height: 100vh;
  background: var(--color-background);
  display: flex;
  flex-direction: column;
}

/* ========= 顶部导航 ========= */
.design-header {
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
  position: sticky;
  top: 0;
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
  gap: 24px;
}
.nav-link {
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: 14px;
  transition: color 0.2s;
}
.nav-link:hover {
  color: var(--color-primary);
}

/* ========= 三栏布局 ========= */
.design-layout {
  display: grid;
  grid-template-columns: 340px 1fr 420px;
  gap: 0;
  flex: 1;
  min-height: 0;
  max-width: 1920px;
  margin: 0 auto;
  width: 100%;
}

/* ========= 聊天面板 ========= */
.chat-panel {
  border-right: 1px solid var(--color-border);
  background: var(--color-surface);
  display: flex;
  flex-direction: column;
  height: calc(100vh - 72px);
}

.chat-panel-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border-light);
}
.chat-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-primary);
  font-family: var(--font-family-display);
  letter-spacing: 1px;
  margin-bottom: 6px;
}
.chat-badge .dot {
  width: 8px;
  height: 8px;
  background: var(--color-accent);
  border-radius: 50%;
  box-shadow: 0 0 0 3px rgba(201, 123, 90, 0.2);
  animation: pulse 2s ease-in-out infinite;
}
.chat-tip {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.msg {
  display: flex;
  gap: 12px;
  max-width: 100%;
  animation: msg-in 0.4s ease-out both;
}

@keyframes msg-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.msg-user {
  justify-content: flex-end;
}

.msg-avatar {
  width: 32px;
  height: 32px;
  min-width: 32px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  color: var(--glaze-white);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-family-display);
  font-size: 14px;
  font-weight: 700;
  box-shadow: 0 2px 6px rgba(45, 74, 72, 0.25);
  margin-top: 4px;
}

.msg-body {
  max-width: calc(100% - 44px);
}
.msg-user .msg-body {
  max-width: 85%;
}

.msg-content {
  padding: 12px 16px;
  border-radius: var(--radius-xl);
  font-size: 13px;
  line-height: 1.8;
}

.msg-ai .msg-content {
  background: var(--color-background);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-light);
  border-bottom-left-radius: 4px;
}

.msg-user .msg-content {
  background: var(--color-primary);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.msg-options-inline {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.option-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.option-chip:hover {
  border-color: var(--color-accent);
  background: rgba(201, 123, 90, 0.04);
}
.option-chip.active {
  border-color: var(--color-primary);
  background: rgba(45, 74, 72, 0.06);
}
.chip-idx {
  font-family: var(--font-family-display);
  color: var(--color-accent);
  font-weight: 700;
}
.chip-name {
  color: var(--color-text-primary);
  font-weight: 500;
}

.dispatch-inline {
  margin-top: 12px;
}

/* ========= 微调面板 ========= */
.tweak-panel {
  margin: 0 20px 12px;
  padding: 12px;
  background: var(--color-bg2);
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-border-light);
}
.tweak-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 10px;
  font-weight: 500;
}
.tweak-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.tweak-chip {
  padding: 6px 10px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  border-radius: var(--radius-full);
  font-size: 12px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}
.tweak-chip:hover {
  border-color: var(--color-accent);
  color: var(--color-accent-dark);
  background: rgba(201, 123, 90, 0.05);
}

/* ========= 输入栏 ========= */
.chat-input {
  padding: 16px 20px 20px;
  border-top: 1px solid var(--color-border-light);
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

.input-textarea {
  flex: 1;
  min-height: 48px;
  max-height: 140px;
  padding: 12px 16px;
  font-size: 13px;
  font-family: inherit;
  line-height: 1.6;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  background: var(--color-background);
  color: var(--color-text-primary);
  resize: none;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.input-textarea:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(45, 74, 72, 0.08);
}
.input-textarea::placeholder {
  color: var(--color-text-muted);
}

.send-btn {
  width: 48px;
  height: 48px;
  min-width: 48px;
  border-radius: var(--radius-xl);
  border: none;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  color: #fff;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  box-shadow: 0 4px 12px rgba(45, 74, 72, 0.25);
}
.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.send-btn:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(45, 74, 72, 0.35);
}
.send-btn svg {
  width: 20px;
  height: 20px;
}

/* ========= 方案面板 ========= */
.options-panel {
  padding: 32px;
  overflow-y: auto;
  height: calc(100vh - 72px);
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

/* ========= 响应式 ========= */
@media (max-width: 1400px) {
  .design-layout {
    grid-template-columns: 320px 1fr 380px;
  }
}
@media (max-width: 1100px) {
  .design-layout {
    grid-template-columns: 1fr;
    height: auto;
  }
  .chat-panel, .options-panel, .preview-panel {
    height: auto;
    border: none;
    border-bottom: 1px solid var(--color-border);
  }
}

/* Scrollbar */
.chat-messages::-webkit-scrollbar,
.options-panel::-webkit-scrollbar {
  width: 6px;
}
.chat-messages::-webkit-scrollbar-thumb,
.options-panel::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 3px;
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
