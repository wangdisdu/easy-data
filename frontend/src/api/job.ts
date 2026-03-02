import request from '@/utils/request'

export interface Job {
  id: number
  type: string
  status: string
  setting?: string
  description?: string
  extend?: string
  begin_time?: number
  end_time?: number
  create_time: number
  update_time: number
}

export interface JobLog {
  id: number
  job_id: number
  content: string
  create_time: number
}

export interface JobCreate {
  type?: string
  setting: string
  description?: string
}

export const createJob = (data: JobCreate) => {
  return request.post<{ data: Job }>('/jobs', data)
}

export const getJobs = (params?: { skip?: number; limit?: number }) => {
  return request.get<{ data: Job[]; total: number }>('/jobs', { params })
}

export const getJob = (id: number) => {
  return request.get<{ data: Job }>(`/jobs/${id}`)
}

export const deleteJob = (id: number) => {
  return request.delete<{ data: Job }>(`/jobs/${id}`)
}

export const getJobLogs = (id: number) => {
  return request.get<{ data: JobLog[] }>(`/jobs/${id}/logs`)
}
