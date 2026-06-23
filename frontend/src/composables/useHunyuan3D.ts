import { ref, onUnmounted } from 'vue'
import { hunyuan3dApi } from '@/api/modules'
import type { Hunyuan3DSubmitRequest, TaskStatusResponse } from '@/types'

export interface Hunyuan3DTaskState {
  taskId: string | null
  jobId: string | null
  state: 'idle' | 'submitting' | 'pending' | 'running' | 'completed' | 'failed' | 'timeout'
  progress: number
  message: string
  glbUrl: string | null
  thumbnailUrl: string | null
  error: string | null
}

/**
 * Hunyuan3D 任务管理 composable
 *
 * 功能:
 * - 提交 3D 生成任务
 * - SSE 实时进度监听
 * - 状态轮询 fallback
 * - 超时处理
 */
export function useHunyuan3D() {
  const taskState = ref<Hunyuan3DTaskState>({
    taskId: null,
    jobId: null,
    state: 'idle',
    progress: 0,
    message: '',
    glbUrl: null,
    thumbnailUrl: null,
    error: null
  })

  let eventSource: EventSource | null = null
  let pollTimer: number | null = null
  let timeoutTimer: number | null = null

  /**
   * 提交 3D 生成任务
   */
  const submitTask = async (request: Hunyuan3DSubmitRequest) => {
    // 清理旧任务
    cleanup()

    taskState.value = {
      taskId: null,
      jobId: null,
      state: 'submitting',
      progress: 0,
      message: '正在提交任务...',
      glbUrl: null,
      thumbnailUrl: null,
      error: null
    }

    try {
      const response = await hunyuan3dApi.submit(request)

      taskState.value.taskId = response.task_id
      taskState.value.jobId = response.job_id
      taskState.value.state = 'pending'
      taskState.value.message = '任务已提交,等待处理...'

      // 启动 SSE 监听
      startSSE(response.task_id)

      // 启动超时计时器 (5 分钟)
      timeoutTimer = window.setTimeout(() => {
        handleTimeout()
      }, 5 * 60 * 1000)

    } catch (error: any) {
      taskState.value.state = 'failed'
      taskState.value.error = error.response?.data?.detail || '提交任务失败'
      taskState.value.message = taskState.value.error
    }
  }

  /**
   * 启动 SSE 实时监听
   */
  const startSSE = (taskId: string) => {
    const url = hunyuan3dApi.getTaskEventsUrl(taskId)

    // 注意: EventSource 会自动带上 Cookie (withCredentials)
    eventSource = new EventSource(url)

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleSSEEvent(data)
      } catch (e) {
        console.error('SSE parse error:', e)
      }
    }

    eventSource.onerror = (error) => {
      console.error('SSE error:', error)
      eventSource?.close()
      eventSource = null

      // SSE 断开后 fallback 到轮询
      if (taskState.value.state !== 'completed' && taskState.value.state !== 'failed') {
        startPolling(taskId)
      }
    }
  }

  /**
   * 处理 SSE 事件
   */
  const handleSSEEvent = (data: any) => {
    if (data.state) {
      taskState.value.state = data.state
    }

    if (data.progress !== undefined) {
      taskState.value.progress = data.progress
    }

    if (data.message) {
      taskState.value.message = data.message
    }

    if (data.state === 'completed' && data.result) {
      taskState.value.glbUrl = data.result.glb_url
      taskState.value.thumbnailUrl = data.result.thumbnail_url
      taskState.value.progress = 100
      taskState.value.message = '生成完成!'
      cleanup()
    }

    if (data.state === 'failed') {
      taskState.value.error = data.error || '生成失败'
      taskState.value.message = taskState.value.error
      cleanup()
    }
  }

  /**
   * 轮询 fallback (SSE 失败时)
   */
  const startPolling = (taskId: string) => {
    pollTimer = window.setInterval(async () => {
      try {
        const status = await hunyuan3dApi.getTaskStatus(taskId)
        updateFromStatus(status)

        if (status.state === 'completed' || status.state === 'failed' || status.state === 'timeout') {
          cleanup()
        }
      } catch (error) {
        console.error('Poll error:', error)
      }
    }, 2000) // 每 2 秒轮询一次
  }

  /**
   * 从状态响应更新本地状态
   */
  const updateFromStatus = (status: TaskStatusResponse) => {
    taskState.value.state = status.state

    if (status.state === 'completed' && status.result) {
      taskState.value.glbUrl = status.result.glb_url || null
      taskState.value.thumbnailUrl = status.result.thumbnail_url || null
      taskState.value.progress = 100
      taskState.value.message = '生成完成!'
    } else if (status.state === 'failed') {
      taskState.value.error = status.error || '生成失败'
      taskState.value.message = taskState.value.error
    } else if (status.state === 'timeout') {
      taskState.value.error = '生成超时'
      taskState.value.message = '任务超时,请稍后重试'
    }
  }

  /**
   * 处理超时
   */
  const handleTimeout = () => {
    if (taskState.value.state !== 'completed' && taskState.value.state !== 'failed') {
      taskState.value.state = 'timeout'
      taskState.value.error = '任务超时(5分钟)'
      taskState.value.message = '生成超时,请稍后重试'
      cleanup()
    }
  }

  /**
   * 清理资源
   */
  const cleanup = () => {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }

    if (pollTimer !== null) {
      clearInterval(pollTimer)
      pollTimer = null
    }

    if (timeoutTimer !== null) {
      clearTimeout(timeoutTimer)
      timeoutTimer = null
    }
  }

  /**
   * 重置状态
   */
  const reset = () => {
    cleanup()
    taskState.value = {
      taskId: null,
      jobId: null,
      state: 'idle',
      progress: 0,
      message: '',
      glbUrl: null,
      thumbnailUrl: null,
      error: null
    }
  }

  // 组件卸载时清理
  onUnmounted(() => {
    cleanup()
  })

  return {
    taskState,
    submitTask,
    reset,
    cleanup
  }
}
