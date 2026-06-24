<template>
  <div class="design-page">
    <DesignHeader @command="onUserCommand" />

    <div class="design-layout">
      <ChatPanel
        :messages="messages"
        :selected-option-id="selectedOptionId"
        v-model:show-tweak-panel="showTweakPanel"
        :tweaks="tweaks"
        v-model:input-text="inputText"
        :sending="sending"
        :studios="studios"
        @select-option="selectOption"
        @apply-tweak="handleApplyTweak"
        @send="sendUserMessage"
        @generate3d="generate3D"
        @upload="onReferenceUpload"
      />
      <OptionCards
        :options="options"
        :selected-option-id="selectedOptionId"
        @select="selectOption"
        @order="openOrder"
      />
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

    <DispatchPanel
      v-model:visible="dispatchVisible"
      :studios="studios"
      :top-studio-name="topStudioName"
      v-model:studio-accepted="studioAccepted"
      :accepted-studio-name="acceptedStudioName"
      @confirm="confirmOrder"
    />
    <WorkOrderPopup v-model="workorderVisible" :order-info="currentOrderInfo" />
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
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { GLAZE_OPTIONS, GLAZE_PALETTE_MAP } from '@/constants/glaze'
import { usePreviewRotation } from '@/composables/usePreviewRotation'
import { useDesignVersions } from '@/composables/useDesignVersions'
import { useHunyuan3D } from '@/composables/useHunyuan3D'
import { useDesignMessages } from '@/composables/useDesignMessages'
import { useDesignMessagesReal } from '@/composables/useDesignMessagesReal'
import { useOrderFlow } from '@/composables/useOrderFlow'
import type { Option } from '@/types/design'
import DesignHeader from '@/components/DesignHeader.vue'
import ChatPanel from '@/components/ChatPanel.vue'
import OptionCards from '@/components/OptionCards.vue'
import PreviewCanvas from '@/components/PreviewCanvas.vue'
import DispatchPanel from '@/components/DispatchPanel.vue'
import WorkOrderPopup from '@/components/WorkOrderPopup.vue'
import Hunyuan3DProgress from '@/components/Hunyuan3DProgress.vue'

const auth = useAuthStore()
const router = useRouter()

async function onUserCommand(cmd: string) {
  if (cmd === 'logout') {
    try {
      await ElMessageBox.confirm('确定退出当前账号?', '退出登录', {
        confirmButtonText: '退出', cancelButtonText: '取消', type: 'warning',
      })
    } catch { return }
    await auth.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
    return
  }
  const routes: Record<string, string> = { profile: '/profile', orders: '/orders', admin: '/admin', studio: '/studio' }
  if (routes[cmd]) router.push(routes[cmd])
}

// ---- 3D 预览 ---------------------------------------------------------------
const previewRef = ref<InstanceType<typeof PreviewCanvas> | null>(null)
const currentGlaze = ref('冷白釉')
const glazeOptions = GLAZE_OPTIONS
const glazePaletteMap = GLAZE_PALETTE_MAP
const showTweakPanel = ref(false)

const preview = usePreviewRotation()
const { rotateX, rotateY, autoRotate, toggleAutoRotate, resetView } = preview

// ---- 消息/方案 (切换到真实 API) ------------------------------------------
// 使用环境变量控制是否使用真实 API，默认使用真实 API
const USE_REAL_API = import.meta.env.VITE_USE_REAL_API !== 'false'

const { messages, options, selectedOptionId, inputText, sending, tweaks,
        addAiMessage, onReferenceUpload, sendUserMessage, applyTweak, initSession } =
  USE_REAL_API
    ? useDesignMessagesReal(currentGlaze)
    : useDesignMessages(currentGlaze)

// ---- 版本树 ----------------------------------------------------------------
const { versions, showVersionTree, pushVersion, rollbackToVersion } =
  useDesignVersions(computed(() => options.value.find(o => o.id === selectedOptionId.value) ?? null) as any, (v) => {
    currentGlaze.value = v.glaze
    options.value = [...options.value]
  })

// ---- 派单工作室（demo 数据）------------------------------------------------
const studios = [
  { id: 'st-1', name: '景德镇 · 陶溪川 · 林师傅工作室', scores: { craft: 0.92, capacity: 0.78, geo: 0.85, rating: 0.95 }, totalScore: 0.885 },
  { id: 'st-2', name: '景德镇 · 三宝村 · 青釉工坊', scores: { craft: 0.88, capacity: 0.65, geo: 0.82, rating: 0.9 }, totalScore: 0.82 },
  { id: 'st-3', name: '德化 · 白瓷之都 · 陈氏制瓷', scores: { craft: 0.85, capacity: 0.95, geo: 0.62, rating: 0.88 }, totalScore: 0.83 },
  { id: 'st-4', name: '宜兴 · 紫砂陶社 · 竹坞窑', scores: { craft: 0.8, capacity: 0.72, geo: 0.58, rating: 0.92 }, totalScore: 0.77 },
]
const topStudioName = computed(() => {
  const top = studios.reduce((a, b) => a.totalScore > b.totalScore ? a : b)
  return top.name.split(' · ').slice(-1)[0]
})

const currentOption = computed(() => options.value.find(o => o.id === selectedOptionId.value) ?? null)

// ---- 订单流程 (抽到 composable) --------------------------------------------
const { dispatchVisible, workorderVisible, studioAccepted, acceptedStudioName,
        openOrder, confirmOrder, currentOrderInfo } =
  useOrderFlow(topStudioName, currentOption)

// ---- Hunyuan3D ------------------------------------------------------------
const hunyuan = useHunyuan3D()
const { taskState, submitTask, reset: resetHunyuan } = hunyuan
const showHunyuanProgress = ref(false)

async function generate3D() {
  if (!inputText.value.trim()) return
  showHunyuanProgress.value = true
  try { await submitTask({ Prompt: inputText.value, Model: '3.1' }) }
  catch (e) { console.error('Submit 3D task failed:', e) }
}

watch(() => taskState.value.state, (state) => {
  if (state === 'completed' && taskState.value.glbUrl) {
    const newOption: Option = {
      id: `opt-hunyuan-${Date.now()}`, idx: '🎨', name: 'AI 生成 3D',
      desc: `根据「${inputText.value.slice(0, 30)}...」生成的 3D 模型`,
      glaze: currentGlaze.value, size: '待工艺校验', days: 7, price: 0,
      tags: ['Hunyuan3D', 'AI生成'], type: 'custom',
      colors: { light: '#f5f0e8', mid: '#ece0d0', dark: '#b8a08a' },
      glbUrl: taskState.value.glbUrl,
      thumbnailUrl: taskState.value.thumbnailUrl || undefined,
    }
    options.value.push(newOption)
    selectedOptionId.value = newOption.id
    addAiMessage(`<strong>陶语 · Hunyuan3D 生成完成</strong><br/>已为您生成 3D 模型，请在右侧预览中查看。`)
  }
})

function handleHunyuanClose() {
  showHunyuanProgress.value = false
  if (taskState.value.state === 'completed') resetHunyuan()
}
function handleHunyuanRetry() { generate3D() }
function handleHunyuanFallback() { showHunyuanProgress.value = false; resetHunyuan(); sendUserMessage() }

// ---- 釉色 / 方案选择 -------------------------------------------------------
function changeGlaze(name: string) {
  const prev = currentGlaze.value
  currentGlaze.value = name
  if (currentOption.value) {
    currentOption.value.glaze = name
    const palette = glazePaletteMap[name] || glazePaletteMap['冷白釉']
    if (palette) currentOption.value.colors = { ...palette }
    options.value = [...options.value]
  }
  if (prev !== name) pushVersion(`釉色：${prev} → ${name}`)
}

function selectOption(opt: Option) {
  selectedOptionId.value = opt.id
  showTweakPanel.value = true
  rotateY.value = 0
  if (versions.value.findIndex(v => v.label.includes(`基线 · ${opt.name}`)) === -1) {
    versions.value.push({
      versionNo: versions.value.length + 1, label: `基线 · ${opt.name}`,
      glaze: opt.glaze, colors: { ...opt.colors }, desc: opt.desc,
      tagsSnapshot: [...opt.tags], createdAt: Date.now(),
    })
  }
}

function handleApplyTweak(t: string) {
  applyTweak(t, pushVersion)
  rotateY.value += 0.1
}

const craftParams = computed<Record<string, string | number>>(() => {
  const opt = currentOption.value
  if (!opt) return {} as Record<string, string | number>
  return { '材质': opt.glaze, '尺寸': opt.size, '壁厚': '4 ± 1 mm', '窑温': '1280 ℃', '烧制': '还原焰 · 12h', '工期': `${opt.days} 天`, '成品率': '约 92%' }
})

const ceramicBodyStyle = computed(() => {
  const glaze = glazeOptions.find(g => g.name === currentGlaze.value) || glazeOptions[0]
  const opt = currentOption.value
  let shape = 'width: 170px; height: 260px; border-radius: 45% 45% 40% 40% / 30% 30% 70% 70%;'
  if (opt?.type === 'rabbit') shape = 'width: 180px; height: 220px; border-radius: 50% 50% 45% 45% / 55% 55% 45% 45%;'
  else if (opt?.type === 'moon-vase') shape = 'width: 160px; height: 260px; border-radius: 50% 50% 45% 45% / 40% 40% 60% 60%;'
  else if (opt?.type === 'incense-holder') shape = 'width: 220px; height: 140px; border-radius: 50% 50% 40% 40% / 70% 70% 30% 30%;'
  return `${shape} background: ${glaze.bg};`
})

watch(selectedOptionId, (id) => {
  const opt = options.value.find(o => o.id === id)
  if (opt?.glaze && glazeOptions.find(g => g.name === opt.glaze)) currentGlaze.value = opt.glaze
})

onMounted(() => {
  auth.fetchUser()
  preview.bindStage(previewRef.value?.stageEl ?? null)

  // 初始化会话（如果使用真实 API）
  if (USE_REAL_API && initSession) {
    initSession()
  }

  addAiMessage(`<strong>你好呀，我是陶语 👋</strong><br/>把你想要的陶瓷用自然语言描述给我，我帮你生成可直接下单烧制的方案。<br/><em style="color:#8a7d6f;font-size:12px;">试试：送给妈妈的生日礼物，她属兔，喜欢月亮和桂花…</em>`)

  // 自动发送演示消息（可选）
  setTimeout(() => {
    if (!inputText.value.trim()) {
      inputText.value = '送给妈妈的生日礼物，她属兔，喜欢月亮和桂花，希望是冷白釉，放玄关'
      sendUserMessage()
    }
  }, 1500)
})
</script>

<style scoped>
.design-page {
  height: 100vh;
  background: var(--color-background);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.design-layout {
  display: grid;
  grid-template-columns: 340px 1fr 420px;
  gap: 0;
  flex: 1;
  min-height: 0;
  max-width: 1920px;
  margin: 0 auto;
  width: 100%;
  overflow: hidden;
}
.design-layout > :first-child { height: 100%; overflow: hidden; }
.design-layout > :nth-child(2) { height: 100%; min-height: 0; }
.design-layout > :last-child { height: 100%; overflow-y: auto; overflow-x: hidden; }
.design-layout > :last-child::-webkit-scrollbar { width: 6px; }
.design-layout > :last-child::-webkit-scrollbar-track { background: transparent; }
.design-layout > :last-child::-webkit-scrollbar-thumb { background: var(--color-border); border-radius: 3px; }
.design-layout > :last-child::-webkit-scrollbar-thumb:hover { background: var(--color-text-muted); }
@media (max-width: 1400px) { .design-layout { grid-template-columns: 320px 1fr 380px; } }
@media (max-width: 1100px) {
  .design-page { height: auto; min-height: 100vh; overflow: auto; }
  .design-layout { grid-template-columns: 1fr; height: auto; overflow: visible; }
  .design-layout > :first-child, .design-layout > :nth-child(2), .design-layout > :last-child { height: auto; overflow: visible; }
}
</style>
