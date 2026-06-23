<template>
  <div class="design-page">
    <!-- 顶部导航 -->
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
        </div>
      </div>
    </header>

    <!-- 三栏布局 -->
    <div class="design-layout">
      <!-- 左：对话流 -->
      <ChatPanel
        :messages="messages"
        :selected-option-id="selectedOptionId"
        v-model:show-tweak-panel="showTweakPanel"
        :tweaks="tweaks"
        v-model:input-text="inputText"
        :sending="sending"
        :studios="studios"
        @select-option="selectOption"
        @apply-tweak="applyTweak"
        @send="sendUserMessage"
        @generate3d="generate3D"
      />

      <!-- 中：三方案卡片 -->
      <OptionCards
        :options="options"
        :selected-option-id="selectedOptionId"
        @select="selectOption"
        @order="openOrder"
      />

      <!-- 右：3D 预览 -->
      <PreviewCanvas
        ref="previewRef"
        :current-option="currentOption"
        :rotate-x="rotateX"
        :rotate-y="rotateY"
        :auto-rotate="autoRotate"
        :ceramic-body-style="ceramicBodyStyle"
        :glaze-options="glazeOptions"
        :current-glaze="currentGlaze"
        :versions="versions"
        v-model:show-version-tree="showVersionTree"
        :craft-params="craftParams"
        @rotate="rotateY += $event"
        @toggle-auto-rotate="toggleAutoRotate"
        @reset-view="resetView"
        @change-glaze="changeGlaze"
        @order="openOrder"
        @rollback="rollbackToVersion"
      />
    </div>

    <!-- 派单可视化弹窗 + 接单 Toast -->
    <DispatchPanel
      v-model:visible="dispatchVisible"
      :studios="studios"
      :top-studio-name="topStudioName"
      v-model:studio-accepted="studioAccepted"
      :accepted-studio-name="acceptedStudioName"
      @confirm="confirmOrder"
    />

    <!-- 工单弹窗 -->
    <WorkOrderPopup v-model="workorderVisible" :order-info="currentOrderInfo" />

    <!-- Hunyuan3D 进度弹窗 -->
    <Hunyuan3DProgress
      :visible="showHunyuanProgress"
      :state="taskState.state"
      :progress="taskState.progress"
      :message="taskState.message"
      :error="taskState.error"
      @close="handleHunyuanClose"
      @retry="handleHunyuanRetry"
      @fallback="handleHunyuanFallback"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import ChatPanel from '@/components/ChatPanel.vue'
import OptionCards from '@/components/OptionCards.vue'
import PreviewCanvas from '@/components/PreviewCanvas.vue'
import DispatchPanel from '@/components/DispatchPanel.vue'
import WorkOrderPopup from '@/components/WorkOrderPopup.vue'
import Hunyuan3DProgress from '@/components/Hunyuan3DProgress.vue'
import { usePreviewRotation } from '@/composables/usePreviewRotation'
import { useDesignVersions } from '@/composables/useDesignVersions'
import { useHunyuan3D } from '@/composables/useHunyuan3D'
import { GLAZE_OPTIONS, GLAZE_PALETTE_MAP } from '@/constants/glaze'
import type { Message, Option } from '@/types/design'

const previewRef = ref<InstanceType<typeof PreviewCanvas> | null>(null)
const messages = ref<Message[]>([])
const inputText = ref('')
const sending = ref(false)
const options = ref<Option[]>([])
const selectedOptionId = ref<string | null>(null)
const showTweakPanel = ref(false)
const currentGlaze = ref('冷白釉')

// 3D 预览的旋转/拖拽/auto-rotate 已抽到 composable
const preview = usePreviewRotation()
const { rotateX, rotateY, autoRotate } = preview

// Hunyuan3D 3D 生成
const hunyuan = useHunyuan3D()
const { taskState, submitTask, reset: resetHunyuan } = hunyuan
const showHunyuanProgress = ref(false)

const dispatchVisible = ref(false)
const workorderVisible = ref(false)

const glazeOptions = GLAZE_OPTIONS
const glazePaletteMap = GLAZE_PALETTE_MAP

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

// P8.4.1 · 方案版本树（抽到 composable，与 currentOption 解耦后管理）
const { versions, showVersionTree, pushVersion, rollbackToVersion } =
  useDesignVersions(currentOption as any, (v) => {
    // 回滚后同步全局 currentGlaze + 强制响应式刷新
    currentGlaze.value = v.glaze
    options.value = [...options.value]
  })

const craftParams = computed<Record<string, string | number>>(() => {
  if (!currentOption.value) return {}
  const params: Record<string, string | number> = {
    '材质': currentOption.value.glaze,
    '尺寸': currentOption.value.size,
    '壁厚': '4 ± 1 mm',
    '窑温': '1280 ℃',
    '烧制': '还原焰 · 12h',
    '工期': `${currentOption.value.days} 天`,
    '成品率': '约 92%',
  }
  return params
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

// 旋转控制与拖拽逻辑已收敛到 preview composable，这里仅暴露给模板使用
const toggleAutoRotate = preview.toggleAutoRotate
const resetView = preview.resetView

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
}

function addUserMessage(content: string) {
  messages.value.push({
    role: 'user',
    content
  })
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

// Hunyuan3D 3D 生成
async function generate3D() {
  if (!inputText.value.trim()) {
    return
  }

  showHunyuanProgress.value = true

  try {
    await submitTask({
      Prompt: inputText.value,
      Model: '3.1'
    })
  } catch (error) {
    console.error('Submit 3D task failed:', error)
  }
}

// 监听任务完成
watch(() => taskState.value.state, (newState) => {
  if (newState === 'completed' && taskState.value.glbUrl) {
    // 将生成的 GLB 添加到方案列表
    const newOption: Option = {
      id: `opt-hunyuan-${Date.now()}`,
      idx: '🎨',
      name: 'AI 生成 3D',
      desc: `根据「${inputText.value.slice(0, 30)}...」生成的 3D 模型`,
      glaze: currentGlaze.value,
      size: '待工艺校验',
      days: 7,
      price: 0,
      tags: ['Hunyuan3D', 'AI生成'],
      type: 'custom',
      colors: { light: '#f5f0e8', mid: '#ece0d0', dark: '#b8a08a' },
      glbUrl: taskState.value.glbUrl,
      thumbnailUrl: taskState.value.thumbnailUrl || undefined
    }

    options.value.push(newOption)
    selectedOptionId.value = newOption.id

    addAiMessage(`<strong>陶语 · Hunyuan3D 生成完成</strong><br/>
      已为您生成 3D 模型,请在右侧预览中查看。<br/>
      <em style="color:#8a7d6f;font-size:12px;">注意: AI 生成的模型需要人工工艺校验后才能烧制。</em>`)
  }
})

function handleHunyuanClose() {
  showHunyuanProgress.value = false
  if (taskState.value.state === 'completed') {
    resetHunyuan()
  }
}

function handleHunyuanRetry() {
  generate3D()
}

function handleHunyuanFallback() {
  showHunyuanProgress.value = false
  resetHunyuan()
  // 使用默认方案生成流程
  sendUserMessage()
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

  // 3 秒后给出示例方案：自动注入 prompt 触发演示流
  setTimeout(() => {
    if (!inputText.value.trim()) {
      inputText.value = '送给妈妈的生日礼物，她属兔，喜欢月亮和桂花，希望是冷白釉，放玄关'
    }
    sendUserMessage()
  }, 1500)

  // 拖拽旋转：交给 composable 接管（自动管理 mousedown/move/up + 卸载清理）
  preview.bindStage(previewRef.value?.stageEl ?? null)
})

// onUnmounted 内的 rotateTimer 清理也由 composable 自动管理

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
}
</style>
