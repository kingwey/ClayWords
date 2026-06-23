<template>
  <div class="profile-page">
    <header class="page-header">
      <h1 class="page-title">个人资料</h1>
      <el-button @click="router.back()">返回</el-button>
    </header>

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="4" animated />
    </div>

    <div v-else class="profile-card">
      <!-- 头像 + 昵称概要 -->
      <div class="profile-summary">
        <span class="avatar">{{ avatarLetter }}</span>
        <div class="summary-text">
          <div class="display-name">{{ auth.displayName || '未设置昵称' }}</div>
          <span class="role-tag">{{ auth.roleLabel }}</span>
        </div>
      </div>

      <el-divider />

      <!-- 资料表单 -->
      <el-form label-width="88px" class="profile-form">
        <el-form-item label="昵称">
          <el-input
            v-model="nicknameInput"
            placeholder="留空则显示脱敏手机号"
            maxlength="50"
            show-word-limit
            clearable
            style="max-width: 360px"
          />
        </el-form-item>

        <el-form-item label="手机号">
          <span class="readonly-value">{{ auth.phone || '—' }}</span>
        </el-form-item>

        <el-form-item label="角色">
          <span class="readonly-value">{{ auth.roleLabel || '—' }}</span>
        </el-form-item>

        <el-form-item label="用户 ID">
          <span class="readonly-value mono">{{ auth.userId || '—' }}</span>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="saving"
            :disabled="!dirty"
            @click="save"
          >
            保存修改
          </el-button>
          <el-button :disabled="!dirty" @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const loading = ref(true)
const saving = ref(false)
const nicknameInput = ref('')

const dirty = computed(() => nicknameInput.value.trim() !== (auth.nickname || ''))

const avatarLetter = computed(() => {
  const name = auth.displayName
  if (!name) return '陶'
  const digits = auth.phone.replace(/\D/g, '')
  if (auth.nickname) return auth.nickname.slice(0, 1).toUpperCase()
  if (digits.length > 0) return digits.slice(-1)
  return name.slice(0, 1).toUpperCase()
})

function reset() {
  nicknameInput.value = auth.nickname || ''
}

async function save() {
  saving.value = true
  try {
    await auth.updateNickname(nicknameInput.value.trim())
    ElMessage.success(nicknameInput.value.trim() ? '昵称已更新' : '昵称已清空')
    reset()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '更新失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await auth.fetchUser(true)
  reset()
  loading.value = false
})
</script>

<style scoped>
.profile-page {
  max-width: 760px;
  margin: 0 auto;
  padding: var(--spacing-8, 32px) var(--spacing-6, 24px);
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-6, 24px);
}

.page-title {
  font-family: var(--font-family-display);
  font-size: var(--font-size-2xl, 24px);
  font-weight: 700;
  color: var(--color-primary, #2c3e2d);
  letter-spacing: 2px;
  margin: 0;
}

.profile-card {
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border-light, #eee);
  border-radius: var(--radius-2xl, 16px);
  box-shadow: var(--shadow-sm);
  padding: var(--spacing-8, 32px);
}

.profile-summary {
  display: flex;
  align-items: center;
  gap: 16px;
}

.profile-summary .avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  color: #fff;
  font-size: 22px;
  font-weight: 600;
  font-family: var(--font-family-mono);
}

.summary-text {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.display-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary, #2c3e2d);
}

.role-tag {
  align-self: flex-start;
  font-size: 12px;
  padding: 2px 10px;
  border-radius: var(--radius-full, 999px);
  background: rgba(201, 123, 90, 0.12);
  color: var(--color-accent, #c97b5a);
  border: 1px solid rgba(201, 123, 90, 0.25);
}

.profile-form {
  margin-top: 8px;
}

.readonly-value {
  color: var(--color-text-secondary, #606266);
  font-size: 14px;
}

.readonly-value.mono {
  font-family: monospace;
  font-size: 13px;
}

.loading-container {
  padding: var(--spacing-8, 32px);
}
</style>
