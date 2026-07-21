import { ref } from 'vue'
import type { Ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { Message, Option } from '@/types/design'
import { sessionsApi, tasksApi } from '@/api/modules'

export function useDesignMessagesReal(currentGlaze: Ref<string>) {
  const messages = ref<Message[]>([])
  const options = ref<Option[]>([])
  const selectedOptionId = ref<string | null>(null)
  const inputText = ref('')
  const sending = ref(false)
  const referenceImageUrl = ref<string | null>(null)
  const sessionId = ref<string | null>(null)

  function addAiMessage(content: string, withOptions?: Option[]) {
    messages.value.push({ role: 'ai', content, options: withOptions })
  }

  function addUserMessage(content: string) {
    messages.value.push({ role: 'user', content })
  }

  function onReferenceUpload(payload: { uploadId: string; url: string }) {
    referenceImageUrl.value = payload.url
    addAiMessage('已收到你的参考图 📎，我会参考它的造型与风格来生成方案。')
  }

  /**
   * 初始化会话
   */
  async function initSession() {
    try {
      const { data } = await sessionsApi.createSession('陶瓷设计会话')
      sessionId.value = data.id
      console.log('Session created:', sessionId.value)
    } catch (error) {
      console.error('Failed to create session:', error)
      ElMessage.error('会话创建失败，将使用本地模式')
    }
  }

  /**
   * 轮询任务状态，直到完成或失败
   */
  async function pollTaskStatus(taskId: string): Promise<any> {
    const maxAttempts = 60 // 最多轮询 60 次
    const interval = 2000 // 每 2 秒轮询一次

    for (let i = 0; i < maxAttempts; i++) {
      try {
        const { data } = await tasksApi.getTaskStatus(taskId)

        console.log(`Task ${taskId} status:`, data.state, data.progress)

        if (data.state === 'completed') {
          return data.result
        }

        if (data.state === 'failed') {
          throw new Error(data.error || '任务处理失败')
        }

        // 更新进度提示
        if (data.state === 'processing' && data.progress) {
          const progressMsg = messages.value.find(m => m.role === 'ai' && m.content.includes('正在处理'))
          if (progressMsg) {
            progressMsg.content = `<strong>陶语 · 正在处理</strong><br/>进度: ${Math.round(data.progress * 100)}%`
          }
        }

        await new Promise(resolve => setTimeout(resolve, interval))
      } catch (error) {
        console.error('Poll task error:', error)
        throw error
      }
    }

    throw new Error('任务超时')
  }

  /**
   * 发送用户消息并生成方案
   */
  async function sendUserMessage() {
    if (!inputText.value.trim() || sending.value) return

    const prompt = inputText.value.trim()
    inputText.value = ''
    sending.value = true

    addUserMessage(prompt)

    try {
      // 1. 如果没有会话，先创建
      if (!sessionId.value) {
        await initSession()
        if (!sessionId.value) {
          throw new Error('无法创建会话')
        }
      }

      // 2. 显示关键词解析中
      addAiMessage(`<strong>陶语 · 正在分析</strong><br/>
        正在解析您的设计需求…<br/>
        <em style="color:#8a7d6f;font-size:12px;">使用 AI 提取造型、釉色、尺寸等参数</em>`)

      // 3. 发送消息到后端（创建任务）
      // 使用 demo=true 参数启用演示模式（不需要 Worker）
      const { data: taskData } = await sessionsApi.sendMessage(sessionId.value, prompt, true)
      console.log('Task created:', taskData.task_id)

      // 4. 显示处理中
      addAiMessage(`<strong>陶语 · 正在处理</strong><br/>任务已创建，正在生成方案…`)

      // 5. 轮询任务状态
      const result = await pollTaskStatus(taskData.task_id)

      // 6. 处理返回结果
      if (result && result.designs && result.designs.length > 0) {
        // 转换后端返回的设计方案为前端 Option 格式
        const newOptions: Option[] = result.designs.map((design: any, index: number) => ({
          id: design.design_id || `opt-${Date.now()}-${index}`,
          idx: `${index + 1}`,
          name: design.name || `方案 ${index + 1}`,
          desc: design.description || '',
          glaze: design.glaze_color || currentGlaze.value,
          size: design.size || 'H 20 × W 16 cm',
          days: design.estimated_days || 9,
          price: design.price || 388,
          tags: design.tags || [],
          type: design.type || 'vase',
          colors: design.colors || { light: '#f5f0e8', mid: '#ece0d0', dark: '#b8a08a' },
          glbUrl: design.glb_url,
          thumbnailUrl: design.thumbnail_url,
        }))

        options.value = newOptions
        selectedOptionId.value = newOptions[0].id

        addAiMessage(
          `<strong>陶语 · 方案生成完成</strong><br/>
          已为您生成 ${newOptions.length} 个设计方案。<br/>
          <em style="color:#8a7d6f;font-size:12px;">👉 点击右侧方案查看 3D，或使用"微调"按钮修改细节。</em>`,
          newOptions.map(o => ({ ...o }))
        )
      } else {
        // 没有返回方案，使用模拟数据兜底
        throw new Error('后端未返回设计方案')
      }
    } catch (error: any) {
      console.error('Send message error:', error)
      ElMessage.error(error.message || '消息发送失败')

      // 失败后回退到 mock 数据
      addAiMessage('抱歉，AI 生成遇到问题，为您展示演示方案')
      await sendUserMessageMock(prompt)
    } finally {
      sending.value = false
    }
  }

  /**
   * Mock 模式（兜底方案）
   */
  async function sendUserMessageMock(prompt: string) {
    await new Promise(resolve => setTimeout(resolve, 300))

    addAiMessage(`<strong>陶语 · 关键词解析</strong><br/>
      🐰 兔子造型 &nbsp;·&nbsp; 🌙 月亮意象 &nbsp;·&nbsp; 🌼 桂花纹样<br/>
      🎨 ${currentGlaze.value} &nbsp;·&nbsp; 📐 玄关尺寸（建议 H 18–24 cm）<br/>
      <em style="color:#8a7d6f;font-size:12px;">正在并行调用三条生成路线…</em>`)

    await new Promise(resolve => setTimeout(resolve, 500))

    const mockOptions: Option[] = [
      {
        id: 'opt-1', idx: '①', name: '玉兔捧月',
        desc: '一只憨态可掬的兔子捧着满月，月亮中空可放干花或小信物。冷白釉主体，点缀桂花细节，适合玄关摆放。',
        glaze: currentGlaze.value, size: 'H 20 × W 16 cm', days: 9, price: 386,
        tags: ['叙事造型', '礼物首选', '冷白釉', '可放干花'], type: 'rabbit',
        colors: { light: '#f5f0e8', mid: '#ece0d0', dark: '#b8a08a' },
      },
      {
        id: 'opt-2', idx: '②', name: '月下垂桂',
        desc: '兔耳化作桂枝造型的流线型花瓶，瓶口如月轮。釉面点缀桂花形凹印，注入清水后有光影浮动。',
        glaze: currentGlaze.value === '冷白釉' ? '青瓷釉' : currentGlaze.value,
        size: 'H 24 × W 14 cm', days: 10, price: 468,
        tags: ['实用花瓶', '桂枝造型', '青瓷釉', '桂花凹印'], type: 'moon-vase',
        colors: { light: '#c8dfe5', mid: '#8aaeb8', dark: '#4a6e7a' },
      },
      {
        id: 'opt-3', idx: '③', name: '望舒',
        desc: '极简月牙形底座摆件。以器型胜，不做多余装饰。适合放在书桌、茶席边，也可做小型香插。',
        glaze: currentGlaze.value === '冷白釉' ? '玉青釉' : currentGlaze.value,
        size: 'H 12 × W 18 cm', days: 7, price: 268,
        tags: ['极简', '茶席摆件', '可做香插', '工期短'], type: 'incense-holder',
        colors: { light: '#d4e8dc', mid: '#8ab89e', dark: '#3a6a52' },
      },
    ]

    options.value = mockOptions
    selectedOptionId.value = mockOptions[0].id

    addAiMessage(
      `<strong>陶语 · 三个方案出炉啦</strong><br/>
      每款方案均已通过工艺校验。<br/>
      <em style="color:#8a7d6f;font-size:12px;">👉 可点击下方方案查看 3D，或用"微调"按钮修改细节。</em>`,
      mockOptions.map(o => ({ ...o }))
    )
  }

  function applyTweak(text: string, pushVersion: (label: string) => void) {
    addUserMessage(text)
    setTimeout(() => {
      addAiMessage(`<strong>陶语 · 已应用微调</strong><br/>「${text}」 → 更新方案参数，正在重新渲染 3D…`)
      const opt = options.value.find(o => o.id === selectedOptionId.value)
      if (opt) {
        if (text.includes('耳朵')) opt.desc += '（已调整：兔耳长度 +15%）'
        if (text.includes('圆润')) opt.colors.light = '#f8f4ec'
        if (text.includes('墨绿')) { opt.colors.dark = '#2d4a48'; opt.tags.push('墨绿装饰线') }
        if (text.includes('桂花')) opt.tags.push('桂花纹理')
        if (text.includes('哑光')) opt.tags.push('哑光质感')
        options.value = [...options.value]
        pushVersion(`微调：${text}`)
      }
    }, 300)
  }

  const tweaks = [
    { text: '耳朵再长一点' }, { text: '整体更圆润' }, { text: '加大底座' },
    { text: '加入桂花纹理' }, { text: '哑光质感' }, { text: '缩小一圈' },
    { text: '加高颈部' }, { text: '加一点墨绿装饰线' },
  ]

  return {
    messages, options, selectedOptionId, inputText, sending, referenceImageUrl,
    tweaks, addAiMessage, addUserMessage, onReferenceUpload, sendUserMessage,
    applyTweak, initSession, sessionId,
  }
}
