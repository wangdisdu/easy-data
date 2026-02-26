import { defineStore } from 'pinia'
import { ref } from 'vue'
import request from '@/utils/request'
import router from '@/router'

interface User {
  id: number
  guid: string
  account: string
  name: string
  email?: string
  phone?: string
}

interface LoginForm {
  username: string
  password: string
}

interface TokenResponse {
  access_token: string
  token_type: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<User | null>(null)

  // 登录
  const login = async (form: LoginForm) => {
    const formData = new FormData()
    formData.append('username', form.username)
    formData.append('password', form.password)

    const response = await request.post<TokenResponse>('/auth/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })

    token.value = response.data.access_token
    localStorage.setItem('token', response.data.access_token)

    // 获取用户信息
    await getUserInfo()

    return response
  }

  // 注册
  const register = async (userData: {
    account: string
    name: string
    passwd: string
    email?: string
    phone?: string
  }) => {
    await request.post('/auth/register', userData)
  }

  // 获取用户信息
  const getUserInfo = async () => {
    try {
      const response = await request.get<User>('/auth/me')
      user.value = response.data
      return response
    } catch (error) {
      logout()
      throw error
    }
  }

  // 退出登录
  const logout = () => {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    router.push('/login')
  }

  // 检查是否已登录
  const isAuthenticated = () => {
    return !!token.value
  }

  return {
    token,
    user,
    login,
    register,
    getUserInfo,
    logout,
    isAuthenticated,
  }
})

