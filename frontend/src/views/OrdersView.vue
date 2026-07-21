<template>
  <div class="orders-page">
    <header class="page-header">
      <h1 class="page-title">我的订单</h1>
      <el-button @click="router.push('/design')" type="primary">
        新建设计
      </el-button>
    </header>

    <!-- Status Filter -->
    <div class="filter-bar">
      <el-radio-group v-model="statusFilter" size="default">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="pending">待确认</el-radio-button>
        <el-radio-button value="producing">制作中</el-radio-button>
        <el-radio-button value="completed">已完成</el-radio-button>
        <el-radio-button value="shipped">已发货</el-radio-button>
      </el-radio-group>
    </div>

    <!-- Orders List -->
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="orders.length === 0" class="empty-state">
      <el-empty description="暂无订单" />
      <el-button type="primary" @click="router.push('/design')">
        开始第一个设计
      </el-button>
    </div>

    <div v-else class="orders-list">
      <div
        v-for="order in orders"
        :key="order.order_id"
        class="order-card"
        @click="viewOrderDetail(order.order_id)"
      >
        <div class="order-status">
          <el-tag :color="getStatusColor(order.status)" :style="{ color: '#fff' }">
            {{ order.status_label }}
          </el-tag>
        </div>

        <div class="order-info">
          <div class="order-id">订单号: {{ order.order_id.slice(0, 8) }}...</div>
          <div class="order-time">{{ formatDate(order.created_at) }}</div>
        </div>

        <div class="order-price">
          <span class="price">¥{{ order.total_price.toFixed(2) }}</span>
        </div>

        <div class="order-actions">
          <el-button
            v-if="canCancel(order.status)"
            size="small"
            @click.stop="handleCancel(order.order_id)"
          >
            取消订单
          </el-button>
          <el-button
            v-if="order.status === 'pending'"
            size="small"
            type="primary"
            @click.stop="handlePay(order.order_id)"
          >
            立即支付
          </el-button>
          <el-button size="small" @click.stop="viewOrderDetail(order.order_id)">
            查看详情
          </el-button>
        </div>
      </div>
    </div>

    <!-- Order Detail Dialog -->
    <el-dialog
      v-model="detailVisible"
      title="订单详情"
      width="600px"
      :close-on-click-modal="false"
    >
      <div v-if="currentOrder" class="order-detail">
        <div class="detail-section">
          <h4>订单信息</h4>
          <div class="detail-row">
            <span class="label">订单号:</span>
            <span class="value">{{ currentOrder.order.order_id }}</span>
          </div>
          <div class="detail-row">
            <span class="label">总价:</span>
            <span class="value price">¥{{ currentOrder.order.total_price.toFixed(2) }}</span>
          </div>
          <div class="detail-row">
            <span class="label">收货地址:</span>
            <span class="value">{{ currentOrder.order.shipping_address || '未填写' }}</span>
          </div>
        </div>

        <div class="detail-section">
          <h4>订单状态</h4>
          <div class="timeline">
            <div
              v-for="(item, index) in currentOrder.timeline"
              :key="index"
              class="timeline-item"
            >
              <div class="timeline-dot" :style="{ backgroundColor: item.color }"></div>
              <div class="timeline-content">
                <div class="timeline-label">{{ item.label }}</div>
                <div v-if="item.reason" class="timeline-reason">{{ item.reason }}</div>
                <div class="timeline-time">{{ formatDate(item.created_at) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button
          v-if="currentOrder?.can_cancel"
          type="danger"
          @click="handleCancel(currentOrder.order.order_id)"
        >
          取消订单
        </el-button>
      </template>
    </el-dialog>

    <!-- Cancel Dialog -->
    <el-dialog
      v-model="cancelVisible"
      title="取消订单"
      width="400px"
    >
      <el-form>
        <el-form-item label="取消原因">
          <el-input
            v-model="cancelReason"
            type="textarea"
            :rows="3"
            placeholder="请输入取消原因（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelVisible = false">返回</el-button>
        <el-button type="danger" @click="confirmCancel">确认取消</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

interface Order {
  order_id: string
  user_id: string
  session_id: string
  option_id: string
  studio_id: string | null
  status: string
  status_label: string
  total_price: number
  shipping_address: string
  created_at: string
  updated_at: string
}

interface OrderDetail {
  order: Order
  timeline: Array<{
    status: string
    label: string
    color: string
    reason: string
    operator: string
    created_at: string
  }>
  can_cancel: boolean
  can_refund: boolean
}

const router = useRouter()

const orders = ref<Order[]>([])
const loading = ref(false)
const statusFilter = ref('')
const detailVisible = ref(false)
const cancelVisible = ref(false)
const currentOrder = ref<OrderDetail | null>(null)
const cancelingOrderId = ref('')
const cancelReason = ref('')

// 走陶语色板：墨绿主推进 / 陶土橙制作 / 玉青完成 / 金箔预警 / 胭脂红错
const statusColors: Record<string, string> = {
  pending:          'var(--color-text-tertiary)',
  confirmed:        'var(--color-primary)',
  dispatched:       'var(--color-primary-light)',
  producing:        'var(--color-accent)',
  glazing:          'var(--color-accent)',
  firing:           'var(--color-accent-dark)',
  cooling:          'var(--color-text-secondary)',
  qc:               'var(--color-warning)',
  completed:        'var(--color-success)',
  shipping_pending: 'var(--color-primary-light)',
  shipped:          'var(--color-primary)',
  delivered:        'var(--color-success)',
  cancelled:        'var(--color-text-tertiary)',
  refunding:        'var(--color-warning)',
  refunded:         'var(--color-text-tertiary)'
}

function getStatusColor(status: string): string {
  return statusColors[status] || 'var(--color-text-tertiary)'
}

function canCancel(status: string): boolean {
  const noCancel = ['delivered', 'refunded', 'cancelled', 'refunding']
  return !noCancel.includes(status)
}

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function fetchOrders() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (statusFilter.value) {
      params.set('status_filter', statusFilter.value)
    }

    const response = await fetch(`/api/v1/orders?${params}`, {
      credentials: 'include'  // cookie 自动携带 token
    })

    if (!response.ok) throw new Error('Failed to fetch orders')

    const data = await response.json()
    orders.value = data.orders
  } catch (error) {
    console.error('Fetch orders error:', error)
    ElMessage.error('获取订单列表失败')
  } finally {
    loading.value = false
  }
}

async function viewOrderDetail(orderId: string) {
  try {
    const response = await fetch(`/api/v1/orders/${orderId}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    })

    if (!response.ok) throw new Error('Failed to fetch order detail')

    const data = await response.json()
    currentOrder.value = data
    detailVisible.value = true
  } catch (error) {
    console.error('Fetch order detail error:', error)
    ElMessage.error('获取订单详情失败')
  }
}

function handleCancel(orderId: string) {
  cancelingOrderId.value = orderId
  cancelReason.value = ''
  cancelVisible.value = true
}

async function confirmCancel() {
  try {
    const response = await fetch(
      `/api/v1/orders/${cancelingOrderId.value}/cancel?reason=${encodeURIComponent(cancelReason.value)}`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      }
    )

    if (!response.ok) throw new Error('Failed to cancel order')

    ElMessage.success('订单已取消')
    cancelVisible.value = false
    detailVisible.value = false
    await fetchOrders()
  } catch (error) {
    console.error('Cancel order error:', error)
    ElMessage.error('取消订单失败')
  }
}

async function handlePay(orderId: string) {
  try {
    await ElMessageBox.confirm('确认支付此订单？', '支付确认', {
      confirmButtonText: '确认支付',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const response = await fetch(`/api/v1/orders/${orderId}/pay`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    })

    if (!response.ok) throw new Error('Failed to pay order')

    ElMessage.success('支付成功')
    await fetchOrders()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Pay order error:', error)
      ElMessage.error('支付失败')
    }
  }
}

watch(statusFilter, () => {
  fetchOrders()
})

onMounted(() => {
  fetchOrders()
})
</script>

<style scoped>
.orders-page {
  max-width: 900px;
  margin: 0 auto;
  padding: var(--spacing-8) var(--spacing-6);
  min-height: 100vh;
  background: var(--color-background);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-6);
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
}

.page-header :deep(.el-button) {
  border-radius: var(--radius-full);
  padding: 10px 20px;
}

.filter-bar :deep(.el-radio-button__inner) {
  border-radius: var(--radius-full);
  margin: 0 var(--spacing-1);
}

.filter-bar :deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-radius: var(--radius-full);
}

.empty-state {
  text-align: center;
  padding: var(--spacing-12);
}

.orders-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.order-card {
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  padding: var(--spacing-5);
  display: flex;
  align-items: center;
  gap: var(--spacing-5);
  cursor: pointer;
  transition: all var(--transition-normal);
  border: 1px solid var(--color-border);
}

.order-card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
  border-color: var(--color-primary);
}

.order-status :deep(.el-tag) {
  border-radius: var(--radius-full);
  padding: 4px 12px;
  font-weight: 500;
}

.order-info {
  flex: 1;
}

.order-id {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.order-time {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  margin-top: var(--spacing-1);
}

.order-price {
  text-align: right;
}

.order-price .price {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-primary);
}

.order-actions {
  display: flex;
  gap: var(--spacing-2);
}

.order-actions :deep(.el-button) {
  border-radius: var(--radius-full);
  padding: 6px 14px;
  font-size: var(--font-size-sm);
}

/* Detail Dialog */
.order-detail {
  padding: var(--spacing-2) 0;
}

.detail-section {
  margin-bottom: var(--spacing-6);
}

.detail-section h4 {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-3);
  padding-bottom: var(--spacing-2);
  border-bottom: 1px solid var(--color-border);
}

.detail-row {
  display: flex;
  padding: var(--spacing-2) 0;
}

.detail-row .label {
  width: 100px;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.detail-row .value {
  flex: 1;
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.detail-row .value.price {
  color: var(--color-primary);
  font-weight: 700;
}

/* Timeline */
.timeline {
  position: relative;
  padding-left: var(--spacing-6);
}

.timeline::before {
  content: '';
  position: absolute;
  left: 6px;
  top: 8px;
  bottom: 8px;
  width: 2px;
  background: var(--color-border);
}

.timeline-item {
  position: relative;
  padding-bottom: var(--spacing-4);
}

.timeline-item:last-child {
  padding-bottom: 0;
}

.timeline-dot {
  position: absolute;
  left: -22px;
  top: 4px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid var(--color-surface);
}

.timeline-label {
  font-weight: 500;
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.timeline-reason {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-top: var(--spacing-1);
}

.timeline-time {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-top: var(--spacing-1);
}

/* Dialog overrides */
:deep(.el-dialog) {
  border-radius: var(--radius-2xl);
}

:deep(.el-dialog__header) {
  padding: var(--spacing-5) var(--spacing-6);
  border-bottom: 1px solid var(--color-border);
}

:deep(.el-dialog__title) {
  font-weight: 600;
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
}

:deep(.el-dialog__body) {
  padding: var(--spacing-6);
}

:deep(.el-dialog__footer) {
  padding: var(--spacing-4) var(--spacing-6);
  border-top: 1px solid var(--color-border);
}

:deep(.el-dialog__footer .el-button) {
  border-radius: var(--radius-full);
  padding: 10px 20px;
}
</style>
