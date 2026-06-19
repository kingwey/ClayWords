<template>
  <div class="home">
    <header class="hero">
      <div class="hero-content">
        <h1 class="title">陶语</h1>
        <p class="subtitle">AI 陶瓷定制 · 所想即所得</p>
        <el-button type="primary" size="large" @click="goToDesign">
          开始创作
        </el-button>
      </div>
      <div class="hero-3d">
        <div ref="threeContainer" class="three-container"></div>
      </div>
    </header>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import * as THREE from 'three'

const router = useRouter()
const threeContainer = ref<HTMLElement | null>(null)
let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let cube: THREE.Mesh

function goToDesign() {
  router.push('/design')
}

function initThree() {
  if (!threeContainer.value) return

  scene = new THREE.Scene()
  camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000)
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })

  threeContainer.value.appendChild(renderer.domElement)

  const geometry = new THREE.BoxGeometry(2, 2, 2)
  const material = new THREE.MeshStandardMaterial({
    color: 0x7B9BA8,
    roughness: 0.3,
    metalness: 0.1
  })
  cube = new THREE.Mesh(geometry, material)
  scene.add(cube)

  const light = new THREE.DirectionalLight(0xffffff, 1)
  light.position.set(5, 5, 5)
  scene.add(light)
  scene.add(new THREE.AmbientLight(0xffffff, 0.5))

  camera.position.z = 4

  animate()
}

function animate() {
  requestAnimationFrame(animate)
  cube.rotation.x += 0.01
  cube.rotation.y += 0.01
  renderer.render(scene, camera)
}

function handleResize() {
  if (!threeContainer.value) return
  const width = threeContainer.value.clientWidth
  const height = threeContainer.value.clientHeight
  renderer.setSize(width, height)
  camera.aspect = width / height
  camera.updateProjectionMatrix()
}

onMounted(() => {
  initThree()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  renderer?.dispose()
})
</script>

<style scoped>
.home {
  min-height: 100vh;
}

.hero {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: var(--spacing-8);
  background: linear-gradient(135deg, var(--color-background) 0%, var(--color-surface) 100%);
}

.hero-content {
  flex: 1;
  max-width: 500px;
}

.title {
  font-family: var(--font-family-display);
  font-size: var(--font-size-3xl);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-4);
}

.subtitle {
  font-size: var(--font-size-lg);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-8);
}

.hero-3d {
  flex: 1;
  height: 400px;
}

.three-container {
  width: 100%;
  height: 100%;
  border-radius: var(--radius-lg);
}
</style>
