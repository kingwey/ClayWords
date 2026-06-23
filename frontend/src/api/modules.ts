import client from './client'
import type {
  StudioOrderSummary,
  StudioOrderDetail,
  StudioListItem,
  AlertItem,
  Hunyuan3DSubmitRequest,
  Hunyuan3DSubmitResponse,
  TaskStatusResponse
} from '@/types'

// ============ 认证 API ============

export interface CurrentUser {
  user_id: string
  phone: string         // 已脱敏 (139****1234)
  role: 'user' | 'studio' | 'admin'
  studio_id: string | null
}

export const authApi = {
  /** 当前登录用户资料 (用于显示昵称 / 头像; 未登录返回 401) */
  getCurrentUser() {
    return client.get<CurrentUser>('/api/v1/auth/user')
  },

  /** 登出 - 后端清 HttpOnly cookie */
  logout() {
    return client.post('/api/v1/auth/logout')
  }
}

// ============ Hunyuan3D API ============

export const hunyuan3dApi = {
  /** 提交 3D 生成任务 */
  submit(payload: Hunyuan3DSubmitRequest) {
    return client.post<Hunyuan3DSubmitResponse>('/api/v1/hunyuan3d/submit', payload)
  },

  /** 查询任务状态 */
  getTaskStatus(taskId: string) {
    return client.get<TaskStatusResponse>(`/api/v1/tasks/${taskId}`)
  },

  /** SSE 实时进度流 (返回 EventSource URL) */
  getTaskEventsUrl(taskId: string) {
    return `/api/v1/tasks/${taskId}/events`
  }
}

// ============ 工作室端 API ============

export const studioApi = {
  /** 工作室订单列表 */
  listOrders(statusFilter?: string) {
    const params = statusFilter ? { status_filter: statusFilter } : {}
    return client.get<StudioOrderSummary[]>('/api/v1/studio/orders', { params })
  },

  /** 订单详情 */
  getOrder(orderId: string) {
    return client.get<StudioOrderDetail>(`/api/v1/studio/orders/${orderId}`)
  },

  /** 接单 */
  acceptOrder(orderId: string, payload: { estimated_completion_date?: string; notes?: string }) {
    return client.post(`/api/v1/studio/orders/${orderId}/accept`, payload)
  },

  /** 拒单 */
  rejectOrder(orderId: string, payload: { reason: string; reason_category: string }) {
    return client.post(`/api/v1/studio/orders/${orderId}/reject`, payload)
  },

  /** 完成制作 */
  completeOrder(orderId: string) {
    return client.post(`/api/v1/studio/orders/${orderId}/complete`)
  },

  /** 发货 */
  shipOrder(
    orderId: string,
    payload: { carrier: string; tracking_number: string; estimated_delivery_date?: string; notes?: string }
  ) {
    return client.post(`/api/v1/logistics/orders/${orderId}/ship`, payload)
  }
}

// ============ 管理后台 API ============

export const adminApi = {
  /** 待审核工作室列表 */
  listPendingStudios() {
    return client.get<StudioListItem[]>('/api/v1/studios/pending')
  },

  /** 全部工作室列表 */
  listStudios() {
    return client.get<StudioListItem[]>('/api/v1/studios')
  },

  /** 工作室详情 */
  getStudio(studioId: string) {
    return client.get(`/api/v1/studios/${studioId}`)
  },

  /** 审核工作室（批准/拒绝） */
  approveStudio(
    studioId: string,
    payload: { action: 'approve' | 'reject'; reason?: string; adjusted_capacity?: number }
  ) {
    return client.post(`/api/v1/studios/${studioId}/approve`, payload)
  },

  /** 全部订单（管理视角，复用用户订单接口） */
  listOrders(statusFilter?: string) {
    const params = statusFilter ? { status_filter: statusFilter } : {}
    return client.get('/api/v1/orders', { params })
  },

  /** Admin 视角：跨用户/跨工作室订单列表 */
  listAllOrders(params: {
    status_filter?: string
    user_id?: string
    studio_id?: string
    keyword?: string
    limit?: number
    offset?: number
  } = {}) {
    return client.get('/api/v1/admin/orders', { params })
  },

  /** Admin 视角：订单详情 + 完整日志 */
  getOrderDetail(orderId: string) {
    return client.get(`/api/v1/admin/orders/${orderId}`)
  },

  /** Admin 强制取消 */
  cancelOrder(orderId: string, reason: string) {
    return client.post(`/api/v1/admin/orders/${orderId}/cancel`, { reason })
  },

  /** Admin 强制退款 */
  refundOrder(orderId: string, payload: { reason: string; amount?: number }) {
    return client.post(`/api/v1/admin/orders/${orderId}/refund`, payload)
  },

  /** Admin 重派 */
  redispatchOrder(orderId: string, reason: string) {
    return client.post(`/api/v1/admin/orders/${orderId}/redispatch`, { reason })
  },

  /** 活跃告警 */
  listActiveAlerts() {
    return client.get<AlertItem[]>('/api/v1/alerts/active')
  },

  /** 业务指标（JSON） */
  getMetrics() {
    return client.get('/metrics/json')
  }
}
