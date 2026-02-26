<template>
  <div class="llm-list">
    <div class="page-header">
      <h1>LLM模型管理</h1>
      <a-button type="primary" @click="showCreateModal">
        <PlusOutlined />
        新建模型
      </a-button>
    </div>

    <a-table
      :columns="columns"
      :data-source="llmList"
      :loading="loading"
      :pagination="pagination"
      row-key="id"
      @change="handleTableChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'provider'">
          <a-tag :color="getProviderColor(record.provider)">
            {{ record.provider }}
          </a-tag>
        </template>
        <template v-if="column.key === 'api_key'">
          <span v-if="record.api_key">{{ maskApiKey(record.api_key) }}</span>
          <span v-else style="color: #999">未设置</span>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button type="link" @click="handleEdit(record)">编辑</a-button>
            <a-popconfirm title="确定要删除吗？" @confirm="handleDelete(record.id)">
              <a-button type="link" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 创建/编辑弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="modalTitle"
      @ok="handleSubmit"
      :confirm-loading="submitLoading"
      width="800px"
    >
      <a-form :model="form" :rules="formRules" ref="formRef" layout="vertical">
        <a-form-item name="provider" label="模型提供商">
          <a-select v-model:value="form.provider" placeholder="请选择模型提供商" @change="handleProviderChange">
            <a-select-option value="openai">OpenAI</a-select-option>
            <a-select-option value="bailian">阿里云百炼</a-select-option>
            <a-select-option value="bigmodel">智谱模型</a-select-option>
            <a-select-option value="volcengine">火山引擎</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item name="api_key" label="API密钥">
          <a-input-password v-model:value="form.api_key" placeholder="请输入API密钥（可选）" />
        </a-form-item>
        <a-form-item name="base_url" label="API基础URL">
          <a-input v-model:value="form.base_url" placeholder="请输入API基础URL（可选）" />
        </a-form-item>
        <a-form-item name="model" label="模型名称">
          <a-input v-model:value="form.model" placeholder="请输入模型名称（如：gpt-4, qwen-max等）" />
        </a-form-item>
        <a-form-item name="setting" label="其他配置信息">
          <a-textarea
            v-model:value="form.setting"
            :rows="5"
            placeholder="请输入其他配置信息（JSON格式，如temperature、max_tokens等）"
          />
        </a-form-item>
        <a-form-item name="description" label="描述信息">
          <a-textarea v-model:value="form.description" :rows="3" placeholder="请输入描述信息" />
        </a-form-item>
        <a-form-item name="extend" label="扩展信息">
          <a-textarea v-model:value="form.extend" :rows="3" placeholder="请输入扩展信息（JSON格式）" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import type { Llm } from '@/api/llm'
import { getLlms, getLlm, createLlm, updateLlm, deleteLlm } from '@/api/llm'

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
  { title: '提供商', key: 'provider', width: 120 },
  { title: '模型', dataIndex: 'model', key: 'model', width: 150 },
  { title: 'API密钥', key: 'api_key', width: 150 },
  { title: '基础URL', dataIndex: 'base_url', key: 'base_url', width: 200 },
  { title: '描述', dataIndex: 'description', key: 'description', width: 200, ellipsis: true },
  { title: '操作', key: 'action', width: 160 },
]

const llmList = ref<Llm[]>([])
const loading = ref(false)
const modalVisible = ref(false)
const submitLoading = ref(false)
const editingRecord = ref<Llm | null>(null)
const formRef = ref()

// 表单数据
const form = reactive({
  provider: '',
  api_key: '',
  base_url: '',
  model: '',
  setting: '',
  description: '',
  extend: '',
})

// 表单规则
const formRules = {
  provider: [{ required: true, message: '请选择模型提供商', trigger: 'change' }],
}

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`,
})

const modalTitle = computed(() => (editingRecord.value ? '编辑LLM模型' : '新建LLM模型'))

// 获取提供商颜色
const getProviderColor = (provider: string) => {
  const colorMap: Record<string, string> = {
    openai: 'blue',
    deepseek: 'green',
    ollama: 'purple',
    qwen: 'orange',
    other: 'default',
  }
  return colorMap[provider] || 'default'
}

// 掩码API密钥
const maskApiKey = (apiKey: string) => {
  if (!apiKey || apiKey.length <= 8) {
    return '****'
  }
  return `${apiKey.substring(0, 4)}****${apiKey.substring(apiKey.length - 4)}`
}

// 提供商变化时的默认值设置
const handleProviderChange = () => {
  // 根据提供商设置默认的base_url
  const defaultUrls: Record<string, string> = {
    openai: 'https://api.openai.com/v1',
    bailian: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    bigmodel: 'https://open.bigmodel.cn/api/paas/v4',
    volcengine: 'https://ark.cn-beijing.volces.com/api/v3',
  }
  if (defaultUrls[form.provider] && !form.base_url) {
    form.base_url = defaultUrls[form.provider]
  }
}

const loadData = async () => {
  loading.value = true
  try {
    const response = await getLlms({
      skip: (pagination.current - 1) * pagination.pageSize,
      limit: pagination.pageSize,
    })
    llmList.value = response.data || []
    pagination.total = response.total || 0
  } catch (error) {
    message.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  loadData()
}

const showCreateModal = () => {
  editingRecord.value = null
  Object.assign(form, {
    provider: '',
    api_key: '',
    base_url: '',
    model: '',
    setting: '',
    description: '',
    extend: '',
  })
  modalVisible.value = true
}

const handleEdit = async (record: Llm) => {
  editingRecord.value = record

  // 获取详情
  try {
    const response = await getLlm(record.id)
    const detail = response.data
    Object.assign(form, {
      provider: detail.provider,
      api_key: detail.api_key || '',
      base_url: detail.base_url || '',
      model: detail.model,
      setting: detail.setting || '',
      description: detail.description || '',
      extend: detail.extend || '',
    })
  } catch (error) {
    // 如果获取详情失败，使用列表数据
    Object.assign(form, {
      provider: record.provider,
      api_key: record.api_key || '',
      base_url: record.base_url || '',
      model: record.model,
      setting: record.setting || '',
      description: record.description || '',
      extend: record.extend || '',
    })
  }

  modalVisible.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    submitLoading.value = true

    // 编辑时必须提交所有可清空字段的实际值（含空字符串），否则后端收不到键会认为“不更新”
    const submitData = {
      provider: form.provider,
      api_key: form.api_key ?? '',
      base_url: form.base_url ?? '',
      model: form.model ?? '',
      setting: form.setting ?? '',
      description: form.description ?? '',
      extend: form.extend ?? '',
    }

    if (editingRecord.value) {
      await updateLlm(editingRecord.value.id, submitData)
      message.success('更新成功')
    } else {
      await createLlm(submitData)
      message.success('创建成功')
    }

    modalVisible.value = false
    loadData()
  } catch (error: any) {
    if (error.errorFields) {
      return
    }
    message.error(error.response?.data?.detail || error.message || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

const handleDelete = async (id: number) => {
  try {
    await deleteLlm(id)
    message.success('删除成功')
    loadData()
  } catch (error: any) {
    message.error(error.response?.data?.detail || '删除失败')
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 500;
}
</style>
