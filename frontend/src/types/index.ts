export interface User {
  user_id: string
  phone: string
  role: 'user' | 'studio' | 'admin'
}

export interface LoginResponse {
  role: 'user' | 'studio' | 'admin'
}

export interface Session {
  id: string
  user_id: string
  title: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

export interface DesignParams {
  shape: string
  glaze_color: string
  size: string
  style: string
  emotion: string
  material: string
  usage: string
}

export interface CraftCheck {
  passed: boolean
  issues: string[]
  auto_fixed: boolean
  fixed_mesh_uri?: string
}

export interface DesignOption {
  option_id: string
  name: string
  description: string
  pipeline: 'template' | 'generative' | 'hybrid'
  glb_url: string
  thumbnail_url: string
  craft_check: CraftCheck
  estimated_volume_cm3: number
  estimated_weight_g: number
  price: number
  estimated_days: number
}

export interface Task {
  task_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  options?: string[]
  error?: string
}

export interface SSEEvent {
  stage?: string
  percent?: number
  option_ready?: DesignOption
  done?: { task_id: string; options: string[] }
  error?: { code: string; message: string }
}

// ============ 工作室端 ============

export interface StudioOrderSummary {
  order_id: string
  option_id: string
  design_name: string
  status: string
  total_price: number
  estimated_days: number
  created_at: string
}

export interface StudioOrderDetail {
  order_id: string
  option_id: string
  design_name: string
  design_description: string
  glb_url: string
  thumbnail_url: string
  status: string
  total_price: number
  estimated_days: number
  user_id: string
  studio_id: string | null
  studio_name: string | null
  craft_check: Record<string, any>
  created_at: string
  updated_at: string
}

// ============ 管理后台 ============

export interface StudioListItem {
  studio_id: string
  name: string
  location: string
  specialties: string[]
  capacity: number
  current_load: number
  rating: number
  status: string
  created_at: string
}

export interface AlertItem {
  rule_name: string
  severity: string
  message: string
  triggered_at: string
  labels?: Record<string, string>
}
