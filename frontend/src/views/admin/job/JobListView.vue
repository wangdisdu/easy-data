<template>
  <div class="job-list">
    <div class="page-header">
      <h1>作业列表</h1>
    </div>

    <a-table
      :columns="columns"
      :data-source="jobList"
      :loading="loading"
      :pagination="pagination"
      row-key="id"
      @change="handleTableChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button type="link" size="small" @click="handleView(record)">查看</a-button>
            <a-button type="link" size="small" @click="handleViewLogs(record)">日志</a-button>
            <a-popconfirm title="确定要删除该作业吗？" @confirm="handleDelete(record.id)">
              <a-button type="link" size="small" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 作业详情抽屉 -->
    <a-drawer
      v-model:open="detailVisible"
      title="作业详情"
      width="480"
      :body-style="{ paddingBottom: '80px' }"
    >
      <a-descriptions v-if="currentJob" :column="1" bordered size="small">
        <a-descriptions-item label="ID">{{ currentJob.id }}</a-descriptions-item>
        <a-descriptions-item label="类型">{{ currentJob.type }}</a-descriptions-item>
        <a-descriptions-item label="状态">
          <a-tag :color="statusColor(currentJob.status)">{{ currentJob.status }}</a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="描述">{{ currentJob.description || '-' }}</a-descriptions-item>
        <a-descriptions-item label="开始时间">{{ formatTime(currentJob.begin_time) }}</a-descriptions-item>
        <a-descriptions-item label="结束时间">{{ formatTime(currentJob.end_time) }}</a-descriptions-item>
        <a-descriptions-item label="配置">
          <pre class="setting-pre">{{ currentJob.setting || '-' }}</pre>
        </a-descriptions-item>
      </a-descriptions>
    </a-drawer>

    <!-- 作业日志弹窗 -->
    <a-modal
      v-model:open="logVisible"
      title="作业日志"
      width="800px"
      :footer="null"
      wrap-class-name="job-log-modal"
    >
      <div v-if="logLoading" class="log-loading">
        <a-spin tip="加载中..." />
      </div>
      <pre v-else class="job-log-content">{{ logContent }}</pre>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import type { Job, JobLog } from '@/api/job'
import { getJobs, getJob, deleteJob, getJobLogs } from '@/api/job'

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 70 },
  { title: '类型', dataIndex: 'type', key: 'type', width: 90 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '开始时间', dataIndex: 'begin_time', key: 'begin_time', width: 165, customRender: ({ text }: { text?: number }) => formatTime(text) },
  { title: '结束时间', dataIndex: 'end_time', key: 'end_time', width: 165, customRender: ({ text }: { text?: number }) => formatTime(text) },
  { title: '操作', key: 'action', width: 200, fixed: 'right' },
]

const jobList = ref<Job[]>([])
const loading = ref(false)
const detailVisible = ref(false)
const logVisible = ref(false)
const logLoading = ref(false)
const currentJob = ref<Job | null>(null)
const logContent = ref('')

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`,
})

function formatTime(ts?: number | null): string {
  if (ts == null) return '-'
  const d = new Date(ts)
  return Number.isNaN(d.getTime()) ? '-' : d.toLocaleString()
}

function statusColor(status: string): string {
  const map: Record<string, string> = {
    waiting: 'default',
    running: 'processing',
    stopped: 'warning',
    success: 'success',
    failed: 'error',
  }
  return map[status] ?? 'default'
}

async function fetchList() {
  loading.value = true
  try {
    const res = await getJobs({
      skip: (pagination.current - 1) * pagination.pageSize,
      limit: pagination.pageSize,
    })
    jobList.value = res.data ?? []
    pagination.total = (res as { total?: number }).total ?? 0
  } catch (e) {
    message.error('获取作业列表失败')
  } finally {
    loading.value = false
  }
}

function handleTableChange(pag: { current?: number; pageSize?: number }) {
  if (pag.current != null) pagination.current = pag.current
  if (pag.pageSize != null) pagination.pageSize = pag.pageSize
  fetchList()
}

async function handleView(record: Job) {
  try {
    const res = await getJob(record.id)
    currentJob.value = res.data ?? null
    detailVisible.value = true
  } catch {
    message.error('获取作业详情失败')
  }
}

async function handleViewLogs(record: Job) {
  logVisible.value = true
  logContent.value = ''
  logLoading.value = true
  try {
    const res = await getJobLogs(record.id)
    const logs = (res.data ?? []) as JobLog[]
    logContent.value = logs.map((l) => l.content).join('')
  } catch {
    message.error('获取作业日志失败')
    logContent.value = '加载失败'
  } finally {
    logLoading.value = false
  }
}

async function handleDelete(id: number) {
  try {
    await deleteJob(id)
    message.success('删除成功')
    fetchList()
  } catch {
    message.error('删除失败')
  }
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.page-header {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.page-header h1 {
  margin: 0;
  font-size: 20px;
}
.setting-pre {
  margin: 0;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow: auto;
}
.log-loading {
  padding: 24px;
  text-align: center;
}
.job-log-content {
  margin: 0;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 4px;
  max-height: 60vh;
  overflow: auto;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
