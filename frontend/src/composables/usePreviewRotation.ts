/**
 * 3D 预览旋转/拖拽控制
 *
 * 从 DesignView.vue 抽出的视图状态：
 * - rotateX / rotateY：CSS 3D transform 角度
 * - autoRotate：自动旋转开关
 * - 鼠标拖拽改变角度（拖拽时自动暂停 auto-rotate）
 *
 * 使用方式：
 *   const preview = usePreviewRotation()
 *   preview.bindStage(stageRef)         // 在 onMounted 调用
 *   <div :style="{ transform: preview.transform.value }">
 */
import { computed, onUnmounted, ref, type Ref } from 'vue'

export interface PreviewRotation {
  rotateX: Ref<number>
  rotateY: Ref<number>
  autoRotate: Ref<boolean>
  transform: Ref<string>
  toggleAutoRotate: () => void
  resetView: () => void
  bindStage: (stage: HTMLElement | null) => void
}

interface Options {
  initialRotateX?: number
  initialRotateY?: number
  /** auto-rotate 每 tick 的角度增量（度） */
  rotateStep?: number
  /** 拖拽 X 灵敏度 */
  dragSensitivityX?: number
  /** 拖拽 Y 灵敏度 */
  dragSensitivityY?: number
  /** 上下俯仰角钳制范围 */
  pitchClamp?: [number, number]
  /** auto-rotate 定时器周期（ms） */
  intervalMs?: number
}

export function usePreviewRotation(opts: Options = {}): PreviewRotation {
  const {
    initialRotateX = -8,
    initialRotateY = 0,
    rotateStep = 0.8,
    dragSensitivityX = 0.5,
    dragSensitivityY = 0.3,
    pitchClamp = [-25, 25],
    intervalMs = 50,
  } = opts

  const rotateX = ref(initialRotateX)
  const rotateY = ref(initialRotateY)
  const autoRotate = ref(true)

  const transform = computed(
    () => `rotateX(${rotateX.value}deg) rotateY(${rotateY.value}deg)`
  )

  const timer = setInterval(() => {
    if (autoRotate.value) {
      rotateY.value += rotateStep
    }
  }, intervalMs)

  // 拖拽状态封闭在 composable 内，不污染调用方
  let dragging = false
  let lastX = 0
  let lastY = 0
  let boundStage: HTMLElement | null = null

  const onMove = (e: MouseEvent) => {
    if (!dragging) return
    const dx = e.clientX - lastX
    const dy = e.clientY - lastY
    rotateY.value += dx * dragSensitivityX
    rotateX.value = Math.max(
      pitchClamp[0],
      Math.min(pitchClamp[1], rotateX.value - dy * dragSensitivityY)
    )
    lastX = e.clientX
    lastY = e.clientY
  }

  const onUp = () => {
    dragging = false
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }

  const onDown = (e: MouseEvent) => {
    dragging = true
    autoRotate.value = false
    lastX = e.clientX
    lastY = e.clientY
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  const bindStage = (stage: HTMLElement | null) => {
    if (boundStage) {
      boundStage.removeEventListener('mousedown', onDown)
    }
    boundStage = stage
    if (stage) {
      stage.addEventListener('mousedown', onDown)
    }
  }

  onUnmounted(() => {
    clearInterval(timer)
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
    if (boundStage) {
      boundStage.removeEventListener('mousedown', onDown)
    }
  })

  return {
    rotateX,
    rotateY,
    autoRotate,
    transform,
    toggleAutoRotate: () => {
      autoRotate.value = !autoRotate.value
    },
    resetView: () => {
      rotateX.value = initialRotateX
      rotateY.value = initialRotateY
    },
    bindStage,
  }
}
