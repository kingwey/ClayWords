<template>
  <div class="admin-page">
    <AdminNav />

    <div class="admin-content">
      <h1 class="page-title">工作室管理</h1>

      <el-tabs v-model="activeTab" @tab-change="onTabChange">
        <el-tab-pane label="待审核" name="pending" />
        <el-tab-pane label="全部工作室" name="all" />
      </el-tabs>

      <div v-if="loading" class="loading-container">
        <el-skeleton :rows="4" animated />
      </div>

      <el-empty v-else-if="studios.length === 0" description="暂无数据" />

      <el-table v-else :data="studios" style="width: 100%" stripe>
        <el-table-column prop="name" label="工作室" min-width="140" />
        <el-table-column prop="location" label="所在地" width="100" />
        <el-table-column label="专长" min-width="160">
          <template #default="{ row }">
            <el-tag v-for="s in row.specialties" :key="s" size="small" style="margin: 2px">
              {{ s }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="capacity" label="产能" width="80" />
        <el-table-column prop="rating" label="评分" width="80">
          <template #default="{ row }">{{ row.rating?.toFixed(1) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button type="success" size="small" @click="openApprove(row)">通过</el-button>
              <el-button type="danger" size="small" @click="openReject(row)">拒绝</el-button>
            </template>
            <span v-else class="text-muted">—</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 通过弹窗 -->
    <el-dialog v-model="approveVisible" title="审核通过" width="420px">
      <el-form label-width="100px">
        <el-form-item label="工作室">{{ activeStudio?.name }}</el-form-item>
        <el-form-item label="调整产能">
          <el-input-number v-model="adjustedCapacity" :min="1" :max="100" />
          <span class="hint">留空则使用申请值</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="approveVisible = false">取消</el-button>
        <el-button type="success" @click="confirmApprove">确认通过</el-button>
      </template>
    </el-dialog>

    <!-- 拒绝弹窗 -->
    <el-dialog v-model="rejectVisible" title="审核拒绝" width="420px">
      <el-form label-width="100px">
        <el-form-item label="工作室">{{ activeStudio?.name }}</el-form-item>
        <el-form-item label="拒绝原因" required>
          <el-input v-model="rejectReason" type="textarea" :rows="3" placeholder="请填写拒绝原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmReject">确认拒绝</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { adminApi } from '@/api/modules'
import AdminNav from './AdminNav.vue'
import type { StudioListItem } from '@/types'

const activeTab = ref('pending')
const studios = ref<StudioListItem[]>([])
const loading = ref(false)

const approveVisible = ref(false)
const rejectVisible = ref(false)
const activeStudio = ref<StudioListItem | null>(null)
const adjustedCapacity = ref<number | undefined>(undefined)
const rejectReason = ref('')

const STATUS_LABELS: Record<string, string> = {
  pending: '待审核',
  active: '已激活',
  approved: '已通过',
  rejected: '已拒绝',
  suspended: '已暂停'
}

function statusLabel(s: string): string {
  return STATUS_LABELS[s] || s
}

function statusType(s: string): string {
  const map: Record<string, string> = {
    pending: 'warning',
    active: 'success',
    approved: 'success',
    rejected: 'danger',
    suspended: 'info'
  }
  return map[s] || 'info'
}

async function fetchStudios() {
  loading.value = true
  try {
    const { data } =
      activeTab.value === 'pending'
        ? await adminApi.listPendingStudios()
        : await adminApi.listStudios()
    studios.value = data
  } catch (e) {
    /* 拦截器已提示 */
  } finally {
    loading.value = false
  }
}

function onTabChange() {
  fetchStudios()
}

function openApprove(studio: StudioListItem) {
  activeStudio.value = studio
  adjustedCapacity.value = undefined
  approveVisible.value = true
}

async function confirmApprove() {
  if (!activeStudio.value) return
  try {
    await adminApi.approveStudio(activeStudio.value.studio_id, {
      action: 'approve',
      adjusted_capacity: adjustedCapacity.value
    })
    ElMessage.success('已通过审核')
    approveVisible.value = false
    await fetchStudios()
  } catch (e) {
    /* 拦截器已提示 */
  }
}

function openReject(studio: StudioListItem) {
  activeStudio.value = studio
  rejectReason.value = ''
  rejectVisible.value = true
}

async function confirmReject() {
  if (!activeStudio.value) return
  if (!rejectReason.value.trim()) {
    ElMessage.warning('请填写拒绝原因')
    return
  }
  try {
    await adminApi.approveStudio(activeStudio.value.studio_id, {
      action: 'reject',
      reason: rejectReason.value
    })
    ElMessage.success('已拒绝')
    rejectVisible.value = false
    await fetchStudios()
  } catch (e) {
    /* 拦截器已提示 */
  }
}

onMounted(fetchStudios)
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

.loading-container {
  padding: 40px 0;
}

.hint {
  margin-left: 8px;
  font-size: 12px;
  color: var(--color-text-tertiary, #9ca3af);
}

.text-muted {
  color: var(--color-text-tertiary, #9ca3af);
}
</style>
