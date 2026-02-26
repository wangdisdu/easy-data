<template>
  <div class="data-source-list">
    <div class="page-header">
      <h1>数据源管理</h1>
      <a-button type="primary" @click="showCreateModal">
        <PlusOutlined />
        新建数据源
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
      width="600px"
    >
      <a-form :model="form" :rules="formRules" ref="formRef" layout="vertical">
        <a-form-item name="code" label="编码" v-if="!editingRecord">
          <a-input v-model:value="form.code" placeholder="请输入编码" />
        </a-form-item>
        <a-form-item name="name" label="名称">
          <a-input v-model:value="form.name" placeholder="请输入名称" />
        </a-form-item>
        <a-form-item name="platform" label="数据库类型">
          <a-select v-model:value="form.platform" placeholder="请选择数据库类型" @change="handlePlatformChange">
            <a-select-option value="mysql">MySQL</a-select-option>
            <a-select-option value="postgresql">PostgreSQL</a-select-option>
            <a-select-option value="sqlserver">SqlServer</a-select-option>
            <a-select-option value="oracle">Oracle</a-select-option>
            <a-select-option value="clickhouse">ClickHouse</a-select-option>
            <a-select-option value="doris">Doris</a-select-option>
            <a-select-option value="sqlite">SQLite</a-select-option>
          </a-select>
        </a-form-item>

        <!-- 动态配置项 -->
        <!-- SQLite 不需要 host/port/username/password -->
        <template v-if="!isSQLite">
        <a-form-item :validate-status="dbConfigErrors.host ? 'error' : ''" :help="dbConfigErrors.host">
          <template #label>主机地址</template>
          <a-input v-model:value="dbConfig.host" placeholder="请输入主机地址" @blur="validateDbField('host')" />
        </a-form-item>

        <a-form-item :validate-status="dbConfigErrors.port ? 'error' : ''" :help="dbConfigErrors.port">
          <template #label>端口</template>
          <a-input-number v-model:value="dbConfig.port" :min="1" :max="65535" style="width: 100%" @blur="validateDbField('port')" />
        </a-form-item>

        <a-form-item :validate-status="dbConfigErrors.username ? 'error' : ''" :help="dbConfigErrors.username">
          <template #label>用户名</template>
          <a-input v-model:value="dbConfig.username" placeholder="请输入用户名" @blur="validateDbField('username')" />
        </a-form-item>

        <a-form-item label="密码">
          <a-input-password v-model:value="dbConfig.password" placeholder="请输入密码" />
        </a-form-item>
        </template>

        <a-form-item :validate-status="dbConfigErrors.database ? 'error' : ''" :help="dbConfigErrors.database">
          <template #label>{{ dbConfigLabel.database }}</template>
          <a-input
            v-model:value="dbConfig.database"
            :placeholder="isSQLite ? '请输入SQLite文件路径（相对于local_sqlite目录，如：chinook.sqlite）' : '请输入数据库名称'"
            @blur="validateDbField('database')"
          />
        </a-form-item>

        <a-form-item name="semantic" label="语义说明">
          <a-textarea v-model:value="form.semantic" :rows="3" placeholder="请输入数据源语义说明" />
        </a-form-item>

        <a-form-item name="description" label="描述">
          <a-textarea v-model:value="form.description" :rows="3" placeholder="请输入描述" />
        </a-form-item>

        <a-form-item name="workspace_ids" label="关联工作空间">
          <a-select
            v-model:value="form.workspace_ids"
            mode="multiple"
            placeholder="请选择工作空间（可选）"
            :options="workspaceOptions"
            style="width: 100%"
          />
        </a-form-item>

        <!-- 测试连接按钮 -->
        <div class="test-connection-section">
          <a-button type="primary" @click="handleTestConnection" :loading="testLoading">
            测试连接
          </a-button>
          <span v-if="testResult" :class="testResult.status === 'success' ? 'test-success' : 'test-error'">
            {{ testResult.message }}
          </span>
        </div>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import type { DataSource } from '@/api/dataSource'
import {
  getDataSources,
  getDataSource,
  createDataSource,
  updateDataSource,
  deleteDataSource,
  testDataSource,
} from '@/api/dataSource'
import { getWorkspaces } from '@/api/workspace'

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
  { title: '编码', dataIndex: 'code', key: 'code', width: 200 },
  { title: '名称', dataIndex: 'name', key: 'name', width: 200 },
  { title: '数据库类型', dataIndex: 'platform', key: 'platform', width: 100 },
  { title: '操作', key: 'action', width: 160 },
]

const dataSource = ref<DataSource[]>([])
const loading = ref(false)
const modalVisible = ref(false)
const submitLoading = ref(false)
const testLoading = ref(false)
const editingRecord = ref<DataSource | null>(null)
const formRef = ref()
const testResult = ref<{ status: 'success' | 'error'; message: string } | null>(null)

// 表单数据
const form = reactive({
  code: '',
  name: '',
  platform: '',
  setting: '',
  semantic: '',
  description: '',
  workspace_ids: [] as number[],
})

// 工作空间选项
const workspaceOptions = ref<Array<{ label: string; value: number }>>([])

// 数据库配置
const dbConfig = reactive({
  host: '',
  port: 0,
  username: '',
  password: '',
  database: '',
})

// 数据库配置验证错误信息
const dbConfigErrors = reactive({
  host: '',
  port: '',
  username: '',
  database: '',
})

// 判断是否为 SQLite
const isSQLite = computed(() => form.platform.toLowerCase() === 'sqlite')

// 数据库配置标签映射
const dbConfigLabel = computed(() => {
  const platform = form.platform.toLowerCase()
  switch (platform) {
    case 'oracle':
      return {
        database: '服务名/SID',
      }
    case 'clickhouse':
      return {
        database: '数据库',
      }
    case 'doris':
      return {
        database: '数据库',
      }
    case 'sqlite':
      return {
        database: '文件路径',
      }
    default:
      return {
        database: '数据库',
      }
  }
})

// 表单规则，只包含form对象中的字段
const formRules = {
  code: [{ required: true, message: '请输入编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  platform: [{ required: true, message: '请选择数据库类型', trigger: 'change' }],
}

// 验证单个数据库配置字段
const validateDbField = (field: keyof typeof dbConfig) => {
  const value = dbConfig[field]
  let error = ''

  if (field === 'port') {
    if (!value || value <= 0 || value > 65535) {
      error = '请输入有效的端口号（1-65535）'
    }
  } else if (field === 'database') {
    if (!value) {
      error = `${dbConfigLabel.value.database}不能为空`
    }
  } else {
    if (!value) {
      const fieldLabelMap: Record<string, string> = {
        host: '主机地址',
        username: '用户名',
      }
      error = `${fieldLabelMap[field] || field}不能为空`
    }
  }

  dbConfigErrors[field] = error
  return !error
}

// 验证所有数据库配置字段
const validateDbConfig = () => {
  let isValid = true

  // 重置所有错误
  Object.keys(dbConfigErrors).forEach(key => {
    dbConfigErrors[key as keyof typeof dbConfigErrors] = ''
  })

  // SQLite 只需要 database 字段
  if (isSQLite.value) {
    if (!validateDbField('database')) {
      isValid = false
    }
    return isValid
  }

  // 其他数据库类型验证必填字段
  const requiredFields = ['host', 'port', 'username', 'database'] as const
  for (const field of requiredFields) {
    if (!validateDbField(field)) {
      isValid = false
    }
  }

  return isValid
}

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`,
})

const modalTitle = computed(() => (editingRecord.value ? '编辑数据源' : '新建数据源'))

const loadData = async () => {
  loading.value = true
  try {
    const response = await getDataSources({
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
    setting: '',
    semantic: '',
    description: '',
    workspace_ids: [],
  })

  // 重置数据库配置
  Object.assign(dbConfig, {
    host: '',
    port: 0,
    username: '',
    password: '',
    database: '',
  })

  testResult.value = null
  modalVisible.value = true
}

const handleEdit = async (record: DataSource) => {
  editingRecord.value = record

  // 获取详情以获取workspace_ids
  try {
    const response = await getDataSource(record.id)
    const detail = response.data
    Object.assign(form, {
      name: detail.name,
      platform: detail.platform,
      setting: detail.setting,
      semantic: detail.semantic || '',
      description: detail.description || '',
      workspace_ids: detail.workspace_ids || [],
    })
  } catch (error) {
    // 如果获取详情失败，使用列表数据
  Object.assign(form, {
    name: record.name,
    platform: record.platform,
    setting: record.setting,
      semantic: record.semantic || '',
    description: record.description || '',
      workspace_ids: record.workspace_ids || [],
  })
  }

  // 解析JSON配置到dbConfig
  try {
    const setting = JSON.parse(record.setting)
    Object.assign(dbConfig, {
      host: setting.host || '',
      port: setting.port || 0,
      username: setting.username || '',
      password: setting.password || '',
      database: setting.database || '',
    })
  } catch (error) {
    // 解析失败则重置
    Object.assign(dbConfig, {
      host: '',
      port: 0,
      username: '',
      password: '',
      database: '',
    })
  }

  testResult.value = null
  modalVisible.value = true
}

const handlePlatformChange = () => {
  // 重置测试结果
  testResult.value = null

  // SQLite 不需要端口，清空相关字段
  if (isSQLite.value) {
    dbConfig.host = ''
    dbConfig.port = 0
    dbConfig.username = ''
    dbConfig.password = ''
    return
  }

  // 根据不同数据库类型设置默认端口
  switch (form.platform) {
    case 'mysql':
      dbConfig.port = 3306
      break
    case 'postgresql':
      dbConfig.port = 5432
      break
    case 'sqlserver':
      dbConfig.port = 1433
      break
    case 'oracle':
      dbConfig.port = 1521
      break
    case 'clickhouse':
      dbConfig.port = 9000
      break
    case 'doris':
      dbConfig.port = 9030
      break
    default:
      dbConfig.port = 0
  }
}

const handleTestConnection = async () => {
  try {
    testLoading.value = true
    testResult.value = null

    // 验证数据库配置
    if (!validateDbConfig()) {
      // 如果验证失败，不继续测试
      testResult.value = {
        status: 'error',
        message: '数据库配置验证失败，请检查必填字段',
      }
      return
    }

    // 构造测试数据，使用DataSourceCreate类型
    const testData = {
      // 测试时code可以为空，因为后端不验证
      code: form.code || 'test',
      name: form.name || '测试数据源',
      platform: form.platform,
      setting: JSON.stringify(dbConfig),
      description: form.description || '',
    }

    // 调用测试接口
    const response = await testDataSource(0, testData)

    // 新的返回结构为{data:{success:true,message:""}}
    const { success, message: msg } = response.data

    // 更新测试结果
    testResult.value = {
      status: success ? 'success' : 'error',
      message: success ? msg || '连接测试成功' : msg || '连接测试失败',
    }

    // 显示消息
    if (success) {
      message.success(msg || '连接测试成功')
    } else {
      message.error(msg || '连接测试失败')
    }
  } catch (error: any) {
    // 简化错误处理
    const errorMessage = error.response?.data?.message || error.message || '连接测试失败'
    testResult.value = {
      status: 'error',
      message: errorMessage,
    }
    message.error(errorMessage)
  } finally {
    testLoading.value = false
  }
}

const handleSubmit = async () => {
  try {
    // 验证表单字段
    await formRef.value.validate()

    // 验证数据库配置
    if (!validateDbConfig()) {
      // 如果验证失败，不继续提交
      return
    }

    submitLoading.value = true

    // 将dbConfig转换为JSON字符串
    form.setting = JSON.stringify(dbConfig)

    if (editingRecord.value) {
      await updateDataSource(editingRecord.value.id, form)
      message.success('更新成功')
    } else {
      await createDataSource(form)
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
    await deleteDataSource(id)
    message.success('删除成功')
    loadData()
  } catch (error: any) {
    message.error(error.response?.data?.detail || '删除失败')
  }
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

.test-connection-section {
  display: flex;
  align-items: center;
  margin-top: 16px;
  gap: 16px;
}

.test-success {
  color: #52c41a;
}

.test-error {
  color: #ff4d4f;
}
</style>
