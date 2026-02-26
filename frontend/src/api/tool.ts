import request from '@/utils/request'

export interface Tool {
  id: number
  tool: string
  description?: string
  parameters?: string
  content?: string
  extend?: string
  create_time: number
  update_time: number
}

export interface ToolCreate {
  tool: string
  description?: string
  parameters?: string
  content?: string
  extend?: string
}

export interface ToolUpdate {
  tool?: string
  description?: string
  parameters?: string
  content?: string
  extend?: string
}

// 获取工具列表
export const getTools = (params?: { skip?: number; limit?: number }) => {
  return request.get<{ data: Tool[]; total: number }>('/tools', { params })
}

// 获取工具详情
export const getTool = (id: number) => {
  return request.get<{ data: Tool }>(`/tools/${id}`)
}

// 创建工具
export const createTool = (data: ToolCreate) => {
  return request.post<{ data: Tool }>('/tools', data)
}

// 更新工具
export const updateTool = (id: number, data: ToolUpdate) => {
  return request.put<{ data: Tool }>(`/tools/${id}`, data)
}

// 删除工具
export const deleteTool = (id: number) => {
  return request.delete(`/tools/${id}`)
}
