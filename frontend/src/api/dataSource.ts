import request from '@/utils/request'

export interface DataSource {
  id: number
  code: string
  name: string
  platform: string
  setting: string
  semantic?: string
  description?: string
  extend?: string
  create_time: number
  update_time: number
  workspace_ids?: number[]
}

export interface DataSourceCreate {
  code: string
  name: string
  platform: string
  setting: string
  semantic?: string
  description?: string
  extend?: string
  workspace_ids?: number[]
}

export interface DataSourceUpdate {
  name?: string
  platform?: string
  setting?: string
  semantic?: string
  description?: string
  extend?: string
  workspace_ids?: number[]
}

export interface ConnectionTest {
  success: boolean
  message: string
}

// 获取数据源列表
export const getDataSources = (params?: { skip?: number; limit?: number }) => {
  return request.get<{ data: DataSource[]; total: number }>('/data-sources', { params })
}

// 获取数据源详情
export const getDataSource = (id: number) => {
  return request.get<{ data: DataSource }>(`/data-sources/${id}`)
}

// 创建数据源
export const createDataSource = (data: DataSourceCreate) => {
  return request.post<{ data: DataSource }>('/data-sources', data)
}

// 更新数据源
export const updateDataSource = (id: number, data: DataSourceUpdate) => {
  return request.put<{ data: DataSource }>(`/data-sources/${id}`, data)
}

// 删除数据源
export const deleteDataSource = (id: number) => {
  return request.delete(`/data-sources/${id}`)
}

// 测试数据源连接
export const testDataSource = (id: number, data: DataSourceCreate | { platform: string; setting: string }) => {
  return request.post<{ data: ConnectionTest }>(`/data-sources/${id}/test`, data)
}

// 获取数据源的表和视图列表
export const getDataSourceTables = (id: number, params?: { database?: string; schema?: string }) => {
  return request.get<{ data: { tables: string[]; views: string[] } }>(`/data-sources/${id}/tables`, { params })
}

// 获取表结构信息
export const getTableStructure = (dataSourceId: number, tableName: string, params?: { database?: string; schema?: string }) => {
  return request.get<{ data: Array<{ field_name: string; data_type: string; is_nullable?: boolean; is_primary_key?: boolean; default_value?: string; comment?: string }> }>(`/data-sources/${dataSourceId}/tables/${tableName}/structure`, { params })
}

// 执行SQL查询
export const executeSqlQuery = (dataSourceId: number, sql: string, params?: Record<string, any>) => {
  return request.post<{ data: Record<string, any>[] }>(`/data-sources/${dataSourceId}/execute-sql`, {
    sql,
    params
  })
}

