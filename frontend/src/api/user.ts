import request from '@/utils/request'

export interface User {
  id: number
  guid: string
  account: string
  name: string
  email?: string
  phone?: string
  create_time: number
  update_time: number
}

export interface UserUpdate {
  name?: string
  email?: string
  phone?: string
}

// 获取用户列表
export const getUsers = (params?: { skip?: number; limit?: number }) => {
  return request.get<{ data: User[]; total: number }>('/users', { params })
}

// 获取用户详情
export const getUser = (id: number) => {
  return request.get<{ data: User }>(`/users/${id}`)
}

// 更新用户
export const updateUser = (id: number, data: UserUpdate) => {
  return request.put<{ data: User }>(`/users/${id}`, data)
}

// 删除用户
export const deleteUser = (id: number) => {
  return request.delete<{ data: User }>(`/users/${id}`)
}

