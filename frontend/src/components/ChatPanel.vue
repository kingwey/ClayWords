<template>
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
              @click="emit('select-option', opt)"
            >
              <span class="chip-idx">{{ opt.idx }}</span>
              <span class="chip-name">{{ opt.name }}</span>
            </div>
          </div>
          <div v-if="msg.showDispatch" class="dispatch-inline">
            <DispatchVisualization :studios="studios" />
          </div>
        </div>
      </div>
    </div>

    <!-- 微调面板 -->
    <div v-if="showTweakPanel" class="tweak-panel">
      <div class="tweak-header">
        <span>方案微调</span>
        <el-button text @click="emit('update:showTweakPanel', false)">收起</el-button>
      </div>
      <div class="tweak-chips">
        <button
          v-for="t in tweaks"
          :key="t.text"
          class="tweak-chip"
          @click="emit('apply-tweak', t.text)"
        >
          {{ t.text }}
        </button>
      </div>
    </div>

    <!-- 输入区域 (卡片式: 上方文本框 + 下方工具栏) -->
    <div class="chat-input-container">
      <!-- 文本输入 (整行) -->
      <textarea
        :value="inputText"
        class="input-textarea"
        placeholder="发消息或按住空格说话... 例如：送给妈妈的生日礼物，属兔，喜欢月亮桂花，冷白釉"
        @input="emit('update:inputText', ($event.target as HTMLTextAreaElement).value)"
        @keydown.enter.ctrl="emit('send')"
      ></textarea>

      <!-- 底部工具栏 -->
      <div class="input-toolbar">
        <!-- 左侧: 功能图标 -->
        <div class="toolbar-left">
          <button class="tool-icon" title="快速示例">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="3" />
              <path d="M9 8l3 4-3 4" />
            </svg>
          </button>
          <button class="tool-icon" title="上传参考图">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21.44 11.05l-9.19 9.19a5 5 0 01-7.07-7.07l9.19-9.19a3 3 0 014.24 4.24l-9.2 9.19a1 1 0 01-1.41-1.41l8.49-8.49" />
            </svg>
          </button>
          <span class="tool-divider"></span>
          <button
            class="tool-mode"
            :class="{ active: turboMode }"
            title="速通模式：跳过细化，直接出方案"
            @click="turboMode = !turboMode"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" stroke="none">
              <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
            </svg>
            <span>速通</span>
          </button>
        </div>

        <!-- 右侧: 模型 + 语音 + 发送 -->
        <div class="toolbar-right">
          <button class="model-select" title="切换生成方式">
            <span>陶语 · 智能匹配</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>
          <button
            class="tool-icon"
            title="使用 Hunyuan3D 生成真实 3D 模型"
            :disabled="sending"
            @click="emit('generate3d')"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </button>
          <button class="tool-icon" title="语音输入">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="2" width="6" height="12" rx="3" />
              <path d="M5 10a7 7 0 0014 0M12 19v3" />
            </svg>
          </button>
          <button class="send-btn" @click="emit('send')" :disabled="sending || !inputText.trim()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M12 19V5M5 12l7-7 7 7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import DispatchVisualization from './DispatchVisualization.vue'
import type { Message, Option, Studio } from '@/types/design'

const props = defineProps<{
  messages: Message[]
  selectedOptionId: string | null
  showTweakPanel: boolean
  tweaks: { text: string }[]
  inputText: string
  sending: boolean
  studios: Studio[]
}>()

const emit = defineEmits<{
  (e: 'select-option', opt: Option): void
  (e: 'apply-tweak', text: string): void
  (e: 'send'): void
  (e: 'generate3d'): void
  (e: 'update:inputText', value: string): void
  (e: 'update:showTweakPanel', value: boolean): void
}>()

const chatMessages = ref<HTMLElement | null>(null)

// 速通模式开关 (UI 态; 是否真的跳过细化由父组件 send 时读取)
const turboMode = ref(false)

// 消息追加后自动滚到底部（原 scrollToBottom 逻辑下沉到组件内部）
watch(
  () => props.messages.length,
  () => {
    nextTick(() => {
      if (chatMessages.value) {
        chatMessages.value.scrollTop = chatMessages.value.scrollHeight
      }
    })
  },
)
</script>

<style scoped>
/* ========= 聊天面板 ========= */
.chat-panel {
  border-right: 1px solid var(--color-border);
  background: var(--color-surface);
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
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

/* ========= 输入区域 (卡片式容器) ========= */
.chat-input-container {
  margin: 0 16px 16px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  flex-shrink: 0;
  transition: border-color 0.2s, box-shadow 0.2s;
  overflow: hidden;
}

.chat-input-container:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 4px 16px rgba(45, 74, 72, 0.08);
}

/* 文本输入 (整行) */
.input-textarea {
  display: block;
  width: 100%;
  min-height: 56px;
  max-height: 160px;
  padding: 16px 18px 6px;
  font-size: 14px;
  font-family: inherit;
  line-height: 1.6;
  border: none;
  background: transparent;
  color: var(--color-text-primary);
  resize: none;
  outline: none;
  box-sizing: border-box;
}
.input-textarea::placeholder {
  color: var(--color-text-muted);
}

/* ========= 底部工具栏 ========= */
.input-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px 10px;
  gap: 8px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 圆角图标按钮 */
.tool-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
}
.tool-icon:hover:not(:disabled) {
  background: rgba(45, 74, 72, 0.07);
  color: var(--color-primary);
}
.tool-icon:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.tool-icon svg {
  width: 18px;
  height: 18px;
}

/* 竖向分隔线 */
.tool-divider {
  width: 1px;
  height: 18px;
  background: var(--color-border);
  margin: 0 4px;
}

/* 速通模式开关 */
.tool-mode {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 32px;
  padding: 0 10px;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}
.tool-mode svg {
  width: 15px;
  height: 15px;
}
.tool-mode:hover {
  background: rgba(45, 74, 72, 0.06);
}
.tool-mode.active {
  color: var(--color-success, #5b8a72);
}
.tool-mode.active svg {
  color: var(--color-success, #5b8a72);
}

/* 模型/方式选择 */
.model-select {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 32px;
  padding: 0 10px;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}
.model-select:hover {
  background: rgba(45, 74, 72, 0.06);
  color: var(--color-primary);
}
.model-select svg {
  width: 14px;
  height: 14px;
}

/* 发送按钮 (突出) */
.send-btn {
  width: 36px;
  height: 36px;
  min-width: 36px;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  color: #fff;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-left: 4px;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(45, 74, 72, 0.25);
}
.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  box-shadow: none;
}
.send-btn:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(45, 74, 72, 0.35);
}
.send-btn svg {
  width: 18px;
  height: 18px;
}

/* Scrollbar */
.chat-messages::-webkit-scrollbar {
  width: 6px;
}
.chat-messages::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 3px;
}

/* 响应式：窄屏堆叠时取消固定高度与右边框 */
@media (max-width: 1100px) {
  .chat-panel {
    height: auto;
    border: none;
    border-bottom: 1px solid var(--color-border);
  }
}
</style>
