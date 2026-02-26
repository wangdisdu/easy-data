<template>
  <div class="data-query-view">
    <div class="page-header">
      <h1>数据查询</h1>
    </div>

    <div class="data-query-container">
      <!-- 左侧：数据结构树 -->
      <div class="left-panel">
        <a-card title="数据源" :bordered="true" size="small">
          <div class="data-source-selector">
            <a-select
              v-model:value="selectedDataSourceId"
              placeholder="请选择数据源"
              style="width: 100%"
              @change="handleDataSourceChange"
              :loading="loadingDataSources"
            >
              <a-select-option
                v-for="ds in dataSources"
                :key="ds.id"
                :value="ds.id"
              >
                {{ ds.name }} ({{ ds.code }})
              </a-select-option>
            </a-select>
          </div>
          <a-divider style="margin: 12px 0" />
          <div v-if="selectedDataSourceId" class="tree-container">
            <a-tree
              :tree-data="treeData"
              :expanded-keys="expandedKeys"
              :selected-keys="selectedKeys"
              :load-data="onLoadData"
              @expand="onExpand"
              @select="onSelect"
              :show-icon="true"
              :block-node="true"
            >
              <template #icon="{ type }">
                <TableOutlined v-if="type === 'table'" />
                <FileTextOutlined v-else-if="type === 'view'" />
                <InsertRowLeftOutlined v-else />
              </template>
            </a-tree>
          </div>
          <div v-else class="empty-tree">
            请先选择数据源
          </div>
        </a-card>
      </div>

      <!-- 右侧：SQL查询和结果 -->
      <div class="right-panel">
        <a-card title="SQL查询" :bordered="true" size="small" class="sql-editor-card">
          <div class="sql-editor-container">
            <a-textarea
              v-model:value="sqlQuery"
              :rows="10"
              placeholder="请输入SQL查询语句，例如：SELECT * FROM table_name LIMIT 10"
              class="sql-editor"
            />
            <div class="sql-actions">
              <a-button type="primary" @click="handleExecuteSql" :loading="executing" :disabled="!selectedDataSourceId">
                <PlayCircleOutlined />
                执行查询
              </a-button>
              <a-button @click="handleClearSql">清空</a-button>
            </div>
          </div>
        </a-card>

        <a-card title="查询结果" :bordered="true" size="small" class="sql-result-card">
          <div v-if="sqlError" class="sql-error">
            <a-alert :message="sqlError" type="error" show-icon />
          </div>
          <a-table
            v-else
            :columns="resultColumns"
            :data-source="queryResults"
            :loading="executing"
            :pagination="false"
            :scroll="{ x: 'max-content' }"
            size="small"
          />
        </a-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import {
  TableOutlined,
  FileTextOutlined,
  InsertRowLeftOutlined,
  PlayCircleOutlined
} from '@ant-design/icons-vue'
import { getDataSources, getDataSourceTables, getTableStructure, executeSqlQuery } from '@/api/dataSource'
import type { DataSource } from '@/api/dataSource'

interface TreeNode {
  title: string
  key: string
  type: 'table' | 'view' | 'field'
  isLeaf?: boolean
  children?: TreeNode[]
  tableName?: string
  database?: string
  schema?: string
}

const dataSources = ref<DataSource[]>([])
const loadingDataSources = ref(false)
const selectedDataSourceId = ref<number | null>(null)
const treeData = ref<TreeNode[]>([])
const expandedKeys = ref<string[]>([])
const selectedKeys = ref<string[]>([])
const sqlQuery = ref('')
const queryResults = ref<Record<string, any>[]>([])
const resultColumns = ref<any[]>([])
const executing = ref(false)
const sqlError = ref('')

// 加载数据源列表
const loadDataSources = async () => {
  loadingDataSources.value = true
  try {
    const response = await getDataSources({ skip: 0, limit: 1000 })
    dataSources.value = response.data || []
  } catch (error: any) {
    message.error('加载数据源列表失败')
  } finally {
    loadingDataSources.value = false
  }
}

// 数据源改变时加载表和视图
const handleDataSourceChange = async (dataSourceId: number | null) => {
  if (!dataSourceId) {
    treeData.value = []
    selectedKeys.value = []
    expandedKeys.value = []
    sqlQuery.value = ''
    return
  }

  try {
    const response = await getDataSourceTables(dataSourceId)
    const { tables = [], views = [] } = response.data || {}

    const children: TreeNode[] = []

    // 添加表节点
    tables.forEach((tableName: string) => {
      children.push({
        title: tableName,
        key: `table-${dataSourceId}-${tableName}`,
        type: 'table',
        isLeaf: false,
        tableName,
      })
    })

    // 添加视图节点
    views.forEach((viewName: string) => {
      children.push({
        title: viewName,
        key: `view-${dataSourceId}-${viewName}`,
        type: 'view',
        isLeaf: false,
        tableName: viewName,
      })
    })

    treeData.value = children
    selectedKeys.value = []
    expandedKeys.value = []
    sqlQuery.value = ''
  } catch (error: any) {
    message.error('加载表和视图失败')
    treeData.value = []
  }
}

// 加载表结构
const loadTableStructure = async (node: TreeNode) => {
  if (!selectedDataSourceId.value || !node.tableName) return

  try {
    const response = await getTableStructure(selectedDataSourceId.value, node.tableName)
    const structure = response.data || []

    const children: TreeNode[] = structure.map((field: any) => ({
      title: `${field.field_name} (${field.data_type})`,
      key: `field-${selectedDataSourceId.value}-${node.tableName}-${field.field_name}`,
      type: 'field',
      isLeaf: true
    }))

    // 更新节点
    const updateNode = (nodes: TreeNode[]): boolean => {
      for (const n of nodes) {
        if (n.key === node.key) {
          n.children = children
          n.isLeaf = false
          return true
        }
        if (n.children && updateNode(n.children)) {
          return true
        }
      }
      return false
    }

    updateNode(treeData.value)
  } catch (error: any) {
    message.error('加载表结构失败')
  }
}

// 树节点加载数据
const onLoadData = (treeNode: any) => {
  return new Promise<void>((resolve) => {
    const node: TreeNode = treeNode.dataRef

    if (node.type === 'table' || node.type === 'view') {
      loadTableStructure(node).then(() => resolve()).catch(() => resolve())
    } else {
      resolve()
    }
  })
}

// 展开节点
const onExpand = (keys: string[]) => {
  expandedKeys.value = keys
}

// 选择节点
const onSelect = (keys: string[], info: any) => {
  selectedKeys.value = keys

  const node: TreeNode = info.node.dataRef
  if (node.type === 'table' || node.type === 'view') {
    // 自动填充SQL查询
    const tableName = node.tableName || ''
    if (tableName) {
      sqlQuery.value = `SELECT * FROM ${tableName} LIMIT 10`
    }
  }
}

// 执行SQL查询
const handleExecuteSql = async () => {
  if (!sqlQuery.value.trim()) {
    message.warning('请输入SQL查询语句')
    return
  }

  if (!selectedDataSourceId.value) {
    message.warning('请先选择数据源')
    return
  }

  executing.value = true
  sqlError.value = ''
  queryResults.value = []
  resultColumns.value = []

  try {
    const response = await executeSqlQuery(selectedDataSourceId.value, sqlQuery.value)
    const results = response.data || []

    if (results.length > 0) {
      // 从第一条结果中提取列名
      const firstRow = results[0]
      resultColumns.value = Object.keys(firstRow).map(key => ({
        title: key,
        dataIndex: key,
        key: key,
        ellipsis: true
      }))
    }

    queryResults.value = results
    message.success(`查询成功，共 ${results.length} 条记录`)
  } catch (error: any) {
    const errorMsg = error.response?.data?.msg || error.message || '执行SQL查询失败'
    sqlError.value = errorMsg
    message.error(errorMsg)
  } finally {
    executing.value = false
  }
}

// 清空SQL
const handleClearSql = () => {
  sqlQuery.value = ''
  queryResults.value = []
  resultColumns.value = []
  sqlError.value = ''
}

onMounted(() => {
  loadDataSources()
})
</script>

<style scoped>
.data-query-view {
  height: 100%;
  display: flex;
  flex-direction: column;
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

.data-query-container {
  display: flex;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.left-panel {
  width: 300px;
  flex-shrink: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.left-panel :deep(.ant-card-body) {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.data-source-selector {
  margin-bottom: 0;
  flex-shrink: 0;
}

.tree-container {
  flex: 1;
  min-height: 0;
  overflow-x: auto;
  overflow-y: auto;
  max-width: 100%;
  /* 自定义滚动条样式 */
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.2) transparent;
}

.tree-container::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.tree-container::-webkit-scrollbar-track {
  background: transparent;
}

.tree-container::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
}

.tree-container::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.3);
}

.tree-container :deep(.ant-tree) {
  min-width: max-content;
  white-space: nowrap;
  width: 100%;
}

.tree-container :deep(.ant-tree-list) {
  min-width: max-content;
}

.tree-container :deep(.ant-tree-node-content-wrapper) {
  white-space: nowrap;
  overflow: visible;
  display: inline-flex;
  align-items: center;
}

.tree-container :deep(.ant-tree-title) {
  white-space: nowrap;
  display: inline-block;
  max-width: none;
}

.empty-tree {
  text-align: center;
  padding: 40px 20px;
  color: #999;
  flex: 1;
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.sql-editor-card {
  flex-shrink: 0;
}

.sql-editor-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sql-editor {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
  font-size: 14px;
}

.sql-actions {
  display: flex;
  gap: 8px;
}

.sql-result-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.sql-result-card :deep(.ant-card-body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: auto;
}

.sql-error {
  margin-bottom: 16px;
}

.empty-result {
  text-align: center;
  padding: 40px;
  color: #999;
}
</style>
