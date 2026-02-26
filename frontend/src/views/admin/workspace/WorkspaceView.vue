<template>
  <div class="workspace-list">
    <div class="page-header">
      <h1>工作空间管理</h1>
      <a-button type="primary" @click="showCreateModal">
        <PlusOutlined />
        新建工作空间
      </a-button>
    </div>

    <a-table
      :columns="columns"
      :data-source="dataSource"
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
    >
      <a-form :model="form" :rules="rules" ref="formRef" layout="vertical">
        <a-form-item name="code" label="编码" v-if="!editingRecord">
          <a-input v-model:value="form.code" placeholder="请输入编码" />
        </a-form-item>
        <a-form-item name="name" label="名称">
          <a-input v-model:value="form.name" placeholder="请输入名称" />
        </a-form-item>
        <a-form-item name="description" label="描述">
          <a-textarea v-model:value="form.description" :rows="3" placeholder="请输入描述" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import type { WorkSpace } from '@/api/workspace'
import { getWorkspaces, createWorkspace, updateWorkspace, deleteWorkspace } from '@/api/workspace'

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '编码', dataIndex: 'code', key: 'code' },
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '描述', dataIndex: 'description', key: 'description' },
  { title: '操作', key: 'action', width: 150 },
]

const dataSource = ref<WorkSpace[]>([])
const loading = ref(false)
const modalVisible = ref(false)
const submitLoading = ref(false)
const editingRecord = ref<WorkSpace | null>(null)
const formRef = ref()

const form = reactive({
  code: '',
  name: '',
  description: '',
})

const rules = {
  code: [{ required: true, message: '请输入编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
}

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`,
})

const modalTitle = computed(() => (editingRecord.value ? '编辑工作空间' : '新建工作空间'))

const loadData = async () => {
  loading.value = true
  try {
    const response = await getWorkspaces({
      skip: (pagination.current - 1) * pagination.pageSize,
      limit: pagination.pageSize,
    })
    dataSource.value = response.data || []
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
    code: '',
    name: '',
    description: '',
  })
  modalVisible.value = true
}

const handleEdit = (record: WorkSpace) => {
  editingRecord.value = record
  Object.assign(form, {
    name: record.name,
    description: record.description || '',
  })
  modalVisible.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    submitLoading.value = true

    if (editingRecord.value) {
      await updateWorkspace(editingRecord.value.id, form)
      message.success('更新成功')
    } else {
      await createWorkspace(form)
      message.success('创建成功')
    }

    modalVisible.value = false
    loadData()
  } catch (error: any) {
    if (error.errorFields) {
      return
    }
    message.error(error.response?.data?.detail || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

const handleDelete = async (id: number) => {
  try {
    await deleteWorkspace(id)
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

