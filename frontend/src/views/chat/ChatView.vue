<template>
  <div class="chat-container">
    <a-layout class="chat-layout">
      <!-- 对话区域 -->
      <a-layout-content class="chat-content">
        <div class="chat-messages" ref="messagesContainer">
          <div
            v-for="(message, index) in messages"
            :key="index"
            :class="['message-item', message.type === 'user' ? 'user-message' : 'ai-message']"
          >
            <div class="message-avatar">
              <a-avatar v-if="message.type === 'user'" :size="40" style="background-color: #1890ff">
                我
              </a-avatar>
              <a-avatar v-else :size="40" style="background-color: #52c41a">
                AI
              </a-avatar>
            </div>
            <div class="message-content">
              <!-- 结构化消息部分 -->
              <div v-if="message.type === 'ai' && message.parts && message.parts.length > 0" class="message-parts">
                <div v-for="(part, partIndex) in message.parts" :key="partIndex" class="message-part">
                  <!-- 文本内容 -->
                  <div
                    v-if="part.type === 'text'"
                    class="message-text ai-message-text"
                    v-html="formatMessage(part.content, message.type)"
                  ></div>

                  <!-- 调用工具 -->
                  <div v-else-if="part.type === 'tool_call'" class="tool-call-container">
                    <div class="tool-call-header" @click="toggleToolPart(message, partIndex)">
                      <div class="tool-call-icon">
                        <CaretRightOutlined v-if="!part.expanded" />
                        <CaretDownOutlined v-else />
                      </div>
                      <span class="tool-call-title">🔧 调用工具</span>
                      <span class="tool-call-id">ID: {{ part.tool_call_id }}</span>
                      <ArrowRightOutlined />
                    </div>
                    <div v-show="part.expanded" class="tool-call-content">
                      <div class="message-text ai-message-text" v-html="formatMessage(part.content, message.type)"></div>
                    </div>
                  </div>

                  <!-- 工具结果 -->
                  <div v-else-if="part.type === 'tool_result'" class="tool-result-container">
                    <div class="tool-result-header" @click="toggleToolPart(message, partIndex)">
                      <div class="tool-result-icon">
                        <CaretRightOutlined v-if="!part.expanded" />
                        <CaretDownOutlined v-else />
                      </div>
                      <span class="tool-result-title">🔧 工具结果</span>
                      <span class="tool-result-id">ID: {{ part.tool_result_id }}</span>
                      <ArrowLeftOutlined />
                    </div>
                    <div v-show="part.expanded" class="tool-result-content">
                      <div class="message-text ai-message-text" v-html="formatMessage(part.content, message.type)"></div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 兼容旧格式：如果没有 parts，使用 content -->
              <div
                v-else
                class="message-text"
                :class="{ 'ai-message-text': message.type === 'ai' }"
                v-html="formatMessage(message.content, message.type)"
              ></div>

              <div class="message-time-wrapper">
                <span class="message-time">{{ formatTime(message.timestamp) }}</span>
                <a-spin v-if="message.streaming" size="small" style="margin-left: 8px" />
              </div>
            </div>
          </div>
          <div v-if="loading" class="message-item ai-message">
            <div class="message-avatar">
              <a-avatar :size="40" style="background-color: #52c41a">AI</a-avatar>
            </div>
            <div class="message-content">
              <a-spin />
            </div>
          </div>
        </div>

        <!-- 输入区域：多行输入框 -->
        <div class="chat-input-area">
          <div class="input-wrapper">
            <a-textarea
              v-model:value="inputMessage"
              placeholder="输入您的问题，例如：你能做什么？"
              :auto-size="{ minRows: 2, maxRows: 6 }"
              :disabled="loading || !isConnected"
              @keydown.enter.exact.prevent="sendMessage"
            />
            <div class="input-actions">
              <span class="input-hint">Enter 发送 · Shift+Enter 换行</span>
              <div class="input-buttons">
                <a-button
                  type="text"
                  :icon="h(SettingOutlined)"
                  @click="showAgentSelector = true"
                  :title="selectedAgentId ? `当前: ${getAgentName(selectedAgentId)}` : '当前: 主智能体'"
                />
                <a-button
                  type="primary"
                  :loading="loading"
                  @click="sendMessage"
                  :disabled="!inputMessage.trim() || !isConnected"
                >
                  发送
                </a-button>
              </div>
            </div>
          </div>
          <div v-if="!isConnected" class="connection-status">
            <a-alert message="连接已断开，正在重连..." type="warning" show-icon style="margin-top: 8px" />
          </div>
        </div>

        <!-- Agent 选择器弹窗：使用 antd 组件简化 -->
        <a-modal
          v-model:open="showAgentSelector"
          title="选择智能体"
          :footer="null"
          width="400px"
          @open="loadAgents"
        >
          <a-spin :spinning="loadingAgents" tip="加载中...">
            <div v-if="loadingAgents" style="min-height: 120px" />
            <a-empty v-else-if="agents.length === 0" description="暂无智能体" />
            <a-radio-group
              v-else
              v-model:value="selectedAgentId"
              @change="handleAgentChange"
              style="width: 100%"
            >
              <a-space direction="vertical" :style="{ width: '100%' }">
                <a-radio :value="undefined">
                  <div>主智能体</div>
                  <div class="agent-option-desc">使用系统默认智能体</div>
                </a-radio>
                <a-radio v-for="agent in agents" :key="agent.id" :value="agent.id">
                  <div>{{ agent.name }}</div>
                  <div class="agent-option-desc">{{ agent.description || '暂无描述' }}</div>
                </a-radio>
              </a-space>
            </a-radio-group>
          </a-spin>
        </a-modal>
      </a-layout-content>
    </a-layout>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, computed, h } from 'vue'
import { message } from 'ant-design-vue'
import { CaretRightOutlined, CaretDownOutlined, ArrowRightOutlined, ArrowLeftOutlined, SettingOutlined } from '@ant-design/icons-vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { renderMarkdown } from '@/utils/markdown'
import { getAgents, type Agent } from '@/api/agent'

const router = useRouter()

interface MessagePart {
  type: 'text' | 'tool_call' | 'tool_result'
  content: string
  tool_call_id?: string
  tool_result_id?: string
  expanded?: boolean // 用于控制折叠/展开状态
}

interface ChatMessage {
  type: 'user' | 'ai'
  content: string
  parts: MessagePart[] // 结构化消息部分
  timestamp: number
  streaming?: boolean // 标记是否正在流式输出
}

const messages = ref<ChatMessage[]>([])
const inputMessage = ref('')
const loading = ref(false)
const messagesContainer = ref<HTMLElement>()
const ws = ref<WebSocket | null>(null)
const isConnected = ref(false)
const currentStreamingMessageIndex = ref<number>(-1) // 当前正在流式输出的消息索引
const selectedAgentId = ref<number | undefined>(undefined)
const agents = ref<Agent[]>([])
const showAgentSelector = ref(false)
const loadingAgents = ref(false)

const getAgentName = (agentId: number | undefined): string => {
  if (agentId === undefined) {
    return '主智能体'
  }
  const agent = agents.value.find(a => a.id === agentId)
  return agent ? agent.name : `智能体 ${agentId}`
}

const formatMessage = (content: string, type: 'user' | 'ai') => {
  if (!content) return ''

  // AI 消息使用 Markdown 渲染
  if (type === 'ai') {
    return renderMarkdown(content)
  }

  // 用户消息使用简单的 HTML 转义和换行处理
  return content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
}

const formatTime = (timestamp: number) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 切换工具部分的展开/折叠状态
const toggleToolPart = (message: ChatMessage, partIndex: number) => {
  if (message.parts && message.parts[partIndex]) {
    message.parts[partIndex].expanded = !message.parts[partIndex].expanded
  }
}

// 加载智能体列表
const loadAgents = async () => {
  if (loadingAgents.value) return
  loadingAgents.value = true
  try {
    const response = await getAgents({ limit: 100 })
    console.log('getAgents 完整响应:', response)
    // 只展示启用状态的智能体（status=active）
    agents.value = (response.data || []).filter((a) => a.status === 'active')
    console.log('加载的智能体列表:', agents.value)
    console.log('智能体数量:', agents.value.length)
  } catch (error) {
    console.error('加载智能体列表失败:', error)
    message.error('加载智能体列表失败')
  } finally {
    loadingAgents.value = false
  }
}

// 处理智能体切换
const handleAgentChange = () => {
  // 关闭选择器弹窗
  showAgentSelector.value = false
  // 切换智能体时，断开当前连接并重新连接
  if (ws.value) {
    ws.value.close()
    ws.value = null
    isConnected.value = false
  }
  // 重新初始化连接
  initWebSocket()
}

// 初始化 WebSocket 连接
const initWebSocket = async () => {
  const authStore = useAuthStore()

  // 检查登录状态
  if (!authStore.isAuthenticated()) {
    message.warning('请先登录后再使用聊天功能')
    // 跳转到登录页，登录后返回当前页面
    router.push({
      name: 'login',
      query: { redirect: router.currentRoute.value.fullPath }
    })
    return
  }

  const token = authStore.token
  if (!token) {
    message.error('获取认证信息失败，请重新登录')
    router.push({
      name: 'login',
      query: { redirect: router.currentRoute.value.fullPath }
    })
    return
  }

  // 验证 token 是否合法
  try {
    await authStore.getUserInfo()
  } catch (error) {
    // token 无效，清除并跳转到登录页
    message.error('认证信息已过期，请重新登录')
    authStore.logout()
    router.push({
      name: 'login',
      query: { redirect: router.currentRoute.value.fullPath }
    })
    return
  }

  // 转换为 WebSocket 协议
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  // 如果选择了智能体，使用智能体接口，否则使用主智能体接口
  const wsUrl = selectedAgentId.value
    ? `${protocol}//${host}/api/v1/ws/chat/${selectedAgentId.value}?token=${token}`
    : `${protocol}//${host}/api/v1/ws/chat/main?token=${token}`

  try {
    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      console.log('WebSocket 连接已建立')
      isConnected.value = true
    }

    ws.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        // 处理连接成功消息
        if (data.type === 'connection' && data.status === 'success') {
          console.log('WebSocket 连接认证成功:', data.message)
          return
        }

        // 处理错误消息
        if (data.type === 'error' || data.status === 'error') {
          message.error(data.message || '服务器返回错误')
          loading.value = false
          // 如果正在流式输出，结束流式状态
          if (currentStreamingMessageIndex.value >= 0) {
            if (messages.value[currentStreamingMessageIndex.value]) {
              messages.value[currentStreamingMessageIndex.value].streaming = false
            }
            currentStreamingMessageIndex.value = -1
          }
          return
        }

        // 处理流式输出开始
        if (data.type === 'stream_start') {
          // 创建一个新的 AI 消息，标记为流式输出
          const aiMessage: ChatMessage = {
            type: 'ai',
            content: '',
            parts: [],
            timestamp: Date.now(),
            streaming: true
          }
          messages.value.push(aiMessage)
          currentStreamingMessageIndex.value = messages.value.length - 1
          loading.value = false // 开始接收流式数据，不再显示 loading
          scrollToBottom()
          return
        }

        // 处理流式数据块
        if (data.type === 'stream_chunk' && data.chunk) {
          if (currentStreamingMessageIndex.value >= 0) {
            const currentMessage = messages.value[currentStreamingMessageIndex.value]
            if (currentMessage) {
              // 追加内容到字符串
              currentMessage.content += data.chunk

              // 处理工具调用或工具调用结果
              if (data.tool_call_id || data.tool_result_id) {
                // 检查是否已经有对应的部分
                let targetPart: MessagePart | undefined

                if (data.tool_call_id) {
                  // 查找或创建工具调用部分
                  targetPart = currentMessage.parts.find(p => p.type === 'tool_call' && p.tool_call_id === data.tool_call_id)
                  if (!targetPart) {
                    // 如果有文本内容，先保存为文本部分
                    const textContent = currentMessage.content.slice(0, -data.chunk.length)
                    if (textContent.trim()) {
                      const lastPart = currentMessage.parts[currentMessage.parts.length - 1]
                      if (!lastPart || lastPart.type !== 'text') {
                        currentMessage.parts.push({
                          type: 'text',
                          content: textContent,
                          expanded: true
                        })
                      } else {
                        lastPart.content = textContent
                      }
                      currentMessage.content = ''
                    }
                    // 创建新的工具调用部分
                    targetPart = {
                      type: 'tool_call',
                      content: data.chunk,
                      tool_call_id: data.tool_call_id,
                      expanded: false // 默认折叠
                    }
                    currentMessage.parts.push(targetPart)
                    currentMessage.content = ''
                  } else {
                    // 追加到现有工具调用部分
                    targetPart.content += data.chunk
                    currentMessage.content = ''
                  }
                } else if (data.tool_result_id) {
                  // 查找或创建工具调用结果部分
                  targetPart = currentMessage.parts.find(p => p.type === 'tool_result' && p.tool_result_id === data.tool_result_id)
                  if (!targetPart) {
                    // 如果有文本内容，先保存为文本部分
                    const textContent = currentMessage.content.slice(0, -data.chunk.length)
                    if (textContent.trim()) {
                      const lastPart = currentMessage.parts[currentMessage.parts.length - 1]
                      if (!lastPart || lastPart.type !== 'text') {
                        currentMessage.parts.push({
                          type: 'text',
                          content: textContent,
                          expanded: true
                        })
                      } else {
                        lastPart.content = textContent
                      }
                      currentMessage.content = ''
                    }
                    // 创建新的工具调用结果部分
                    targetPart = {
                      type: 'tool_result',
                      content: data.chunk,
                      tool_result_id: data.tool_result_id,
                      expanded: false // 默认折叠
                    }
                    currentMessage.parts.push(targetPart)
                    currentMessage.content = ''
                  } else {
                    // 追加到现有工具调用结果部分
                    targetPart.content += data.chunk
                    currentMessage.content = ''
                  }
                }
              } else {
                // 普通文本内容，检查最后一部分是否为文本类型
                let lastPart = currentMessage.parts[currentMessage.parts.length - 1]
                if (lastPart && lastPart.type === 'text') {
                  // 追加到最后一个文本部分
                  lastPart.content = currentMessage.content
                } else {
                  // 创建新的文本部分
                  currentMessage.parts.push({
                    type: 'text',
                    content: currentMessage.content,
                    expanded: true
                  })
                }
              }

              scrollToBottom()
            }
          }
          return
        }

        // 处理流式输出结束
        if (data.type === 'stream_end') {
          if (currentStreamingMessageIndex.value >= 0) {
            const currentMessage = messages.value[currentStreamingMessageIndex.value]
            if (currentMessage) {
              // 更新最终内容（如果有完整响应）
              if (data.response) {
                currentMessage.content = data.response
              }

              // 如果有剩余的文本内容，添加到 parts
              if (currentMessage.content.trim()) {
                const lastPart = currentMessage.parts[currentMessage.parts.length - 1]
                if (lastPart && lastPart.type === 'text') {
                  lastPart.content = currentMessage.content
                } else {
                  currentMessage.parts.push({
                    type: 'text',
                    content: currentMessage.content,
                    expanded: true
                  })
                }
                currentMessage.content = ''
              }

              // 结束流式状态
              currentMessage.streaming = false
            }
            currentStreamingMessageIndex.value = -1
          }
          loading.value = false
          scrollToBottom()
          return
        }

      } catch (error) {
        console.error('解析消息失败:', error)
        loading.value = false
        // 如果正在流式输出，结束流式状态
        if (currentStreamingMessageIndex.value >= 0) {
          if (messages.value[currentStreamingMessageIndex.value]) {
            messages.value[currentStreamingMessageIndex.value].streaming = false
          }
          currentStreamingMessageIndex.value = -1
        }
      }
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket 错误:', error)
      message.error('连接错误，请刷新页面重试')
      isConnected.value = false
      loading.value = false
    }

    ws.value.onclose = (event) => {
      console.log('WebSocket 连接已关闭', event.code, event.reason)
      isConnected.value = false
      loading.value = false

      // 如果是认证失败导致的关闭，提示用户重新登录
      if (event.code === 1008) {
        message.error(event.reason || '认证失败，请重新登录')
        authStore.logout()
      }
    }
  } catch (error) {
    console.error('WebSocket 连接失败:', error)
    message.error('连接失败，请刷新页面重试')
    isConnected.value = false
  }
}

const sendMessage = () => {
  const messageText = inputMessage.value.trim()
  if (!messageText || loading.value || !isConnected.value) return

  // 添加用户消息
  messages.value.push({
    type: 'user',
    content: messageText,
    timestamp: Date.now(),
  })

  inputMessage.value = ''
  loading.value = true
  scrollToBottom()

  // 通过 WebSocket 发送消息
  if (ws.value && ws.value.readyState === WebSocket.OPEN) {
    ws.value.send(JSON.stringify({ message: messageText }))
  } else {
    message.error('连接未建立，请刷新页面重试')
    loading.value = false
  }
}

onMounted(() => {
  loadAgents()
  // 添加欢迎消息
  messages.value.push({
    type: 'ai',
    content: '您好！我是 Easy Data 智能助手，可以帮您分析数据。请告诉我您想要分析什么？',
    parts: [{
      type: 'text',
      content: '您好！我是 Easy Data 智能助手，可以帮您分析数据。请告诉我您想要分析什么？',
      expanded: true
    }],
    timestamp: Date.now(),
  })

  // 初始化 WebSocket 连接
  initWebSocket()
})

onUnmounted(() => {
  // 关闭 WebSocket 连接
  if (ws.value) {
    ws.value.close()
    ws.value = null
  }
})
</script>

<style scoped>
.chat-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.chat-content {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f5f5;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.user-message {
  flex-direction: row-reverse;
}

.message-content {
  flex: 1;
  max-width: 70%;
}

.user-message .message-content {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.ai-message .message-content {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.message-text {
  padding: 12px 16px;
  border-radius: 8px;
  word-wrap: break-word;
  line-height: 1.6;
}

.user-message .message-text {
  background: #1890ff;
  color: white;
}

.ai-message .message-text {
  background: white;
  color: #333;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* Markdown 样式优化 */
.ai-message-text {
  font-size: 14px;
}

.ai-message-text :deep(h1),
.ai-message-text :deep(h2),
.ai-message-text :deep(h3),
.ai-message-text :deep(h4),
.ai-message-text :deep(h5),
.ai-message-text :deep(h6) {
  margin-top: 16px;
  margin-bottom: 8px;
  font-weight: 600;
  line-height: 1.25;
}

.ai-message-text :deep(h1) {
  font-size: 1.5em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 0.3em;
}

.ai-message-text :deep(h2) {
  font-size: 1.3em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 0.3em;
}

.ai-message-text :deep(h3) {
  font-size: 1.1em;
}

.ai-message-text :deep(p) {
  margin-bottom: 10px;
}

.ai-message-text :deep(ul),
.ai-message-text :deep(ol) {
  margin-bottom: 10px;
  padding-left: 24px;
}

.ai-message-text :deep(li) {
  margin-bottom: 4px;
}

.ai-message-text :deep(blockquote) {
  margin: 10px 0;
  padding: 0 16px;
  color: #6a737d;
  border-left: 4px solid #dfe2e5;
}

.ai-message-text :deep(code) {
  padding: 2px 6px;
  margin: 0 2px;
  font-size: 85%;
  background-color: rgba(27, 31, 35, 0.05);
  border-radius: 3px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
}

.ai-message-text :deep(pre) {
  margin: 10px 0;
  padding: 12px 16px;
  overflow-x: auto;
  background-color: #f6f8fa;
  border-radius: 6px;
  line-height: 1.45;
}

.ai-message-text :deep(pre code) {
  display: inline;
  padding: 0;
  margin: 0;
  overflow: visible;
  line-height: inherit;
  word-wrap: normal;
  background-color: transparent;
  border: 0;
  font-size: 100%;
}

.ai-message-text :deep(table) {
  border-collapse: collapse;
  margin: 10px 0;
  width: 100%;
  display: block;
  overflow-x: auto;
}

.ai-message-text :deep(thead) {
  background-color: #f6f8fa;
}

.ai-message-text :deep(th),
.ai-message-text :deep(td) {
  padding: 8px 12px;
  border: 1px solid #dfe2e5;
  text-align: left;
}

.ai-message-text :deep(th) {
  font-weight: 600;
}

.ai-message-text :deep(a) {
  color: #1890ff;
  text-decoration: none;
}

.ai-message-text :deep(a:hover) {
  text-decoration: underline;
}

.ai-message-text :deep(hr) {
  margin: 16px 0;
  border: 0;
  border-top: 1px solid #eaecef;
}

.ai-message-text :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  margin: 10px 0;
}

.message-time-wrapper {
  display: flex;
  align-items: center;
  margin-top: 4px;
}

.message-time {
  font-size: 12px;
  color: #999;
}

.chat-input-area {
  margin: 0 20px 16px;
  padding: 16px 20px;
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 12px;
  box-shadow: 0 -1px 4px rgba(0, 0, 0, 0.04);
}

.input-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-wrapper :deep(.ant-input) {
  resize: none;
}

.input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.input-hint {
  font-size: 12px;
  color: #8c8c8c;
}

.input-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
}

.agent-option-desc {
  font-size: 12px;
  color: #8c8c8c;
  margin-top: 2px;
}

/* 消息部分样式 */
.message-parts {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.message-part {
  display: flex;
  flex-direction: column;
}

/* 工具调用样式 */
.tool-call-container,
.tool-result-container {
  border-radius: 8px;
  overflow: hidden;
  margin: 4px 0;
}

.tool-call-container {
  background: #fafafa;
  border: 1px solid #d9d9d9;
}

.tool-result-container {
  background: #fafafa;
  border: 1px solid #d9d9d9;
}

.tool-call-header,
.tool-result-header {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  user-select: none;
  transition: background-color 0.2s;
}

.tool-call-header:hover {
  background-color: #f0f0f0;
}

.tool-result-header:hover {
  background-color: #f0f0f0;
}

.tool-call-icon,
.tool-result-icon {
  margin-right: 8px;
  color: #8c8c8c;
  font-size: 12px;
  transition: transform 0.2s;
}

.tool-result-icon {
  color: #8c8c8c;
}

.tool-call-title,
.tool-result-title {
  font-weight: 500;
  font-size: 13px;
  flex: 1;
  color: #595959;
}

.tool-call-title {
  color: #595959;
}

.tool-result-title {
  color: #595959;
}

.tool-call-id,
.tool-result-id {
  font-size: 11px;
  color: #8c8c8c;
  margin-left: 8px;
  margin-right: 8px;
}

/* 箭头图标样式 */
.tool-call-header :deep(.anticon-arrow-right),
.tool-result-header :deep(.anticon-arrow-left) {
  font-size: 12px;
  color: #bfbfbf;
}

.tool-call-content,
.tool-result-content {
  padding: 12px;
  background: white;
  border-top: 1px solid #e8e8e8;
}

.tool-result-content {
  background: #fafafa;
}

</style>

