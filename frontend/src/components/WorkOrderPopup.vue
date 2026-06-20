<template>
  <el-dialog
    v-model="visible"
    title=""
    width="420px"
    :close-on-click-modal="false"
    :show-close="false"
    class="workorder-dialog"
  >
    <div class="workorder-content">
      <!-- Seal Animation -->
      <div class="seal-container">
        <div class="seal" :class="{ 'stamp': isStamped }">
          <span class="seal-text">工单已派出</span>
        </div>
        <div class="handwritten" :class="{ 'show': showHandwritten }">
          师傅接单中...
        </div>
      </div>

      <!-- Work Order Info -->
      <div class="workorder-info">
        <div class="info-header">
          <h3>{{ orderInfo.studioName }}</h3>
          <span class="order-id">#{{ orderInfo.orderId.slice(0, 8) }}</span>
        </div>

        <div class="info-details">
          <div class="detail-row">
            <span class="label">作品名称</span>
            <span class="value">{{ orderInfo.productName }}</span>
          </div>
          <div class="detail-row">
            <span class="label">制作工期</span>
            <span class="value">{{ orderInfo.leadTime }}天</span>
          </div>
          <div class="detail-row">
            <span class="label">预计送达</span>
            <span class="value">{{ orderInfo.deliveryDate }}</span>
          </div>
        </div>

        <div class="craft-params">
          <h4>工艺参数</h4>
          <div class="param-tags">
            <span v-for="param in orderInfo.params" :key="param" class="param-tag">
              {{ param }}
            </span>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="workorder-actions">
        <el-button @click="handleViewPDF">
          查看工单 PDF
        </el-button>
        <el-button type="primary" @click="handleClose">
          完成
        </el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

interface OrderInfo {
  orderId: string
  studioName: string
  productName: string
  leadTime: number
  deliveryDate: string
  params: string[]
  pdfUrl?: string
}

const props = defineProps<{
  modelValue: boolean
  orderInfo: OrderInfo
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'viewPDF', url: string): void
  (e: 'close'): void
}>()

const visible = ref(props.modelValue)
const isStamped = ref(false)
const showHandwritten = ref(false)

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val) {
    // Reset animation state
    isStamped.value = false
    showHandwritten.value = false

    // Trigger stamp animation
    setTimeout(() => {
      isStamped.value = true
    }, 200)

    // Show handwritten text
    setTimeout(() => {
      showHandwritten.value = true
    }, 800)
  }
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

function handleViewPDF() {
  if (props.orderInfo.pdfUrl) {
    emit('viewPDF', props.orderInfo.pdfUrl)
    window.open(props.orderInfo.pdfUrl, '_blank')
  }
}

function handleClose() {
  emit('close')
  visible.value = false
}
</script>

<style scoped>
.workorder-content {
  padding: var(--spacing-4);
  text-align: center;
}

/* Seal Animation */
.seal-container {
  position: relative;
  height: 120px;
  margin-bottom: var(--spacing-6);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.seal {
  width: 100px;
  height: 100px;
  border: 4px solid var(--color-primary);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(201, 123, 90, 0.08);
  opacity: 0;
  transform: scale(0.5) rotate(-30deg);
  transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.seal.stamp {
  opacity: 1;
  transform: scale(1) rotate(0deg);
}

.seal-text {
  font-size: var(--font-size-sm);
  font-weight: 900;
  color: var(--color-primary-dark);
  text-align: center;
  line-height: 1.2;
}

.handwritten {
  margin-top: var(--spacing-3);
  font-size: var(--font-size-lg);
  font-family: "SimSun", "Songti SC", serif;
  color: var(--color-primary);
  opacity: 0;
  transform: translateY(10px);
  transition: all 0.4s ease-out;
}

.handwritten.show {
  opacity: 1;
  transform: translateY(0);
  animation: writing 1.5s ease-out forwards;
}

@keyframes writing {
  0% {
    opacity: 0;
    letter-spacing: 2px;
  }
  50% {
    opacity: 1;
  }
  100% {
    opacity: 1;
    letter-spacing: 1px;
  }
}

/* Work Order Info */
.workorder-info {
  background: var(--color-background);
  border-radius: var(--radius-lg);
  padding: var(--spacing-5);
  margin-bottom: var(--spacing-5);
  text-align: left;
}

.info-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-4);
  padding-bottom: var(--spacing-3);
  border-bottom: 1px dashed var(--color-border);
}

.info-header h3 {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-text-primary);
}

.order-id {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-family: var(--font-family-mono);
}

.info-details {
  margin-bottom: var(--spacing-4);
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: var(--spacing-2) 0;
}

.detail-row .label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.detail-row .value {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-primary);
}

.craft-params h4 {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-2);
}

.param-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-2);
}

.param-tag {
  font-size: var(--font-size-xs);
  padding: var(--spacing-1) var(--spacing-3);
  background: var(--color-bg2);
  color: var(--color-primary-dark);
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border);
}

/* Action Buttons */
.workorder-actions {
  display: flex;
  gap: var(--spacing-3);
  justify-content: center;
}

.workorder-actions .el-button {
  flex: 1;
  border-radius: var(--radius-full);
}

.workorder-actions .el-button:first-child {
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
}

.workorder-actions .el-button:first-child:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.workorder-actions .el-button:last-child {
  background: var(--color-primary);
  border-color: var(--color-primary);
}

.workorder-actions .el-button:last-child:hover {
  background: var(--color-primary-dark);
  border-color: var(--color-primary-dark);
}
</style>

<style>
/* Global dialog styles */
.workorder-dialog .el-dialog {
  border-radius: var(--radius-2xl);
  overflow: hidden;
}

.workorder-dialog .el-dialog__header {
  display: none;
}

.workorder-dialog .el-dialog__body {
  padding: 0;
}
</style>
