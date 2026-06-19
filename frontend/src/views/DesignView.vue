<template>
  <div class="design-page">
    <div class="design-layout">
      <!-- Left: Chat -->
      <aside class="chat-panel">
        <div class="chat-header">
          <h2>对话设计</h2>
        </div>
        <div ref="chatMessages" class="chat-messages">
          <div v-for="msg in messages" :key="msg.id" :class="['message', `message-${msg.role}`]">
            <div class="message-content">{{ msg.content }}</div>
          </div>
        </div>
        <div class="chat-input">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="3"
            :placeholder="placeholderText"
            :maxlength="200"
            show-word-limit
            @keydown.enter.ctrl="sendMessage"
          />
          <el-button type="primary" @click="sendMessage" :loading="sending">
            发送
          </el-button>
        </div>
      </aside>

      <!-- Center: Options -->
      <main class="options-panel">
        <div class="options-grid">
          <div v-for="option in options" :key="option.id" class="option-card" @click="selectOption(option)">
            <div class="option-thumbnail">
              <img v-if="option.thumbnail_url" :src="option.thumbnail_url" :alt="option.name" />
              <div v-else class="option-placeholder"></div>
            </div>
            <div class="option-info">
              <h3>{{ option.name }}</h3>
              <div class="option-meta">
                <el-tag size="small" :type="option.craft_check.passed ? 'success' : 'warning'">
                  {{ option.craft_check.passed ? '工艺合格' : '已自动修复' }}
                </el-tag>
                <span class="price">¥{{ option.price }}</span>
              </div>
            </div>
          </div>
        </div>
      </main>

      <!-- Right: 3D Preview -->
      <aside class="preview-panel">
        <div ref="previewContainer" class="preview-container"></div>
        <div class="preview-controls">
          <el-button @click="autoRotate = !autoRotate">
            {{ autoRotate ? '停止旋转' : '自动旋转' }}
          </el-button>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
}

interface CraftCheck {
  passed: boolean
  issues: string[]
  auto_fixed: boolean
}

interface Option {
  id: string
  name: string
  thumbnail_url: string
  glb_url: string
  craft_check: CraftCheck
  price: number
}

const chatMessages = ref<HTMLElement | null>(null)
const previewContainer = ref<HTMLElement | null>(null)
const messages = ref<Message[]>([])
const inputText = ref('')
const sending = ref(false)
const options = ref<Option[]>([])
const autoRotate = ref(true)

const placeholders = [
  '我想要一个玉兔捧月的花瓶',
  '给妈妈做一个生日礼物摆件',
  '一个中式风格的茶宠',
  '简约风格的陶瓷装饰品'
]
const placeholderText = ref(placeholders[0])

let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let controls: OrbitControls
let currentMesh: THREE.Mesh

function selectOption(option: Option) {
  console.log('Selected option:', option)
}

async function sendMessage() {
  if (!inputText.value.trim()) return
  sending.value = true
  messages.value.push({
    id: Date.now().toString(),
    role: 'user',
    content: inputText.value
  })
  inputText.value = ''
  sending.value = false
}

function initPreview() {
  if (!previewContainer.value) return

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0xf5f0e8)

  camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000)
  camera.position.set(3, 3, 3)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(window.devicePixelRatio)
  previewContainer.value.appendChild(renderer.domElement)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.autoRotate = autoRotate.value

  const light = new THREE.DirectionalLight(0xffffff, 1)
  light.position.set(5, 5, 5)
  scene.add(light)
  scene.add(new THREE.AmbientLight(0xffffff, 0.5))

  const geometry = new THREE.BoxGeometry(1.5, 1.5, 1.5)
  const material = new THREE.MeshStandardMaterial({
    color: 0x7B9BA8,
    roughness: 0.3
  })
  currentMesh = new THREE.Mesh(geometry, material)
  scene.add(currentMesh)

  animate()
}

function animate() {
  requestAnimationFrame(animate)
  controls.autoRotate = autoRotate.value
  controls.update()
  renderer.render(scene, camera)
}

function handleResize() {
  if (!previewContainer.value) return
  const width = previewContainer.value.clientWidth
  const height = previewContainer.value.clientHeight
  renderer.setSize(width, height)
  camera.aspect = width / height
  camera.updateProjectionMatrix()
}

onMounted(() => {
  initPreview()
  window.addEventListener('resize', handleResize)

  let idx = 0
  setInterval(() => {
    idx = (idx + 1) % placeholders.length
    placeholderText.value = placeholders[idx]
  }, 3000)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  renderer?.dispose()
})
</script>

<style scoped>
.design-page {
  height: 100vh;
  overflow: hidden;
}

.design-layout {
  display: grid;
  grid-template-columns: 30% 40% 30%;
  height: 100%;
}

.chat-panel {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--color-border);
  background: var(--color-surface);
}

.chat-header {
  padding: var(--spacing-4);
  border-bottom: 1px solid var(--color-border);
}

.chat-header h2 {
  font-size: var(--font-size-lg);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-4);
}

.message {
  margin-bottom: var(--spacing-4);
}

.message-user {
  text-align: right;
}

.message-content {
  display: inline-block;
  padding: var(--spacing-3);
  border-radius: var(--radius-md);
  max-width: 80%;
}

.message-user .message-content {
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.message-assistant .message-content {
  background: var(--color-background);
}

.chat-input {
  padding: var(--spacing-4);
  border-top: 1px solid var(--color-border);
}

.options-panel {
  overflow-y: auto;
  padding: var(--spacing-4);
  background: var(--color-background);
}

.options-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--spacing-4);
}

.option-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  overflow: hidden;
  cursor: pointer;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}

.option-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.option-thumbnail {
  height: 150px;
  background: var(--color-background);
}

.option-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.option-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, var(--color-glaze-celadon) 0%, var(--color-glaze-jade) 100%);
}

.option-info {
  padding: var(--spacing-3);
}

.option-info h3 {
  font-size: var(--font-size-base);
  margin-bottom: var(--spacing-2);
}

.option-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.price {
  font-weight: bold;
  color: var(--color-accent);
}

.preview-panel {
  display: flex;
  flex-direction: column;
  border-left: 1px solid var(--color-border);
  background: var(--color-surface);
}

.preview-container {
  flex: 1;
}

.preview-controls {
  padding: var(--spacing-4);
  border-top: 1px solid var(--color-border);
  display: flex;
  gap: var(--spacing-2);
}
</style>
