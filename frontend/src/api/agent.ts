import request from '@/utils/request'

export interface Agent {
  id: number
  name: string
  description?: string
  config?: string
  status: string
  extend?: string
  create_time: number
  update_time: number
}

export interface AgentCreate {
  name: string
  description?: string
  config?: string
  status?: string
  extend?: string
}

export interface AgentUpdate {
  name?: string
  description?: string
  config?: string
  status?: string
  extend?: string
}

// 节点配置类型定义
export interface LlmNodeConfig {
  llm_id: number
  script?: string
  tool_ids?: number[]
}

export interface ConditionNodeConfig {
  script: string
  route_mapping: string[]
}

export interface ToolNodeConfig {
  tool_ids: number[]
}

export interface PythonNodeConfig {
  script: string
}

export interface SubgraphNodeConfig {
  agent_id: number  // 注意：前端保存时使用 subgraph_agent_id，但后端 Model 使用 agent_id
}

// 节点配置联合类型
export type NodeConfig = LlmNodeConfig | ConditionNodeConfig | ToolNodeConfig | PythonNodeConfig | SubgraphNodeConfig

export interface AgentGraphNode {
  id: number
  name?: string
  node_type: string
  config?: string // JSON 字符串，根据 node_type 解析为对应的 NodeConfig
  description?: string
  extend?: string
}

export interface AgentGraphEdge {
  from_node_id: number
  to_node_id: number
  from_node_slot: number
  to_node_slot: number
}

export interface AgentGraphModel {
  nodes: AgentGraphNode[]
  edges: AgentGraphEdge[]
}

// 获取智能体列表
export const getAgents = (params?: { skip?: number; limit?: number }) => {
  return request.get<{ data: Agent[]; total: number }>('/agents', { params })
}

// 获取智能体详情
export const getAgent = (id: number) => {
  return request.get<{ data: Agent }>(`/agents/${id}`)
}

// 创建智能体
export const createAgent = (data: AgentCreate) => {
  return request.post<{ data: Agent }>('/agents', data)
}

// 更新智能体
export const updateAgent = (id: number, data: AgentUpdate) => {
  return request.put<{ data: Agent }>(`/agents/${id}`, data)
}

// 删除智能体
export const deleteAgent = (id: number) => {
  return request.delete(`/agents/${id}`)
}

// 获取智能体的完整图形数据（节点和边）
export const getAgentGraph = (agentId: number) => {
  return request.get<{ data: AgentGraphModel }>(`/agents/${agentId}/graph`)
}

// 统一保存智能体的节点和边
export const saveAgentGraph = (agentId: number, data: AgentGraphModel) => {
  return request.post<{ data: AgentGraphModel }>(`/agents/${agentId}/graph`, data)
}
