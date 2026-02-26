import request from '@/utils/request'

export interface DataModel {
  id: number
  code: string
  name: string
  platform: string
  type?: string  // 模型类型：table-表，view-视图
  ds_id?: number
  semantic?: string
  summary?: string
  knowledge?: string
  description?: string
  extend?: string
  create_time: number
  update_time: number
  workspace_ids?: number[]
}

export interface DataModelCreate {
  code: string
  name: string
  platform: string
  type?: string  // 模型类型：table-表，view-视图
  ds_id?: number
  semantic?: string
  summary?: string
  knowledge?: string
  description?: string
  extend?: string
  workspace_ids?: number[]
}

export interface DataModelUpdate {
  name?: string
  platform?: string
  type?: string  // 模型类型：table-表，view-视图
  ds_id?: number
  semantic?: string
  summary?: string
  knowledge?: string
  description?: string
  extend?: string
  workspace_ids?: number[]
}

// 获取数据模型列表
export const getDataModels = (params?: { skip?: number; limit?: number }) => {
  return request.get<{ data: DataModel[]; total: number }>('/data-models', { params })
}

// 获取数据模型详情
export const getDataModel = (id: number) => {
  return request.get<{ data: DataModel }>(`/data-models/${id}`)
}

// 创建数据模型
export const createDataModel = (data: DataModelCreate) => {
  return request.post<{ data: DataModel }>('/data-models', data)
}

// 更新数据模型
export const updateDataModel = (id: number, data: DataModelUpdate) => {
  return request.put<{ data: DataModel }>(`/data-models/${id}`, data)
}

// 删除数据模型
export const deleteDataModel = (id: number) => {
  return request.delete<{ data: DataModel }>(`/data-models/${id}`)
}

