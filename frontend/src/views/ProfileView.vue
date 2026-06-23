<template>
  <div class="profile-page">
    <header class="page-header">
      <h1 class="page-title">个人资料</h1>
      <el-button @click="router.back()">返回</el-button>
    </header>

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="6" animated />
    </div>

    <template v-else>
      <!-- 基本信息卡片 -->
      <div class="profile-card">
        <div class="card-head">
          <div class="profile-summary">
            <span class="avatar">{{ avatarLetter }}</span>
            <div class="summary-text">
              <div class="display-name">{{ auth.displayName || '未设置昵称' }}</div>
              <span class="role-tag">{{ auth.roleLabel }}</span>
            </div>
          </div>
          <el-button v-if="!editing" type="primary" plain @click="startEdit">
            编辑资料
          </el-button>
        </div>

        <el-divider />

        <!-- 只读模式 -->
        <el-descriptions v-if="!editing" :column="1" class="info-list">
          <el-descriptions-item label="昵称">
            {{ auth.nickname || '未设置' }}
          </el-descriptions-item>
          <el-descriptions-item label="手机号">
            {{ auth.phone || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="角色">
            {{ auth.roleLabel || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="用户 ID">
            <span class="mono">{{ auth.userId || '—' }}</span>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 编辑模式 -->
        <el-form v-else label-width="88px" class="profile-form">
          <el-form-item label="昵称">
            <el-input
              v-model="form.nickname"
              placeholder="留空则显示脱敏手机号"
              maxlength="50"
              show-word-limit
              clearable
              style="max-width: 360px"
            />
          </el-form-item>
          <el-form-item label="手机号">
            <el-input
              v-model="form.phone"
              placeholder="11 位手机号"
              maxlength="11"
              style="max-width: 360px"
            />
            <div class="field-hint">修改手机号后将作为新的登录凭证</div>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" @click="save">保存</el-button>
            <el-button @click="cancelEdit">取消</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 第三方账号绑定 -->
      <div class="profile-card">
        <h2 class="section-title">第三方账号</h2>
        <p class="section-desc">绑定后可使用第三方账号快捷登录</p>

        <div class="social-list">
          <div
            v-for="p in providers"
            :key="p.key"
            class="social-item"
          >
            <div class="social-left">
              <span class="social-icon" :style="{ background: p.color }">{{ p.short }}</span>
              <div class="social-meta">
                <span class="social-name">{{ p.label }}</span>
                <span v-if="isBound(p.key)" class="social-status bound">
                  已绑定 · {{ formatBoundAt(p.key) }}
                </span>
                <span v-else class="social-status">未绑定</span>
              </div>
            </div>
            <el-button
              v-if="isBound(p.key)"
              size="small"
              :loading="busyProvider === p.key"
              @click="unbind(p.key)"
            >
              解绑
            </el-button>
            <el-button
              v-else
              size="small"
              type="primary"
              plain
              :loading="busyProvider === p.key"
              @click="bind(p.key)"
            >
              绑定
            </el-button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import type { SocialProvider } from '@/api/modules'

const router = useRouter()
const auth = useAuthStore()

const loading = ref(true)
const editing = ref(false)
const saving = ref(false)
const busyProvider = ref<SocialProvider | ''>('')

const form = reactive({ nickname: '', phone: '' })

const providers: { key: SocialProvider; label: string; short: string; color: string }[] = [
  { key: 'wechat', label: '微信', short: '微', color: '#07c160' },
  { key: 'feishu', label: '飞书', short: '飞', color: '#3370ff' },
  { key: 'qq', label: 'QQ', short: 'Q', color: '#12b7f5' },
  { key: 'dingtalk', label: '钉钉', short: '钉', color: '#3296fa' },
  { key: 'douyin', label: '抖音', short: '抖', color: '#161823' }
]

const avatarLetter = computed(() => {
  if (auth.nickname) return auth.nickname.slice(0, 1).toUpperCase()
  const digits = auth.phone.replace(/\D/g, '')
  if (digits.length > 0) return digits.slice(-1)
  const name = auth.displayName
  return name ? name.slice(0, 1).toUpperCase() : '陶'
})

function isBound(p: SocialProvider): boolean {
  return !!auth.socialBindings[p]
}

function formatBoundAt(p: SocialProvider): string {
  const b = auth.socialBindings[p]
  if (!b?.bound_at) return ''
  return new Date(b.bound_at).toLocaleDateString('zh-CN')
}

function startEdit() {
  // 脱敏手机号不回填到输入框 (避免把 139****1234 当真号提交); 留空表示不改
  form.nickname = auth.nickname || ''
  form.phone = ''
  editing.value = true
}

function cancelEdit() {
  editing.value = false
}

async function save() {
  const payload: { nickname?: string; phone?: string } = {}
  payload.nickname = form.nickname.trim()
  const phone = form.phone.trim()
  if (phone) {
    if (!/^1\d{10}$/.test(phone)) {
      ElMessage.warning('请输入正确的 11 位手机号')
      return
    }
    payload.phone = phone
  }
  saving.value = true
  try {
    await auth.updateProfile(payload)
    ElMessage.success('资料已更新')
    editing.value = false
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '更新失败')
  } finally {
    saving.value = false
  }
}

async function bind(p: SocialProvider) {
  busyProvider.value = p
  try {
    await auth.bindSocial(p)
    ElMessage.success('绑定成功')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '绑定失败')
  } finally {
    busyProvider.value = ''
  }
}

async function unbind(p: SocialProvider) {
  try {
    await ElMessageBox.confirm(`确定解绑${providers.find(x => x.key === p)?.label}?`, '解绑确认', {
      confirmButtonText: '解绑',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  busyProvider.value = p
  try {
    await auth.unbindSocial(p)
    ElMessage.success('已解绑')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '解绑失败')
  } finally {
    busyProvider.value = ''
  }
}

onMounted(async () => {
  await auth.fetchUser(true)
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
  margin-bottom: var(--spacing-6, 24px);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
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

.info-list {
  margin-top: 4px;
}

.field-hint {
  font-size: 12px;
  color: var(--color-text-tertiary, #909399);
  margin-top: 4px;
}

.mono {
  font-family: monospace;
  font-size: 13px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary, #2c3e2d);
  margin: 0 0 4px;
}

.section-desc {
  font-size: 13px;
  color: var(--color-text-tertiary, #909399);
  margin: 0 0 20px;
}

.social-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.social-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border: 1px solid var(--color-border-light, #eee);
  border-radius: var(--radius-lg, 12px);
  transition: border-color 0.2s;
}

.social-item:hover {
  border-color: var(--color-primary-light, #6b8a72);
}

.social-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.social-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
}

.social-meta {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.social-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--color-text-primary, #2c3e2d);
}

.social-status {
  font-size: 12px;
  color: var(--color-text-tertiary, #909399);
}

.social-status.bound {
  color: var(--color-success, #5b8a72);
}

.loading-container {
  padding: var(--spacing-8, 32px);
}
</style>
