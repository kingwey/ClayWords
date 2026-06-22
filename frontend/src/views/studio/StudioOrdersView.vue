<template>
  <div class="studio-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">工作室工作台</h1>
        <p class="page-sub">管理派发给您的订单</p>
      </div>
      <el-button @click="handleLogout">退出登录</el-button>
    </header>

    <!-- 状态筛选 -->
    <div class="filter-bar">
      <el-radio-group v-model="statusFilter" size="default">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="dispatched">待接单</el-radio-button>
        <el-radio-button value="producing">制作中</el-radio-button>
        <el-radio-button value="completed">已完成</el-radio-button>
        <el-radio-button value="shipped">已发货</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 订单列表 -->
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="orders.length === 0" class="empty-state">
      <el-empty description="暂无订单" />
    </div>

    <div v-else class="orders-list">
      <el-card
        v-for="order in orders"
        :key="order.order_id"
        class="order-card"
        shadow="hover"
        @click="goDetail(order.order_id)"
      >
        <div class="card-top">
          <el-tag :type="statusTagType(order.status)" effect="dark">
            {{ statusLabel(order.status) }}
          </el-tag>
          <span class="order-id">#{{ order.order_id.slice(0, 8) }}</span>
        </div>

        <div class="card-body">
          <div class="design-summary">
            <span class="label">设计：</span>
            <span>{{ order.design_name || '自定义设计' }}</span>
          </div>
          <div class="meta-row">
            <span>¥{{ order.total_price.toFixed(2) }}</span>
            <span>工期 {{ order.estimated_days }} 天</span>
            <span>{{ formatDate(order.created_at) }}</span>
          </div>
        </div>

        <div class="card-actions" @click.stop>
          <template v-if="order.status === 'dispatched'">
            <el-button type="primary" size="small" @click="openAccept(order.order_id)">
              接单
            </el-button>
            <el-button size="small" @click="openReject(order.order_id)">拒单</el-button>
          </template>
          <el-button
            v-else-if="order.status === 'producing'"
            type="success"
            size="small"
            @click="handleComplete(order.order_id)"
          >
            标记完成
          </el-button>
          <el-button
            v-else-if="order.status === 'completed'"
            type="primary"
            size="small"
            @click="openShip(order.order_id)"
          >
            发货
          </el-button>
          <el-button size="small" @click="goDetail(order.order_id)">详情</el-button>
        </div>
      </el-card>
    </div>

    <!-- 接单弹窗 -->
    <el-dialog v-model="acceptVisible" title="确认接单" width="420px">
      <el-form label-width="100px">
        <el-form-item label="预计完成">
          <el-date-picker
            v-model="acceptForm.date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="acceptForm.notes" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="acceptVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmAccept">确认接单</el-button>
      </template>
    </el-dialog>

    <!-- 拒单弹窗 -->
    <el-dialog v-model="rejectVisible" title="拒绝订单" width="420px">
      <el-form label-width="100px">
        <el-form-item label="原因分类" required>
          <el-select v-model="rejectForm.category" placeholder="请选择" style="width: 100%">
            <el-option label="产能不足" value="capacity" />
            <el-option label="工艺不符" value="craft" />
            <el-option label="价格不符" value="price" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="详细原因" required>
          <el-input
            v-model="rejectForm.reason"
            type="textarea"
            :rows="3"
            placeholder="请填写至少 5 个字"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmReject">确认拒单</el-button>
      </template>
    </el-dialog>

    <!-- 发货弹窗 -->
    <el-dialog v-model="shipVisible" title="订单发货" width="420px">
      <el-form label-width="100px">
        <el-form-item label="快递公司" required>
          <el-select v-model="shipForm.carrier" placeholder="请选择" style="width: 100%">
            <el-option label="顺丰速运" value="顺丰速运" />
            <el-option label="圆通速递" value="圆通速递" />
            <el-option label="中通快递" value="中通快递" />
            <el-option label="韵达快递" value="韵达快递" />
          </el-select>
        </el-form-item>
        <el-form-item label="快递单号" required>
          <el-input v-model="shipForm.tracking_number" placeholder="请输入快递单号" />
        </el-form-item>
        <el-form-item label="预计送达">
          <el-date-picker
            v-model="shipForm.estimated_delivery_date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="shipForm.notes" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="shipVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmShip">确认发货</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { studioApi } from '@/api/modules'
import { useAuthStore } from '@/stores/auth'
import type { StudioOrderSummary } from '@/types'

const router = useRouter()
const auth = useAuthStore()

const orders = ref<StudioOrderSummary[]>([])
const loading = ref(false)
const statusFilter = ref('')

const acceptVisible = ref(false)
const rejectVisible = ref(false)
const shipVisible = ref(false)
const activeOrderId = ref('')

const acceptForm = ref({ date: '', notes: '' })
const rejectForm = ref({ category: '', reason: '' })
const shipForm = ref({ carrier: '', tracking_number: '', estimated_delivery_date: '', notes: '' })

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
  return new Date(s).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function fetchOrders() {
  loading.value = true
  try {
    const { data } = await studioApi.listOrders(statusFilter.value || undefined)
    orders.value = data
  } catch (e) {
    // 拦截器已提示
  } finally {
    loading.value = false
  }
}

function goDetail(orderId: string) {
  router.push(`/studio/orders/${orderId}`)
}

function openAccept(orderId: string) {
  activeOrderId.value = orderId
  acceptForm.value = { date: '', notes: '' }
  acceptVisible.value = true
}

async function confirmAccept() {
  try {
    await studioApi.acceptOrder(activeOrderId.value, {
      estimated_completion_date: acceptForm.value.date || undefined,
      notes: acceptForm.value.notes || undefined
    })
    ElMessage.success('接单成功')
    acceptVisible.value = false
    await fetchOrders()
  } catch (e) {
    /* 拦截器已提示 */
  }
}

function openReject(orderId: string) {
  activeOrderId.value = orderId
  rejectForm.value = { category: '', reason: '' }
  rejectVisible.value = true
}

async function confirmReject() {
  if (!rejectForm.value.category) {
    ElMessage.warning('请选择原因分类')
    return
  }
  if (rejectForm.value.reason.trim().length < 5) {
    ElMessage.warning('详细原因至少 5 个字')
    return
  }
  try {
    await studioApi.rejectOrder(activeOrderId.value, {
      reason: rejectForm.value.reason,
      reason_category: rejectForm.value.category
    })
    ElMessage.success('已拒单，订单将重新派发')
    rejectVisible.value = false
    await fetchOrders()
  } catch (e) {
    /* 拦截器已提示 */
  }
}

async function handleComplete(orderId: string) {
  try {
    await ElMessageBox.confirm('确认该订单已制作完成？', '标记完成', {
      confirmButtonText: '确认',
      cancelButtonText: '取消'
    })
    await studioApi.completeOrder(orderId)
    ElMessage.success('已标记完成')
    await fetchOrders()
  } catch (e) {
    if (e !== 'cancel') {
      /* 拦截器已提示 */
    }
  }
}

function openShip(orderId: string) {
  activeOrderId.value = orderId
  shipForm.value = { carrier: '', tracking_number: '', estimated_delivery_date: '', notes: '' }
  shipVisible.value = true
}

async function confirmShip() {
  if (!shipForm.value.carrier || !shipForm.value.tracking_number) {
    ElMessage.warning('请填写快递公司和单号')
    return
  }
  try {
    await studioApi.shipOrder(activeOrderId.value, {
      carrier: shipForm.value.carrier,
      tracking_number: shipForm.value.tracking_number,
      estimated_delivery_date: shipForm.value.estimated_delivery_date || undefined,
      notes: shipForm.value.notes || undefined
    })
    ElMessage.success('发货成功')
    shipVisible.value = false
    await fetchOrders()
  } catch (e) {
    /* 拦截器已提示 */
  }
}

function handleLogout() {
  auth.clearAuth()
  router.push('/login')
}

watch(statusFilter, fetchOrders)
onMounted(fetchOrders)
</script>

<style scoped>
.studio-page {
  max-width: 960px;
  margin: 0 auto;
  padding: var(--spacing-8, 32px) var(--spacing-6, 24px);
  min-height: 100vh;
  background: var(--color-background, #f5f5f0);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--spacing-6, 24px);
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--color-text-primary, #2c3e2d);
  margin: 0;
}

.page-sub {
  color: var(--color-text-secondary, #6b7280);
  margin: 4px 0 0;
  font-size: 14px;
}

.filter-bar {
  margin-bottom: var(--spacing-5, 20px);
}

.orders-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.order-card {
  cursor: pointer;
  border-radius: 12px;
}

.card-top {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.order-id {
  color: var(--color-text-tertiary, #9ca3af);
  font-size: 13px;
  font-family: monospace;
}

.card-body {
  margin-bottom: 14px;
}

.design-summary {
  font-size: 15px;
  color: var(--color-text-primary, #2c3e2d);
  margin-bottom: 8px;
}

.design-summary .label {
  color: var(--color-text-secondary, #6b7280);
}

.meta-row {
  display: flex;
  gap: 18px;
  font-size: 13px;
  color: var(--color-text-secondary, #6b7280);
}

.card-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.empty-state,
.loading-container {
  padding: 60px 0;
  text-align: center;
}
</style>
