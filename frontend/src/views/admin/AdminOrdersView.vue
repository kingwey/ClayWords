<template>
  <div class="admin-page">
    <AdminNav />

    <div class="admin-content">
      <h1 class="page-title">订单管理</h1>

      <div class="filter-bar">
        <el-radio-group v-model="statusFilter" @change="onFilterChange">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="pending">待确认</el-radio-button>
          <el-radio-button value="confirmed">已确认</el-radio-button>
          <el-radio-button value="dispatched">已派单</el-radio-button>
          <el-radio-button value="producing">制作中</el-radio-button>
          <el-radio-button value="completed">已完成</el-radio-button>
          <el-radio-button value="shipped">已发货</el-radio-button>
          <el-radio-button value="delivered">已签收</el-radio-button>
          <el-radio-button value="cancelled">已取消</el-radio-button>
          <el-radio-button value="refunding">退款中</el-radio-button>
          <el-radio-button value="refunded">已退款</el-radio-button>
        </el-radio-group>

        <el-input
          v-model="keyword"
          placeholder="按 order_id / user_id 前缀搜索"
          clearable
          style="width: 280px; margin-left: 12px"
          @change="fetchOrders"
        />
      </div>

      <div v-if="loading" class="loading-container">
        <el-skeleton :rows="5" animated />
      </div>

      <el-empty v-else-if="orders.length === 0" description="暂无订单" />

      <el-table v-else :data="orders" style="width: 100%" stripe>
        <el-table-column label="订单号" width="110">
          <template #default="{ row }">
            <span class="mono link" @click="openDetail(row)">{{ row.order_id.slice(0, 8) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :color="row.status_color" effect="dark" style="border: none; color: #fff">
              {{ row.status_label || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="金额" width="100">
          <template #default="{ row }">¥{{ (row.total_price ?? 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="用户" min-width="110">
          <template #default="{ row }">
            <span class="mono">{{ row.user_id?.slice(0, 8) || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="工作室" min-width="110">
          <template #default="{ row }">
            <span class="mono">{{ row.studio_id ? row.studio_id.slice(0, 8) : '未派单' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              type="primary"
              link
              :disabled="!canRedispatch(row)"
              @click="onRedispatch(row)"
            >重派</el-button>
            <el-button
              size="small"
              type="warning"
              link
              :disabled="!row.can_cancel"
              @click="onCancel(row)"
            >取消</el-button>
            <el-button
              size="small"
              type="danger"
              link
              :disabled="!row.can_refund"
              @click="onRefund(row)"
            >退款</el-button>
            <el-button size="small" link @click="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="orders.length > 0" class="pager">
        <el-pagination
          background
          layout="total, prev, pager, next"
          :total="total"
          :page-size="limit"
          :current-page="page"
          @current-change="onPageChange"
        />
      </div>
    </div>

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="detailOpen"
      title="订单详情"
      direction="rtl"
      size="600px"
      destroy-on-close
    >
      <div v-if="!detailLoading && detail" class="detail">
        <h3>{{ detail.order.order_id.slice(0, 8) }}…</h3>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="状态">
            <el-tag :color="detail.order.status_color" effect="dark" style="border: none; color: #fff">
              {{ detail.order.status_label }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="金额">¥{{ (detail.order.total_price ?? 0).toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="用户">{{ detail.order.user_id }}</el-descriptions-item>
          <el-descriptions-item label="工作室">{{ detail.order.studio_id || '—' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(detail.order.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDate(detail.order.updated_at) }}</el-descriptions-item>
          <el-descriptions-item label="收货地址" :span="2">{{ detail.order.shipping_address || '—' }}</el-descriptions-item>
        </el-descriptions>

        <h4 style="margin-top: 24px">操作日志</h4>
        <el-timeline>
          <el-timeline-item
            v-for="(log, idx) in detail.logs"
            :key="idx"
            :timestamp="formatDate(log.created_at)"
            placement="top"
          >
            <p class="log-line">
              <span class="log-status">{{ log.from_status || '∅' }} → {{ log.to_status }}</span>
              <span class="log-operator">{{ log.operator }}</span>
            </p>
            <p v-if="log.reason" class="log-reason">{{ log.reason }}</p>
          </el-timeline-item>
        </el-timeline>
      </div>
      <el-skeleton v-else :rows="6" animated />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '@/api/modules'
import AdminNav from './AdminNav.vue'

interface AdminOrder {
  order_id: string
  user_id: string
  session_id: string
  option_id: string
  studio_id: string | null
  status: string
  status_label: string
  status_color: string
  total_price: number
  shipping_address: string
  created_at: string
  updated_at: string
  can_cancel: boolean
  can_refund: boolean
}

interface AdminLog {
  from_status: string | null
  to_status: string
  operator: string
  reason: string
  created_at: string
}

interface AdminOrderDetail {
  order: AdminOrder
  logs: AdminLog[]
}

const orders = ref<AdminOrder[]>([])
const total = ref(0)
const page = ref(1)
const limit = 20
const loading = ref(false)
const statusFilter = ref('')
const keyword = ref('')

const detailOpen = ref(false)
const detail = ref<AdminOrderDetail | null>(null)
const detailLoading = ref(false)

function formatDate(s: string): string {
  if (!s) return ''
  return new Date(s).toLocaleString('zh-CN')
}

// 重派的状态门槛: 只允许 pending/confirmed/dispatched (与后端一致)
function canRedispatch(row: AdminOrder): boolean {
  return ['pending', 'confirmed', 'dispatched'].includes(row.status)
}

async function fetchOrders() {
  loading.value = true
  try {
    const offset = (page.value - 1) * limit
    const { data } = await adminApi.listAllOrders({
      status_filter: statusFilter.value || undefined,
      keyword: keyword.value || undefined,
      limit,
      offset,
    })
    // 兼容: 老接口返回数组, 新接口返回 { orders, total, ... }
    if (Array.isArray(data)) {
      orders.value = data as AdminOrder[]
      total.value = data.length
    } else {
      orders.value = (data as any).orders || []
      total.value = (data as any).total || orders.value.length
    }
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  page.value = 1
  fetchOrders()
}

function onPageChange(p: number) {
  page.value = p
  fetchOrders()
}

async function openDetail(row: AdminOrder) {
  detailOpen.value = true
  detail.value = null
  detailLoading.value = true
  try {
    const { data } = await adminApi.getOrderDetail(row.order_id)
    detail.value = data as AdminOrderDetail
  } finally {
    detailLoading.value = false
  }
}

async function onCancel(row: AdminOrder) {
  try {
    const { value: reason } = await ElMessageBox.prompt(
      '请输入取消原因 (将记入审计日志)',
      `强制取消订单 ${row.order_id.slice(0, 8)}`,
      {
        confirmButtonText: '确认取消',
        cancelButtonText: '不取消',
        inputValidator: (v: string) => (v && v.trim().length >= 2) || '原因至少 2 字',
      }
    )
    await adminApi.cancelOrder(row.order_id, reason.trim())
    ElMessage.success('订单已取消')
    fetchOrders()
  } catch (e) {
    // 用户点了"不取消"会到这里, 不报错
  }
}

async function onRefund(row: AdminOrder) {
  try {
    const { value: reason } = await ElMessageBox.prompt(
      `订单金额 ¥${(row.total_price ?? 0).toFixed(2)}; 默认全额退款。请输入退款原因`,
      `退款 ${row.order_id.slice(0, 8)}`,
      {
        confirmButtonText: '提交退款',
        cancelButtonText: '取消',
        inputValidator: (v: string) => (v && v.trim().length >= 2) || '原因至少 2 字',
      }
    )
    await adminApi.refundOrder(row.order_id, { reason: reason.trim() })
    ElMessage.success('已进入退款流程')
    fetchOrders()
  } catch (e) {
    /* 取消即跳出 */
  }
}

async function onRedispatch(row: AdminOrder) {
  try {
    const { value: reason } = await ElMessageBox.prompt(
      '重派会释放当前工作室容量并重新跑派单器',
      `重派 ${row.order_id.slice(0, 8)}`,
      {
        confirmButtonText: '确认重派',
        cancelButtonText: '取消',
        inputValidator: (v: string) => (v && v.trim().length >= 2) || '原因至少 2 字',
      }
    )
    const { data } = await adminApi.redispatchOrder(row.order_id, reason.trim())
    const newStudio = (data as any)?.studio_id
    if (newStudio) {
      ElMessage.success(`已重派到 ${String(newStudio).slice(0, 8)}…`)
    } else {
      ElMessage.warning('重派完成但未匹配到合适工作室, 请检查工作室容量')
    }
    fetchOrders()
  } catch (e) {
    /* 取消即跳出 */
  }
}

onMounted(fetchOrders)
</script>

<style scoped>
.admin-page {
  min-height: 100vh;
  background: var(--color-background, #f5f5f0);
}

.admin-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--spacing-6, 24px);
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--color-text-primary, #2c3e2d);
  margin: 0 0 16px;
}

.filter-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.mono {
  font-family: monospace;
  font-size: 13px;
}

.link {
  cursor: pointer;
  color: #409eff;
}

.link:hover {
  text-decoration: underline;
}

.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.detail h3 {
  font-family: monospace;
  margin: 0 0 16px;
}

.detail h4 {
  font-size: 15px;
  color: var(--color-text-primary, #2c3e2d);
  margin-bottom: 8px;
}

.log-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 0;
  font-size: 13px;
}

.log-status {
  font-family: monospace;
  color: #2c3e2d;
}

.log-operator {
  color: #909399;
}

.log-reason {
  margin: 4px 0 0;
  font-size: 12px;
  color: #606266;
}
</style>
