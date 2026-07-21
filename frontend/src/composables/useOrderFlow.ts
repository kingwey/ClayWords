import { ref, computed } from 'vue'
import type { ComputedRef } from 'vue'
import type { Option } from '@/types/design'

export function useOrderFlow(
  topStudioName: ComputedRef<string>,
  currentOption: ComputedRef<Option | null>
) {
  const dispatchVisible = ref(false)
  const workorderVisible = ref(false)
  const studioAccepted = ref(false)
  const acceptedStudioName = ref('')

  function triggerStudioAccept() {
    studioAccepted.value = false
    setTimeout(() => {
      acceptedStudioName.value = topStudioName.value
      studioAccepted.value = true
    }, 2000)
  }

  function openOrder(_opt: Option) {
    dispatchVisible.value = true
  }

  function confirmOrder() {
    dispatchVisible.value = false
    workorderVisible.value = true
    triggerStudioAccept()
  }

  const currentOrderInfo = computed(() => {
    const opt = currentOption.value
    const today = new Date()
    const deliveryDate = new Date(today.getTime() + ((opt?.days || 9) + 2) * 86400000)
    return {
      orderId: `CW${today.getFullYear()}${String(today.getMonth() + 1).padStart(2, '0')}${String(today.getDate()).padStart(2, '0')}${Math.floor(Math.random() * 9999).toString().padStart(4, '0')}`,
      studioName: topStudioName.value,
      productName: opt?.name || '定制陶瓷',
      leadTime: opt?.days || 9,
      deliveryDate: `${deliveryDate.getFullYear()}-${String(deliveryDate.getMonth() + 1).padStart(2, '0')}-${String(deliveryDate.getDate()).padStart(2, '0')}`,
      params: [
        opt?.glaze || '冷白釉', opt?.size || 'H 20 × W 16 cm',
        '壁厚 4±1 mm', '窑温 1280 ℃', '还原焰 · 12h', '成品率 ~92%',
      ],
    }
  })

  return {
    dispatchVisible, workorderVisible, studioAccepted, acceptedStudioName,
    openOrder, confirmOrder, currentOrderInfo,
  }
}
