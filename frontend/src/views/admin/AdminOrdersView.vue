<template>
  <div class="admin-page">
    <AdminNav />

    <div class="admin-content">
      <h1 class="page-title">订单管理</h1>

      <div class="filter-bar">
        <el-radio-group v-model="statusFilter" @change="fetchOrders">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="pending">待确认</el-radio-button>
          <el-radio-button value="dispatched">已派单</el-radio-button>
          <el-radio-button value="producing">制作中</el-radio-button>
          <el-radio-button value="completed">已完成</el-radio-button>
          <el-radio-button value="shipped">已发货</el-radio-button>
          <el-radio-button value="delivered">已签收</el-radio-button>
        </el-radio-group>
      </div>

      <div v-if="loading" class="loading-container">
        <el-skeleton :rows="5" animated />
      </div>

      <el-empty v-else-if="orders.length === 0" description="暂无订单" />

      <el-table v-else :data="orders" style="width: 100%" stripe>
        <el-table-column label="订单号" width="120">
          <template #default="{ row }">
            <span class="mono">{{ row.order_id.slice(0, 8) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status_label" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :color="row.status_color" effect="dark" style="border: none; color: #fff">
              {{ row.status_label || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="金额" width="120">
          <template #default="{ row }">¥{{ row.total_price?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="工作室" min-width="120">
          <template #default="{ row }">{{ row.studio_id ? row.studio_id.slice(0, 8) : '未派单' }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { adminApi } from '@/api/modules'
import AdminNav from './AdminNav.vue'

interface AdminOrder {
  order_id: string
  status: string
  status_label?: string
  status_color?: string
  total_price: number
  studio_id: string | null
  created_at: string
}

const orders = ref<AdminOrder[]>([])
const loading = ref(false)
const statusFilter = ref('')

function formatDate(s: string): string {
  if (!s) return ''
  return new Date(s).toLocaleString('zh-CN')
}

async function fetchOrders() {
  loading.value = true
  try {
    const { data } = await adminApi.listOrders(statusFilter.value || undefined)
    // 后端返回 { orders: [...], total } 或直接数组，做兼容
    orders.value = Array.isArray(data) ? data : data.orders || []
  } catch (e) {
    /* 拦截器已提示 */
  } finally {
    loading.value = false
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
  max-width: 1100px;
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
  margin-bottom: 20px;
}

.loading-container {
  padding: 40px 0;
}

.mono {
  font-family: monospace;
  font-size: 13px;
}
</style>
