<template>
  <div v-if="visible" class="hunyuan-progress-overlay">
    <div class="progress-card">
      <div class="progress-header">
        <h3>AI 生成 3D 模型中...</h3>
        <el-button text @click="emit('close')" v-if="canClose">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>

      <div class="progress-body">
        <!-- 进度条 -->
        <el-progress
          :percentage="progress"
          :status="progressStatus"
          :stroke-width="12"
        />

        <!-- 状态消息 -->
        <div class="status-message">
          <el-icon v-if="state === 'running'" class="spinning">
            <Loading />
          </el-icon>
          <span>{{ message }}</span>
        </div>

        <!-- 错误提示 -->
        <el-alert
          v-if="state === 'failed' || state === 'timeout'"
          :title="error || '生成失败'"
          type="error"
          :closable="false"
          show-icon
        />

        <!-- 成功提示 -->
        <el-alert
          v-if="state === 'completed'"
          title="3D 模型生成完成!"
          type="success"
          :closable="false"
          show-icon
        />
      </div>

      <div class="progress-footer">
        <el-button v-if="state === 'failed' || state === 'timeout'" @click="emit('retry')">
          重试
        </el-button>
        <el-button
          v-if="state === 'failed' || state === 'timeout'"
          type="primary"
          @click="emit('fallback')"
        >
          使用默认方案
        </el-button>
        <el-button
          v-if="state === 'completed'"
          type="primary"
          @click="emit('close')"
        >
          查看模型
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Close, Loading } from '@element-plus/icons-vue'

const props = defineProps<{
  visible: boolean
  state: 'idle' | 'submitting' | 'pending' | 'running' | 'completed' | 'failed' | 'timeout'
  progress: number
  message: string
  error: string | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'retry'): void
  (e: 'fallback'): void
}>()

const canClose = computed(() => {
  return props.state === 'completed' || props.state === 'failed' || props.state === 'timeout'
})

const progressStatus = computed(() => {
  if (props.state === 'completed') return 'success'
  if (props.state === 'failed' || props.state === 'timeout') return 'exception'
  return undefined
})
</script>

<style scoped>
.hunyuan-progress-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  backdrop-filter: blur(4px);
}

.progress-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  width: 500px;
  max-width: 90vw;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.progress-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.progress-body {
  margin-bottom: 20px;
}

.status-message {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  font-size: 14px;
  color: #606266;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.progress-body .el-alert {
  margin-top: 16px;
}

.progress-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
