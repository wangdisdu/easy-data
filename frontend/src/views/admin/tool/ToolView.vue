<template>
  <div class="tool-list">
    <div class="page-header">
      <h1>工具管理</h1>
      <a-button type="primary" @click="showCreateModal">
        <PlusOutlined />
        新建工具
      </a-button>
    </div>

    <a-table
      :columns="columns"
      :data-source="toolList"
      :loading="loading"
      :pagination="pagination"
      row-key="id"
      @change="handleTableChange"
    >
      <template #bodyCell="{ column, record }">
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
        <a-form-item name="tool" label="工具函数名">
          <a-input v-model:value="form.tool" placeholder="请输入工具函数名（与工具代码内容对应）" />
        </a-form-item>
        <a-form-item name="description" label="工具描述">
          <a-textarea v-model:value="form.description" :rows="3" placeholder="请输入工具描述信息" />
        </a-form-item>
        <a-form-item name="parameters" label="工具参数定义">
          <a-textarea
            v-model:value="form.parameters"
            :rows="5"
            placeholder="请输入工具参数定义"
          />
        </a-form-item>
        <a-form-item name="content" label="工具代码内容">
          <a-textarea
            v-model:value="form.content"
            :rows="8"
            placeholder="请输入工具代码内容，与工具函数名对应代码"
          />
        </a-form-item>
        <a-form-item name="extend" label="扩展信息">
          <a-textarea v-model:value="form.extend" :rows="3" placeholder="请输入扩展信息" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import type { Tool } from '@/api/tool'
import { getTools, getTool, createTool, updateTool, deleteTool } from '@/api/tool'

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
  { title: '工具函数名', dataIndex: 'tool', key: 'tool', width: 200 },
  { title: '描述', dataIndex: 'description', key: 'description', width: 300, ellipsis: true },
  { title: '操作', key: 'action', width: 160 },
]

const toolList = ref<Tool[]>([])
const loading = ref(false)
const modalVisible = ref(false)
const submitLoading = ref(false)
const editingRecord = ref<Tool | null>(null)
const formRef = ref()

// 表单数据
const form = reactive({
  tool: '',
  description: '',
  parameters: '',
  content: '',
  extend: '',
})

// 表单规则
const formRules = {
  tool: [{ required: true, message: '请输入工具函数名', trigger: 'blur' }],
}

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`,
})

const modalTitle = computed(() => (editingRecord.value ? '编辑工具' : '新建工具'))

const loadData = async () => {
  loading.value = true
  try {
    const response = await getTools({
      skip: (pagination.current - 1) * pagination.pageSize,
      limit: pagination.pageSize,
    })
    toolList.value = response.data || []
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
    tool: '',
    description: '',
    parameters: '',
    content: '',
    extend: '',
  })
  modalVisible.value = true
}

const handleEdit = async (record: Tool) => {
  editingRecord.value = record

  // 获取详情
  try {
    const response = await getTool(record.id)
    const detail = response.data
    Object.assign(form, {
      tool: detail.tool,
      description: detail.description || '',
      parameters: detail.parameters || '',
      content: detail.content || '',
      extend: detail.extend || '',
    })
  } catch (error) {
    // 如果获取详情失败，使用列表数据
    Object.assign(form, {
      tool: record.tool,
      description: record.description || '',
      parameters: record.parameters || '',
      content: record.content || '',
      extend: record.extend || '',
    })
  }

  modalVisible.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    submitLoading.value = true

    if (editingRecord.value) {
      await updateTool(editingRecord.value.id, form)
      message.success('更新成功')
    } else {
      await createTool(form)
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
    await deleteTool(id)
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
