import request from '@/utils/request'

export interface WorkSpace {
  id: number
  code: string
  name: string
  description?: string
  extend?: string
  create_time: number
  update_time: number
}

export interface WorkSpaceCreate {
  code: string
  name: string
  description?: string
  extend?: string
}

export interface WorkSpaceUpdate {
  name?: string
  description?: string
  extend?: string
}

// 获取工作空间列表
export const getWorkspaces = (params?: { skip?: number; limit?: number }) => {
  return request.get<{ data: WorkSpace[]; total: number }>('/workspaces', { params })
}

// 获取工作空间详情
export const getWorkspace = (id: number) => {
  return request.get<{ data: WorkSpace }>(`/workspaces/${id}`)
}

// 创建工作空间
export const createWorkspace = (data: WorkSpaceCreate) => {
  return request.post<{ data: WorkSpace }>('/workspaces', data)
}

// 更新工作空间
export const updateWorkspace = (id: number, data: WorkSpaceUpdate) => {
  return request.put<{ data: WorkSpace }>(`/workspaces/${id}`, data)
}

// 删除工作空间
export const deleteWorkspace = (id: number) => {
  return request.delete<{ data: WorkSpace }>(`/workspaces/${id}`)
}

