/**
 * 对话式设计台共享类型
 *
 * 从 DesignView.vue 抽出，供 ChatPanel / OptionCards / PreviewCanvas /
 * DispatchPanel 等子组件共用，保证方案对象结构在各处一致。
 */

export interface OptionColors {
  light: string
  mid: string
  dark: string
}

export interface Option {
  id: string
  idx: string
  name: string
  desc: string
  glaze: string
  size: string
  days: number
  price: number
  tags: string[]
  type: 'rabbit' | 'moon-vase' | 'incense-holder' | 'vase'
  colors: OptionColors
  loading?: boolean
}

export interface Message {
  role: 'user' | 'ai'
  content: string
  options?: Option[]
  showDispatch?: boolean
}

export interface GlazeOption {
  name: string
  bg: string
}

export interface Studio {
  id: string
  name: string
  scores: { craft: number; capacity: number; geo: number; rating: number }
  totalScore: number
}
