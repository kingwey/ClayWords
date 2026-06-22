<template>
  <div class="detail-page">
    <StudioNav />

    <div class="detail-content-wrap">
      <header class="page-header">
        <el-button text @click="router.back()">&larr; 返回</el-button>
        <h1 class="page-title">订单详情</h1>
      </header>

      <div v-if="loading" class="loading-container">
        <el-skeleton :rows="6" animated />
      </div>

      <div v-else-if="order" class="detail-content">
      <!-- 状态卡 -->
      <el-card class="section">
        <div class="status-row">
          <el-tag :type="statusTagType(order.status)" effect="dark" size="large">
            {{ statusLabel(order.status) }}
          </el-tag>
          <span class="order-id">订单号：{{ order.order_id }}</span>
        </div>
      </el-card>

      <!-- 设计参数 -->
      <el-card class="section">
        <template #header><span class="section-title">设计信息</span></template>
        <div class="design-info">
          <el-image
            v-if="order.thumbnail_url"
            :src="order.thumbnail_url"
            fit="cover"
            class="design-thumb"
          />
          <div class="design-meta">
            <div class="design-name">{{ order.design_name || '自定义设计' }}</div>
            <div class="design-desc">{{ order.design_description || '暂无描述' }}</div>
          </div>
        </div>
      </el-card>

      <!-- 工艺校验 -->
      <el-card class="section">
        <template #header><span class="section-title">工艺校验</span></template>
        <div class="craft-row">
          <el-tag :type="order.craft_check?.passed ? 'success' : 'danger'">
            {{ order.craft_check?.passed ? '校验通过' : '校验未通过' }}
          </el-tag>
          <el-tag v-if="order.craft_check?.auto_fixed" type="warning" style="margin-left: 8px">
            已自动修复
          </el-tag>
        </div>
        <ul v-if="order.craft_check?.issues?.length" class="issue-list">
          <li v-for="(issue, i) in order.craft_check.issues" :key="i">{{ issue }}</li>
        </ul>
      </el-card>

      <!-- 订单信息 -->
      <el-card class="section">
        <template #header><span class="section-title">订单信息</span></template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="总价">¥{{ order.total_price.toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="预计工期">{{ order.estimated_days }} 天</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(order.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDate(order.updated_at) }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 操作 -->
      <div class="actions">
        <template v-if="order.status === 'dispatched'">
          <el-button type="primary" @click="goBack">返回列表处理接单</el-button>
        </template>
        <template v-else-if="order.status === 'producing'">
          <el-button type="success" @click="handleComplete">标记完成</el-button>
        </template>
      </div>
    </div>

    <el-empty v-else description="订单不存在" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { studioApi } from '@/api/modules'
import StudioNav from './StudioNav.vue'
import type { StudioOrderDetail } from '@/types'

const route = useRoute()
const router = useRouter()

const order = ref<StudioOrderDetail | null>(null)
const loading = ref(false)

const STATUS_LABELS: Record<string, string> = {
  dispatched: '待接单',
  producing: '制作中',
  completed: '已完成',
  shipped: '已发货',
  delivered: '已签收'
}

function statusLabel(s: string): string {
  return STATUS_LABELS[s] || s
}

function statusTagType(s: string): string {
  const map: Record<string, string> = {
    dispatched: 'warning',
    producing: 'primary',
    completed: 'success',
    shipped: 'info',
    delivered: 'success'
  }
  return map[s] || 'info'
}

function formatDate(s: string): string {
  if (!s) return ''
  return new Date(s).toLocaleString('zh-CN')
}

async function fetchDetail() {
  loading.value = true
  try {
    const orderId = route.params.orderId as string
    const { data } = await studioApi.getOrder(orderId)
    order.value = data
  } catch (e) {
    /* 拦截器已提示 */
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push('/studio')
}

async function handleComplete() {
  if (!order.value) return
  try {
    await ElMessageBox.confirm('确认该订单已制作完成？', '标记完成', {
      confirmButtonText: '确认',
      cancelButtonText: '取消'
    })
    await studioApi.completeOrder(order.value.order_id)
    ElMessage.success('已标记完成')
    await fetchDetail()
  } catch (e) {
    if (e !== 'cancel') {
      /* 拦截器已提示 */
    }
  }
}

onMounted(fetchDetail)
</script>

<style scoped>
.detail-page {
  min-height: 100vh;
  background: var(--color-background, #f5f5f0);
}

.detail-content-wrap {
  max-width: 800px;
  margin: 0 auto;
  padding: var(--spacing-8, 32px) var(--spacing-6, 24px);
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: var(--spacing-6, 24px);
}

.page-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--color-text-primary, #2c3e2d);
  margin: 0;
}

.section {
  margin-bottom: 16px;
  border-radius: 12px;
}

.section-title {
  font-weight: 600;
  color: var(--color-text-primary, #2c3e2d);
}

.status-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.order-id {
  color: var(--color-text-tertiary, #9ca3af);
  font-family: monospace;
  font-size: 13px;
}

.craft-row {
  margin-bottom: 8px;
}
.issue-list {
  margin: 8px 0 0;
  padding-left: 20px;
  color: var(--color-text-secondary, #6b7280);
  font-size: 13px;
}

.actions {
  margin-top: 24px;
  text-align: center;
}

.loading-container {
  padding: 40px 0;
}

.design-info {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.design-thumb {
  width: 96px;
  height: 96px;
  border-radius: 8px;
  flex-shrink: 0;
  background: var(--color-bg2, #ececec);
}

.design-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary, #2c3e2d);
  margin-bottom: 6px;
}

.design-desc {
  font-size: 13px;
  color: var(--color-text-secondary, #6b7280);
  line-height: 1.6;
}
</style>
