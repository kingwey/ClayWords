/**
 * 釉色配置
 *
 * 从 DesignView.vue 抽出：
 * - GLAZE_OPTIONS：可选釉色及其 CSS 渐变（用于按钮与 3D 主体背景）
 * - GLAZE_PALETTE_MAP：釉色 → 三阶调色板（用于 SVG / CSS 实时同步）
 */
import type { GlazeOption, OptionColors } from '@/types/design'

export const GLAZE_OPTIONS: GlazeOption[] = [
  { name: '冷白釉', bg: 'linear-gradient(135deg, #f5f0e8 0%, #ece0d0 60%, #b8a08a 100%)' },
  { name: '青瓷釉', bg: 'linear-gradient(135deg, #9ec6d0 0%, #7B9BA8 60%, #4a6e7a 100%)' },
  { name: '胭脂红', bg: 'linear-gradient(135deg, #e8a598 0%, #c75b5b 60%, #8a2a2a 100%)' },
  { name: '天目釉', bg: 'linear-gradient(135deg, #5a4a3a 0%, #2d2926 60%, #1a1513 100%)' },
  { name: '酱黄釉', bg: 'linear-gradient(135deg, #e8c98a 0%, #d4a574 60%, #8a6a3a 100%)' },
  { name: '玉青釉', bg: 'linear-gradient(135deg, #a8d4b8 0%, #5B8A72 60%, #2a5a48 100%)' },
]

export const GLAZE_PALETTE_MAP: Record<string, OptionColors> = {
  '冷白釉': { light: '#f5f0e8', mid: '#ece0d0', dark: '#b8a08a' },
  '青瓷釉': { light: '#9ec6d0', mid: '#7B9BA8', dark: '#4a6e7a' },
  '胭脂红': { light: '#e8a598', mid: '#c75b5b', dark: '#8a2a2a' },
  '天目釉': { light: '#5a4a3a', mid: '#2d2926', dark: '#1a1513' },
  '酱黄釉': { light: '#e8c98a', mid: '#d4a574', dark: '#8a6a3a' },
  '玉青釉': { light: '#a8d4b8', mid: '#5B8A72', dark: '#2a5a48' },
}
