export interface User {
  user_id: string
  phone: string
  role: 'user' | 'studio' | 'admin'
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
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
