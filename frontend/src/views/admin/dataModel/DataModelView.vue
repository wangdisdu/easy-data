<template>
  <div class="data-model-list">
    <div class="page-header">
      <h1>数据模型管理</h1>
      <a-button type="primary" @click="showCreateModal">
        <PlusOutlined />
        新建数据模型
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
            <a-button type="link" @click="handleScan(record)">扫描</a-button>
            <a-button type="link" @click="handleEdit(record)">编辑</a-button>
            <a-popconfirm title="确定要删除吗？" @confirm="handleDelete(record.id)">
              <a-button type="link" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
        <template v-else-if="column.key === 'data_source'">
          {{ getDataSourceDisplay(record.ds_id) }}
        </template>
      </template>
    </a-table>

    <!-- 创建/编辑弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="modalTitle"
      @ok="handleSubmit"
      :confirm-loading="submitLoading"
      width="700px"
    >
      <a-form :model="form" :rules="rules" ref="formRef" layout="vertical">
        <a-form-item name="code" label="编码" v-if="!editingRecord">
          <a-input v-model:value="form.code" placeholder="请输入编码" />
        </a-form-item>
        <a-form-item name="name" label="名称">
          <a-input v-model:value="form.name" placeholder="请输入名称" />
        </a-form-item>
        <a-form-item name="platform" label="数据库类型">
          <a-select v-model:value="form.platform" placeholder="请选择数据库类型">
            <a-select-option value="MySQL">MySQL</a-select-option>
            <a-select-option value="PostgreSQL">PostgreSQL</a-select-option>
            <a-select-option value="SQL Server">SQL Server</a-select-option>
            <a-select-option value="Oracle">Oracle</a-select-option>
            <a-select-option value="ClickHouse">ClickHouse</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item name="type" label="模型类型">
          <a-select v-model:value="form.type" placeholder="请选择模型类型" allow-clear>
            <a-select-option value="table">表</a-select-option>
            <a-select-option value="view">视图</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item name="ds_id" label="所属数据源">
          <a-select
            v-model:value="form.ds_id"
            placeholder="请选择数据源"
            allow-clear
            :options="dataSourceOptions"
          />
        </a-form-item>
        <a-form-item name="semantic" label="语义说明">
          <a-textarea
            v-model:value="form.semantic"
            :rows="8"
            placeholder='请输入模型的语义说明'
          />
        </a-form-item>
        <a-form-item name="summary" label="摘要说明">
          <a-textarea
            v-model:value="form.summary"
            :rows="3"
            placeholder="请输入模型的摘要说明"
          />
        </a-form-item>
        <a-form-item name="knowledge" label="外部知识">
          <a-textarea
            v-model:value="form.knowledge"
            :rows="3"
            placeholder="请输入模型的外部知识"
          />
        </a-form-item>
        <a-form-item name="description" label="描述">
          <a-textarea v-model:value="form.description" :rows="3" placeholder="请输入描述" />
        </a-form-item>
        <a-form-item name="workspace_ids" label="关联工作空间">
          <a-select
            v-model:value="form.workspace_ids"
            mode="multiple"
            placeholder="请选择工作空间（可多选）"
            :options="workspaceOptions"
            style="width: 100%"
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 扫描弹窗 -->
    <a-modal
      v-model:open="scanModalVisible"
      :title="scanModalTitle"
      @ok="handleScanConfirm"
      :confirm-loading="scanSubmitLoading"
      width="560px"
    >
      <a-form layout="vertical">
        <a-form-item label="智能体" required>
          <a-select
            v-model:value="scanForm.agent_id"
            placeholder="请选择智能体"
            :options="agentOptions.map((a) => ({ label: a.name, value: a.id }))"
            style="width: 100%"
          />
        </a-form-item>
        <a-form-item label="输入描述">
          <a-textarea
            v-model:value="scanForm.input"
            :rows="4"
            placeholder="执行任务的输入描述"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import type { DataModel } from '@/api/dataModel'
import type { Agent } from '@/api/agent'
import { getDataModels, createDataModel, updateDataModel, deleteDataModel, getDataModel } from '@/api/dataModel'
import { getDataSources } from '@/api/dataSource'
import { getWorkspaces } from '@/api/workspace'
import { getAgents } from '@/api/agent'
import { createJob } from '@/api/job'

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
  { title: '编码', dataIndex: 'code', key: 'code', width: 200 },
  { title: '名称', dataIndex: 'name', key: 'name', width: 200 },
  { title: '类型', dataIndex: 'type', key: 'type', width: 80 },
  { title: '数据源', dataIndex: 'data_source', key: 'data_source', width: 200 },
  { title: '操作', key: 'action', width: 220 },
]

const dataSource = ref<DataModel[]>([])
const loading = ref(false)
const modalVisible = ref(false)
const submitLoading = ref(false)
const editingRecord = ref<DataModel | null>(null)
const formRef = ref()

const form = reactive({
  code: '',
  name: '',
  platform: '',
  type: undefined as string | undefined,
  ds_id: undefined as number | undefined,
  semantic: '',
  summary: '',
  knowledge: '',
  description: '',
  workspace_ids: [] as number[],
})

const dataSourceOptions = ref<Array<{ label: string; value: number }>>([])
const workspaceOptions = ref<Array<{ label: string; value: number }>>([])
const dataSourceMap = ref<Map<number, { name: string; platform: string }>>(new Map())

// 扫描弹窗
const scanModalVisible = ref(false)
const scanSubmitLoading = ref(false)
const scanTargetRecord = ref<DataModel | null>(null)
const agentOptions = ref<Agent[]>([])
const scanForm = reactive({ agent_id: undefined as number | undefined, input: '' })
const scanModalTitle = computed(() =>
  scanTargetRecord.value ? `扫描${scanTargetRecord.value.name}` : '扫描'
)

const rules = {
  code: [{ required: true, message: '请输入编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  platform: [{ required: true, message: '请选择数据库类型', trigger: 'change' }],
}

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`,
})

const modalTitle = computed(() => (editingRecord.value ? '编辑数据模型' : '新建数据模型'))

const loadData = async () => {
  loading.value = true
  try {
    const response = await getDataModels({
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
    platform: '',
    type: undefined,
    ds_id: undefined,
    semantic: '',
    summary: '',
    knowledge: '',
    description: '',
    workspace_ids: [],
  })
  modalVisible.value = true
}

const handleEdit = async (record: DataModel) => {
  editingRecord.value = record

  // 获取详情以获取workspace_ids
  try {
    const response = await getDataModel(record.id)
    const detail = response.data
    Object.assign(form, {
      name: detail.name,
      platform: detail.platform,
      type: detail.type || undefined,
      ds_id: detail.ds_id || undefined,
      semantic: detail.semantic || '',
      summary: detail.summary || '',
      knowledge: detail.knowledge || '',
      description: detail.description || '',
      workspace_ids: detail.workspace_ids || [],
    })
  } catch (error) {
    // 如果获取详情失败，使用列表数据
  Object.assign(form, {
    name: record.name,
    platform: record.platform,
    type: record.type || undefined,
    ds_id: record.ds_id || undefined,
    semantic: record.semantic || '',
    summary: record.summary || '',
    knowledge: record.knowledge || '',
    description: record.description || '',
    workspace_ids: record.workspace_ids || [],
  })
  }
  modalVisible.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    submitLoading.value = true

    if (editingRecord.value) {
      await updateDataModel(editingRecord.value.id, form)
      message.success('更新成功')
    } else {
      await createDataModel(form)
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
    await deleteDataModel(id)
    message.success('删除成功')
    loadData()
  } catch (error: any) {
    message.error(error.response?.data?.detail || '删除失败')
  }
}

const loadDataSources = async () => {
  try {
    const response = await getDataSources({ skip: 0, limit: 1000 })
    const dataSources = response.data || []
    dataSourceOptions.value = dataSources.map((ds: any) => ({
      label: `${ds.name} (${ds.code})`,
      value: ds.id,
    }))
    // 填充数据源映射，用于快速查找
    dataSourceMap.value = new Map()
    dataSources.forEach((ds: any) => {
      dataSourceMap.value.set(ds.id, {
        name: ds.name,
        platform: ds.platform
      })
    })
  } catch (error) {
    console.error('加载数据源列表失败', error)
  }
}

const loadAgentsForScan = async () => {
  try {
    const res = await getAgents({ skip: 0, limit: 500 })
    const list = res.data || []
    agentOptions.value = list
    const defaultAgent = list.find((a: Agent) => (a.name || '').includes('系统管理助手'))
    if (defaultAgent) {
      scanForm.agent_id = defaultAgent.id
    } else if (list.length > 0) {
      scanForm.agent_id = list[0].id
    }
  } catch {
    message.error('加载智能体列表失败')
  }
}

const handleScan = (record: DataModel) => {
  scanTargetRecord.value = record
  scanForm.input = `分析id为${record.id}的数据模型的数据，总结模型说明，并保存分析结果`
  scanForm.agent_id = undefined
  scanModalVisible.value = true
  loadAgentsForScan()
}

const handleScanConfirm = async () => {
  if (scanForm.agent_id == null) {
    message.warning('请选择智能体')
    return
  }
  scanSubmitLoading.value = true
  try {
    await createJob({
      type: 'agent',
      setting: JSON.stringify({
        agent_id: scanForm.agent_id,
        input: scanForm.input || '',
      }),
      description: scanTargetRecord.value
        ? `扫描数据模型：${scanTargetRecord.value.name}（ID=${scanTargetRecord.value.id}）`
        : undefined,
    })
    message.success('作业已创建，将自动执行')
    scanModalVisible.value = false
  } catch (e: any) {
    message.error(e.response?.data?.msg || '创建作业失败')
  } finally {
    scanSubmitLoading.value = false
  }
}

const getDataSourceDisplay = (dsId?: number): string => {
  if (!dsId) {
    return '-'
  }
  const ds = dataSourceMap.value.get(dsId)
  if (!ds) {
    return '-'
  }
  return `${ds.platform} - ${ds.name}`
}

const loadWorkspaces = async () => {
  try {
    const response = await getWorkspaces({ skip: 0, limit: 1000 })
    workspaceOptions.value = (response.data || []).map((ws: any) => ({
      label: `${ws.name} (${ws.code})`,
      value: ws.id,
    }))
  } catch (error) {
    console.error('加载工作空间列表失败', error)
  }
}

onMounted(() => {
  loadData()
  loadDataSources()
  loadWorkspaces()
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
