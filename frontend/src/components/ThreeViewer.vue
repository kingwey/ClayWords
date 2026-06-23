<template>
  <div ref="containerRef" class="three-viewer"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

const props = defineProps<{
  glbUrl: string
  autoRotate?: boolean
}>()

const containerRef = ref<HTMLDivElement | null>(null)

let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let renderer: THREE.WebGLRenderer | null = null
let controls: OrbitControls | null = null
let animationId: number | null = null
let currentModel: THREE.Group | null = null

const initThreeJS = () => {
  if (!containerRef.value) return

  const container = containerRef.value
  const width = container.clientWidth
  const height = container.clientHeight

  // Scene
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0xf5f5f0)

  // Camera
  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000)
  camera.position.set(0, 1.5, 3)

  // Renderer
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setSize(width, height)
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.2
  container.appendChild(renderer.domElement)

  // Lights
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
  scene.add(ambientLight)

  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
  directionalLight.position.set(2, 4, 3)
  directionalLight.castShadow = true
  directionalLight.shadow.mapSize.width = 2048
  directionalLight.shadow.mapSize.height = 2048
  scene.add(directionalLight)

  const fillLight = new THREE.DirectionalLight(0xc9d7e8, 0.4)
  fillLight.position.set(-2, 2, -2)
  scene.add(fillLight)

  // Ground
  const groundGeometry = new THREE.CircleGeometry(3, 32)
  const groundMaterial = new THREE.MeshStandardMaterial({
    color: 0xf0ebe3,
    roughness: 0.8,
    metalness: 0.1
  })
  const ground = new THREE.Mesh(groundGeometry, groundMaterial)
  ground.rotation.x = -Math.PI / 2
  ground.receiveShadow = true
  scene.add(ground)

  // Controls
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  controls.minDistance = 1
  controls.maxDistance = 10
  controls.maxPolarAngle = Math.PI / 2
  controls.autoRotate = props.autoRotate ?? false
  controls.autoRotateSpeed = 2

  // Load GLB
  loadGLB(props.glbUrl)

  // Animation loop
  const animate = () => {
    animationId = requestAnimationFrame(animate)
    if (controls) controls.update()
    if (renderer && scene && camera) {
      renderer.render(scene, camera)
    }
  }
  animate()

  // Handle resize
  window.addEventListener('resize', handleResize)
}

const loadGLB = (url: string) => {
  if (!scene || !camera) return

  // Remove old model
  if (currentModel) {
    scene.remove(currentModel)
    currentModel = null
  }

  const loader = new GLTFLoader()
  loader.load(
    url,
    (gltf) => {
      const model = gltf.scene

      // Enable shadows
      model.traverse((child) => {
        if ((child as THREE.Mesh).isMesh) {
          child.castShadow = true
          child.receiveShadow = true
        }
      })

      // Center and scale model
      const box = new THREE.Box3().setFromObject(model)
      const center = box.getCenter(new THREE.Vector3())
      const size = box.getSize(new THREE.Vector3())

      // Scale to fit in view (max dimension = 2)
      const maxDim = Math.max(size.x, size.y, size.z)
      const scale = 2 / maxDim
      model.scale.setScalar(scale)

      // Center model
      model.position.sub(center.multiplyScalar(scale))
      model.position.y = size.y * scale / 2 // Place on ground

      scene!.add(model)
      currentModel = model

      console.log('GLB loaded:', url)
    },
    (progress) => {
      const percent = (progress.loaded / progress.total) * 100
      console.log(`Loading GLB: ${percent.toFixed(0)}%`)
    },
    (error) => {
      console.error('Error loading GLB:', error)
    }
  )
}

const handleResize = () => {
  if (!containerRef.value || !camera || !renderer) return

  const width = containerRef.value.clientWidth
  const height = containerRef.value.clientHeight

  camera.aspect = width / height
  camera.updateProjectionMatrix()

  renderer.setSize(width, height)
}

const cleanup = () => {
  if (animationId !== null) {
    cancelAnimationFrame(animationId)
    animationId = null
  }

  window.removeEventListener('resize', handleResize)

  if (controls) {
    controls.dispose()
    controls = null
  }

  if (renderer) {
    renderer.dispose()
    renderer.domElement.remove()
    renderer = null
  }

  scene = null
  camera = null
  currentModel = null
}

// Watch for GLB URL changes
watch(() => props.glbUrl, (newUrl) => {
  if (newUrl && scene) {
    loadGLB(newUrl)
  }
})

// Watch for autoRotate changes
watch(() => props.autoRotate, (newValue) => {
  if (controls) {
    controls.autoRotate = newValue ?? false
  }
})

onMounted(() => {
  initThreeJS()
})

onUnmounted(() => {
  cleanup()
})
</script>

<style scoped>
.three-viewer {
  width: 100%;
  height: 100%;
  position: relative;
  border-radius: 16px;
  overflow: hidden;
}

.three-viewer canvas {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
