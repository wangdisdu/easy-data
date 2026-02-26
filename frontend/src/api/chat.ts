import request from '@/utils/request'

export interface ChatMessage {
  message: string
  session_id?: string
}

export interface ChatResponse {
  response: string
  session_id: string
  status: string
}

// 发送消息
export const sendMessage = (data: ChatMessage) => {
  return request.post<ChatResponse>('/chat/message', data)
}

