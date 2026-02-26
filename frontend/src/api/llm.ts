import request from '@/utils/request'

export interface Llm {
  id: number
  provider: string
  api_key?: string
  base_url?: string
  model: string
  setting?: string
  description?: string
  extend?: string
  create_time: number
  update_time: number
}

export interface LlmCreate {
  provider: string
  api_key?: string
  base_url?: string
  model: string
  setting?: string
  description?: string
  extend?: string
}

export interface LlmUpdate {
  provider?: string
  api_key?: string
  base_url?: string
  model?: string
  setting?: string
  description?: string
  extend?: string
}

// 获取LLM列表
export const getLlms = (params?: { skip?: number; limit?: number }) => {
  return request.get<{ data: Llm[]; total: number }>('/llms', { params })
}

// 获取LLM详情
export const getLlm = (id: number) => {
  return request.get<{ data: Llm }>(`/llms/${id}`)
}

// 创建LLM
export const createLlm = (data: LlmCreate) => {
  return request.post<{ data: Llm }>('/llms', data)
}

// 更新LLM
export const updateLlm = (id: number, data: LlmUpdate) => {
  return request.put<{ data: Llm }>(`/llms/${id}`, data)
}

// 删除LLM
export const deleteLlm = (id: number) => {
  return request.delete(`/llms/${id}`)
}
