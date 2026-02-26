import axios from 'axios'
import type { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios'
import { message } from 'ant-design-vue'
import { useAuthStore } from '@/stores/auth'

// 创建 axios 实例
// 使用相对路径，开发环境通过 Vite 代理转发到 localhost:8000
const service: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// 请求拦截器
service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const authStore = useAuthStore()
    const token = authStore.token
    
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    return config
  },
  (error) => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  (response: AxiosResponse) => {
    // 如果HTTP状态码为200，检查业务响应码
    if (response.status === 200) {
      const res = response.data
      // 根据Resp类的code字段判断是否成功，0000表示成功
      if (res.code === '0000') {
        return res
      } else {
        // 失败时显示msg字段的错误信息
        message.error(res.msg || '请求失败')
        return Promise.reject(new Error(res.msg || '请求失败'))
      }
    } else {
      // 其他HTTP状态码的处理
      message.error(`请求失败，状态码：${response.status}`)
      return Promise.reject(new Error(`请求失败，状态码：${response.status}`))
    }
  },
  (error) => {
    console.error('响应错误:', error)
    
    if (error.response) {
      const { status } = error.response
      
      switch (status) {
        case 401:
          message.error('未授权，请重新登录')
          const authStore = useAuthStore()
          authStore.logout()
          break
        case 403:
          message.error('拒绝访问')
          break
        case 404:
          message.error('请求错误，未找到该资源')
          break
        case 500:
          message.error('服务器错误')
          break
        default:
          message.error(`请示失败${status}`)
      }
    } else {
      message.error('网络连接失败')
    }
    
    return Promise.reject(error)
  }
)

export default service

