<template>
  <div class="agent-list">
    <div class="page-header">
      <h1>智能体管理</h1>
      <a-button type="primary" @click="showCreateModal">
        <PlusOutlined />
        新建智能体
      </a-button>
    </div>

    <a-spin :spinning="loading">
      <div v-if="!loading && agentList.length === 0" class="empty-wrapper">
        <a-empty description="暂无智能体，请先创建一个">
          <template #extra>
            <a-button type="primary" @click="showCreateModal">新建智能体</a-button>
          </template>
        </a-empty>
      </div>
      <template v-else>
        <div class="agent-cards">
          <a-card
            v-for="agent in agentList"
            :key="agent.id"
            class="agent-card"
            :class="{ 'agent-card-disabled': agent.status === 'inactive' }"
          >
            <template #title>
              <div class="card-title">
                <span class="agent-name">{{ agent.name }}</span>
                <a-switch
                  :checked="agent.status === 'active'"
                  @change="(checked) => handleToggleStatus(agent, checked)"
                  :loading="agent.id === togglingId"
                  checked-children="启用"
                  un-checked-children="禁用"
                />
              </div>
            </template>
            <div class="card-content">
              <div class="agent-description" v-if="agent.description">
                {{ agent.description }}
              </div>
              <div class="agent-description-empty" v-else>暂无描述</div>
            </div>
            <template #actions>
              <a-button type="link" @click="handleEdit(agent)">
                <EditOutlined />
                编辑
              </a-button>
              <a-button type="link" @click="handleEditGraph(agent)">
                <ApartmentOutlined />
                开发
              </a-button>
              <a-dropdown>
                <a-button type="link">
                  更多
                  <DownOutlined />
                </a-button>
                <template #overlay>
                  <a-menu @click="({ key }) => handleMoreAction(agent, key)">
                    <a-menu-item key="clone">克隆</a-menu-item>
                    <a-menu-item key="delete" danger>删除</a-menu-item>
                  </a-menu>
                </template>
              </a-dropdown>
            </template>
          </a-card>
        </div>
      </template>

      <div class="pagination-wrapper" v-if="pagination.total > 0">
        <a-pagination
          v-model:current="pagination.current"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :show-size-changer="true"
          :show-total="(total) => `共 ${total} 条`"
          @change="handlePaginationChange"
        />
      </div>
    </a-spin>

    <!-- 创建/编辑弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="modalTitle"
      @ok="handleSubmit"
      :confirm-loading="submitLoading"
      width="800px"
    >
      <a-form :model="form" :rules="formRules" ref="formRef" layout="vertical">
        <a-form-item name="name" label="名称">
          <a-input v-model:value="form.name" placeholder="请输入智能体名称" />
        </a-form-item>
        <a-form-item name="description" label="描述">
          <a-textarea v-model:value="form.description" :rows="3" placeholder="请输入智能体描述" />
        </a-form-item>
        <a-form-item name="config" label="配置信息">
          <a-textarea
            v-model:value="form.config"
            :rows="5"
            placeholder="请输入配置信息（JSON格式）"
          />
        </a-form-item>
        <a-form-item name="status" label="状态">
          <a-select v-model:value="form.status" placeholder="请选择状态">
            <a-select-option value="active">启用</a-select-option>
            <a-select-option value="inactive">禁用</a-select-option>
          </a-select>
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
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { PlusOutlined, EditOutlined, ApartmentOutlined, DownOutlined } from '@ant-design/icons-vue'
import type { Agent } from '@/api/agent'
import {
  getAgents,
  getAgent,
  createAgent,
  updateAgent,
  deleteAgent,
  getAgentGraph,
  saveAgentGraph,
} from '@/api/agent'

const router = useRouter()

const agentList = ref<Agent[]>([])
const loading = ref(false)
const togglingId = ref<number | null>(null)
const cloningId = ref<number | null>(null)
const modalVisible = ref(false)
const submitLoading = ref(false)
const editingRecord = ref<Agent | null>(null)
const formRef = ref()

// 表单数据
const form = reactive({
  name: '',
  description: '',
  config: '',
  status: 'active',
  extend: '',
})

// 表单规则
const formRules = {
  name: [{ required: true, message: '请输入智能体名称', trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`,
})

const modalTitle = computed(() => (editingRecord.value ? '编辑智能体' : '新建智能体'))

const loadData = async () => {
  loading.value = true
  try {
    const response = await getAgents({
      skip: (pagination.current - 1) * pagination.pageSize,
      limit: pagination.pageSize,
    })
    agentList.value = response.data || []
    pagination.total = response.total || 0
  } catch (error) {
    message.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const handlePaginationChange = () => {
  loadData()
}

const handleToggleStatus = async (agent: Agent, checked: boolean) => {
  togglingId.value = agent.id
  try {
    await updateAgent(agent.id, {
      status: checked ? 'active' : 'inactive',
    })
    agent.status = checked ? 'active' : 'inactive'
    message.success(checked ? '已启用' : '已禁用')
  } catch (error: any) {
    message.error(error.response?.data?.detail || '操作失败')
  } finally {
    togglingId.value = null
  }
}

const showCreateModal = () => {
  editingRecord.value = null
  Object.assign(form, {
    name: '',
    description: '',
    config: '',
    status: 'active',
    extend: '',
  })
  modalVisible.value = true
}

const handleEdit = async (record: Agent) => {
  editingRecord.value = record

  // 获取详情
  try {
    const response = await getAgent(record.id)
    const detail = response.data
    Object.assign(form, {
      name: detail.name,
      description: detail.description || '',
      config: detail.config || '',
      status: detail.status,
      extend: detail.extend || '',
    })
  } catch (error) {
    // 如果获取详情失败，使用列表数据
    Object.assign(form, {
      name: record.name,
      description: record.description || '',
      config: record.config || '',
      status: record.status,
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
      await updateAgent(editingRecord.value.id, form)
      message.success('更新成功')
    } else {
      await createAgent(form)
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
    await deleteAgent(id)
    message.success('删除成功')
    loadData()
  } catch (error: any) {
    message.error(error.response?.data?.detail || '删除失败')
  }
}

const handleMoreAction = (agent: Agent, key: string) => {
  if (key === 'clone') {
    Modal.confirm({
      title: '确定要克隆该智能体吗？',
      onOk: () => handleClone(agent),
    })
  } else if (key === 'delete') {
    Modal.confirm({
      title: '确定要删除吗？',
      onOk: () => handleDelete(agent.id),
    })
  }
}

const cloneLoading = ref(false)

const handleClone = async (source: Agent) => {
  cloneLoading.value = true
  try {
    const [detailRes, graphRes] = await Promise.all([
      getAgent(source.id),
      getAgentGraph(source.id),
    ])
    const detail = detailRes.data
    const graph = graphRes.data
    const newAgent = await createAgent({
      name: `${detail.name}（副本）`,
      description: detail.description || '',
      config: detail.config || '',
      status: 'active',
      extend: detail.extend || '',
    })
    const newId = newAgent.data.id
    if (graph?.nodes?.length) {
      await saveAgentGraph(newId, { nodes: graph.nodes, edges: graph.edges || [] })
    }
    message.success('克隆成功')
    loadData()
  } catch (error: any) {
    message.error(error.response?.data?.detail || error.message || '克隆失败')
  } finally {
    cloneLoading.value = false
  }
}

const handleEditGraph = (record: Agent) => {
  router.push(`/admin/agents/${record.id}/edit`)
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.empty-wrapper {
  min-height: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
}

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

.agent-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.agent-card {
  transition: all 0.3s;
}

.agent-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.agent-card-disabled {
  opacity: 0.7;
}

.card-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  min-width: 0; /* 允许 flex 子元素收缩 */
}

.agent-name {
  font-size: 16px;
  font-weight: 500;
  flex: 1;
  min-width: 0; /* 允许文本截断 */
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-content {
  min-height: 60px;
}

.agent-description {
  color: #666;
  font-size: 14px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.agent-description-empty {
  color: #bfbfbf;
  font-size: 14px;
  line-height: 1.6;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}
</style>
