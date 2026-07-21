<template>
  <div class="admin-page">
    <AdminNav />

    <div class="admin-content">
      <h1 class="page-title">运营总览</h1>

      <!-- 指标卡 -->
      <div class="metric-grid">
        <el-card class="metric-card" shadow="hover">
          <div class="metric-value">{{ metrics.total_orders ?? '—' }}</div>
          <div class="metric-label">订单总数</div>
        </el-card>
        <el-card class="metric-card" shadow="hover">
          <div class="metric-value">{{ metrics.total_users ?? '—' }}</div>
          <div class="metric-label">用户总数</div>
        </el-card>
        <el-card class="metric-card" shadow="hover">
          <div class="metric-value">{{ pendingCount }}</div>
          <div class="metric-label">待审核工作室</div>
        </el-card>
        <el-card class="metric-card" shadow="hover">
          <div class="metric-value" :class="{ alarm: alerts.length > 0 }">
            {{ alerts.length }}
          </div>
          <div class="metric-label">活跃告警</div>
        </el-card>
      </div>

      <!-- 活跃告警 -->
      <el-card class="section" shadow="never">
        <template #header>
          <div class="section-header">
            <span class="section-title">活跃告警</span>
            <el-button text @click="fetchAlerts">刷新</el-button>
          </div>
        </template>
        <el-empty v-if="alerts.length === 0" description="暂无告警" :image-size="80" />
        <el-table v-else :data="alerts" style="width: 100%">
          <el-table-column prop="severity" label="级别" width="100">
            <template #default="{ row }">
              <el-tag :type="severityType(row.severity)" effect="dark">
                {{ row.severity }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="rule_name" label="规则" width="180" />
          <el-table-column prop="message" label="描述" />
          <el-table-column prop="triggered_at" label="触发时间" width="180">
            <template #default="{ row }">{{ formatDate(row.triggered_at) }}</template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 快捷入口 -->
      <div class="quick-links">
        <el-button type="primary" @click="router.push('/admin/studios')">
          工作室管理
        </el-button>
        <el-button @click="router.push('/admin/orders')">订单管理</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { adminApi } from '@/api/modules'
import AdminNav from './AdminNav.vue'
import type { AlertItem } from '@/types'

const router = useRouter()

const metrics = ref<Record<string, any>>({})
const alerts = ref<AlertItem[]>([])
const pendingCount = ref(0)

function severityType(s: string): string {
  const map: Record<string, string> = {
    critical: 'danger',
    warning: 'warning',
    info: 'info'
  }
  return map[s] || 'info'
}

function formatDate(s: string): string {
  if (!s) return ''
  return new Date(s).toLocaleString('zh-CN')
}

async function fetchMetrics() {
  try {
    const { data } = await adminApi.getMetrics()
    metrics.value = data
  } catch (e) {
    /* metrics 接口可能未配置，静默 */
  }
}

async function fetchAlerts() {
  try {
    const { data } = await adminApi.listActiveAlerts()
    alerts.value = data
  } catch (e) {
    /* 拦截器已提示 */
  }
}

async function fetchPending() {
  try {
    const { data } = await adminApi.listPendingStudios()
    pendingCount.value = data.length
  } catch (e) {
    /* 拦截器已提示 */
  }
}

onMounted(() => {
  fetchMetrics()
  fetchAlerts()
  fetchPending()
})
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
  margin: 0 0 24px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.metric-card {
  text-align: center;
  border-radius: 12px;
}

.metric-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--color-primary, #2c3e2d);
}

.metric-value.alarm {
  color: var(--color-danger, #c0392b);
}

.metric-label {
  color: var(--color-text-secondary, #6b7280);
  font-size: 14px;
  margin-top: 6px;
}

.section {
  margin-bottom: 24px;
  border-radius: 12px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  font-weight: 600;
  color: var(--color-text-primary, #2c3e2d);
}

.quick-links {
  display: flex;
  gap: 12px;
}

@media (max-width: 768px) {
  .metric-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
