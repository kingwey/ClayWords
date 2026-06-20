<template>
  <div class="dispatch-visualization">
    <div class="dispatch-header">
      <h3>工作室评分</h3>
      <p class="dispatch-subtitle">综合四维评分智能派单</p>
    </div>

    <div class="studios-grid">
      <div
        v-for="(studio, index) in studios"
        :key="studio.id"
        :class="['studio-card', { 'winner': isWinner(studio), 'highlighted': highlightedStudio === studio.id }]"
        :style="{ animationDelay: `${index * 0.15}s` }"
        @click="selectStudio(studio)"
      >
        <div class="studio-header">
          <span class="studio-name">{{ studio.name }}</span>
          <span v-if="isWinner(studio)" class="winner-badge">推荐</span>
        </div>

        <div class="score-bars">
          <div v-for="dim in dimensions" :key="dim.key" class="score-row">
            <span class="dim-label">{{ dim.label }}</span>
            <div class="bar-container">
              <div
                class="bar-fill"
                :style="{
                  width: animated ? `${studio.scores[dim.key] * 100}%` : '0%',
                  backgroundColor: dim.color,
                  transitionDelay: `${index * 0.1 + dimensions.indexOf(dim) * 0.05}s`
                }"
              ></div>
            </div>
            <span class="dim-score">{{ (studio.scores[dim.key] * 100).toFixed(0) }}</span>
          </div>
        </div>

        <div class="studio-total">
          <span class="total-label">综合得分</span>
          <span class="total-value" :class="{ 'gold': isWinner(studio) }">
            {{ (studio.totalScore * 100).toFixed(0) }}
          </span>
        </div>
      </div>
    </div>

    <!-- Winner Animation Overlay -->
    <transition name="winner-pop">
      <div v-if="showWinnerAnimation" class="winner-animation">
        <div class="winner-seal">派</div>
        <p>工单已派至 <strong>{{ winnerName }}</strong></p>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'

interface Studio {
  id: string
  name: string
  scores: {
    craft: number
    capacity: number
    geo: number
    rating: number
  }
  totalScore: number
}

interface Dimension {
  key: keyof Studio['scores']
  label: string
  color: string
}

const props = defineProps<{
  studios: Studio[]
  showAnimation?: boolean
}>()

const emit = defineEmits<{
  (e: 'select', studio: Studio): void
}>()

const dimensions: Dimension[] = [
  { key: 'craft', label: '工艺', color: '#c97b5a' },
  { key: 'capacity', label: '产能', color: '#7B9BA8' },
  { key: 'geo', label: '距离', color: '#5B8A72' },
  { key: 'rating', label: '评分', color: '#D4A574' }
]

const animated = ref(false)
const highlightedStudio = ref<string | null>(null)
const showWinnerAnimation = ref(false)
const winnerName = ref('')

const winner = computed(() => {
  if (props.studios.length === 0) return null
  return props.studios.reduce((prev, current) =>
    prev.totalScore > current.totalScore ? prev : current
  )
})

function isWinner(studio: Studio): boolean {
  return winner.value?.id === studio.id
}

function selectStudio(studio: Studio) {
  highlightedStudio.value = studio.id
  emit('select', studio)
}

function animateScores() {
  animated.value = false
  setTimeout(() => {
    animated.value = true
  }, 100)
}

function triggerWinnerAnimation(studioName: string) {
  winnerName.value = studioName
  showWinnerAnimation.value = true
  setTimeout(() => {
    showWinnerAnimation.value = false
  }, 2500)
}

watch(() => props.studios, () => {
  animateScores()
}, { immediate: true })

onMounted(() => {
  setTimeout(() => {
    animated.value = true
  }, 300)
})

defineExpose({
  triggerWinnerAnimation,
  highlightStudio: (id: string) => { highlightedStudio.value = id }
})
</script>

<style scoped>
.dispatch-visualization {
  position: relative;
  padding: var(--spacing-6);
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-border);
}

.dispatch-header {
  margin-bottom: var(--spacing-6);
}

.dispatch-header h3 {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-1);
}

.dispatch-subtitle {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.studios-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-4);
}

.studio-card {
  padding: var(--spacing-4);
  background: var(--color-background);
  border-radius: var(--radius-lg);
  border: 2px solid transparent;
  cursor: pointer;
  transition: all var(--transition-normal);
  animation: card-enter 0.5s ease-out forwards;
  opacity: 0;
}

@keyframes card-enter {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.studio-card:hover {
  border-color: var(--color-border);
  box-shadow: var(--shadow-md);
}

.studio-card.highlighted {
  border-color: var(--color-primary);
  background: var(--color-surface);
}

.studio-card.winner {
  border-color: #D4A574;
  background: linear-gradient(135deg, rgba(212, 165, 116, 0.08) 0%, rgba(212, 165, 116, 0.02) 100%);
}

.studio-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
}

.studio-name {
  font-weight: 600;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.winner-badge {
  font-size: var(--font-size-xs);
  padding: 2px 8px;
  background: linear-gradient(135deg, #D4A574 0%, #c97b5a 100%);
  color: white;
  border-radius: var(--radius-full);
  font-weight: 600;
}

.score-bars {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.score-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.dim-label {
  width: 36px;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.bar-container {
  flex: 1;
  height: 8px;
  background: var(--color-border);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
  width: 0%;
}

.dim-score {
  width: 28px;
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-primary);
  text-align: right;
}

.studio-total {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--spacing-3);
  padding-top: var(--spacing-3);
  border-top: 1px dashed var(--color-border);
}

.total-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.total-value {
  font-size: var(--font-size-xl);
  font-weight: 800;
  color: var(--color-text-primary);
  transition: all var(--transition-normal);
}

.total-value.gold {
  background: linear-gradient(135deg, #D4A574 0%, #c97b5a 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* Winner Animation */
.winner-animation {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(250, 246, 240, 0.95);
  border-radius: var(--radius-xl);
  z-index: 10;
}

.winner-seal {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  font-weight: 900;
  color: #a55d3f;
  background: linear-gradient(135deg, rgba(201, 123, 90, 0.15) 0%, rgba(201, 123, 90, 0.05) 100%);
  border: 3px solid #c97b5a;
  border-radius: 50%;
  margin-bottom: var(--spacing-4);
  animation: seal-stamp 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

@keyframes seal-stamp {
  0% {
    transform: scale(2) rotate(-15deg);
    opacity: 0;
  }
  50% {
    transform: scale(0.9) rotate(5deg);
  }
  100% {
    transform: scale(1) rotate(0deg);
    opacity: 1;
  }
}

.winner-animation p {
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
}

.winner-animation strong {
  color: var(--color-primary);
  font-weight: 700;
}

.winner-pop-enter-active {
  animation: pop-in 0.3s ease-out;
}

.winner-pop-leave-active {
  animation: pop-out 0.3s ease-in;
}

@keyframes pop-in {
  from { opacity: 0; transform: scale(0.9); }
  to { opacity: 1; transform: scale(1); }
}

@keyframes pop-out {
  from { opacity: 1; transform: scale(1); }
  to { opacity: 0; transform: scale(0.9); }
}

@media (max-width: 640px) {
  .studios-grid {
    grid-template-columns: 1fr;
  }
}
</style>
