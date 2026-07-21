import { ref } from 'vue'
import type { Ref } from 'vue'
import type { Message, Option } from '@/types/design'

export function useDesignMessages(currentGlaze: Ref<string>) {
  const messages = ref<Message[]>([])
  const options = ref<Option[]>([])
  const selectedOptionId = ref<string | null>(null)
  const inputText = ref('')
  const sending = ref(false)
  const referenceImageUrl = ref<string | null>(null)

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

  function generateOptionsFromPrompt(_prompt: string): Option[] {
    return [
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
  }

  async function sendUserMessage() {
    if (!inputText.value.trim() || sending.value) return
    const prompt = inputText.value.trim()
    inputText.value = ''
    sending.value = true

    addUserMessage(prompt)

    setTimeout(() => {
      addAiMessage(`<strong>陶语 · 关键词解析</strong><br/>
        🐰 兔子造型 &nbsp;·&nbsp; 🌙 月亮意象 &nbsp;·&nbsp; 🌼 桂花纹样<br/>
        🎨 ${currentGlaze.value} &nbsp;·&nbsp; 📐 玄关尺寸（建议 H 18–24 cm）<br/>
        <em style="color:#8a7d6f;font-size:12px;">正在并行调用三条生成路线…</em>`)
    }, 300)

    setTimeout(() => {
      options.value = [1, 2, 3].map(i => ({
        id: `opt-${i}`, idx: `${i}`, name: `方案 ${i}`, desc: '', glaze: '', size: '', days: 0, price: 0,
        tags: [], type: 'vase' as const, colors: { light: '#f5f0e8', mid: '#ece0d0', dark: '#b8a08a' }, loading: true,
      }))
    }, 800)

    setTimeout(() => {
      const newOptions = generateOptionsFromPrompt(prompt)
      options.value = newOptions
      selectedOptionId.value = newOptions[0].id
      addAiMessage(
        `<strong>陶语 · 三个方案出炉啦</strong><br/>
        每款方案均已通过工艺校验。<br/>
        <em style="color:#8a7d6f;font-size:12px;">👉 可点击下方方案查看 3D，或用"微调"按钮修改细节。</em>`,
        newOptions.map(o => ({ ...o }))
      )
      sending.value = false
    }, 1800)
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
    tweaks, addAiMessage, addUserMessage, onReferenceUpload, sendUserMessage, applyTweak,
  }
}
