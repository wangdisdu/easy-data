import request from '@/utils/request'

export interface LlmDefaultStatus {
  configured: boolean
}

export interface InitLlmBody {
  provider: string
  model: string
  api_key?: string
  base_url?: string
}

/** 获取默认 LLM（id=1）是否已配置，无需登录 */
export const getLlmDefaultStatus = () => {
  return request.get<{ data: LlmDefaultStatus }>('/system/llm-default-status')
}

/** 系统初始化：更新默认 LLM 的 provider、api_key、base_url，无需登录 */
export const initLlm = (data: InitLlmBody) => {
  return request.post<{ data: { ok: boolean } }>('/system/init-llm', data)
}
