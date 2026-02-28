<template>
  <div class="system-init-page">
    <div class="page-body">
      <header class="page-header">
        <h1 class="page-title">系统初始化</h1>
      </header>

      <div class="main-layout">
        <a-card class="form-card" title="大模型配置">
          <a-form
            :model="form"
            :rules="formRules"
            @finish="handleSubmit"
            layout="vertical"
            :label-col="{ span: 24 }"
            :wrapper-col="{ span: 24 }"
          >
            <a-form-item name="provider" label="模型提供商">
              <a-select
                v-model:value="form.provider"
                placeholder="请选择模型提供商"
                @change="handleProviderChange"
                allow-clear
              >
                <a-select-option value="openai">OpenAI</a-select-option>
                <a-select-option value="bailian">阿里云百炼</a-select-option>
                <a-select-option value="bigmodel">智谱模型</a-select-option>
                <a-select-option value="volcengine">火山引擎</a-select-option>
                <a-select-option value="siliconflow">硅基流动</a-select-option>
              </a-select>
            </a-form-item>

            <a-form-item name="model" label="模型名称">
              <a-input
                v-model:value="form.model"
                placeholder="例如：gpt-4、qwen-max、glm-4-flash 等"
              />
            </a-form-item>

            <a-form-item name="api_key" label="API 密钥">
              <a-input-password
                v-model:value="form.api_key"
                placeholder="请输入 API 密钥"
              />
            </a-form-item>

            <a-form-item name="base_url" label="API 基础 URL">
              <a-input
                v-model:value="form.base_url"
                placeholder="例如：https://dashscope.aliyuncs.com/compatible-mode/v1"
              />
            </a-form-item>

            <a-form-item>
              <a-button type="primary" html-type="submit" :loading="submitLoading">
                保存并进入对话
              </a-button>
            </a-form-item>
          </a-form>
        </a-card>

        <a-card class="guide-card" title="模型使用指引">
          <p class="guide-intro">
            本系统通过 <strong>OpenAI 兼容的 Base URL</strong> 调用大模型。请填写各厂商提供的兼容接口地址（多数国内厂商如阿里云百炼、智谱、火山引擎等均提供 OpenAI 兼容的 API 端点），并填写对应的模型名称与 API 密钥。
          </p>
          <p class="guide-intro">可在以下平台申请或查看 API 密钥：</p>
          <ul class="guide-links">
            <li>
              <span>智谱：</span>
              <a href="https://bigmodel.cn/console/overview" target="_blank" rel="noopener noreferrer">
                https://bigmodel.cn/console/overview
              </a>
            </li>
            <li>
              <span>阿里云百炼：</span>
              <a href="https://bailian.console.aliyun.com" target="_blank" rel="noopener noreferrer">
                https://bailian.console.aliyun.com
              </a>
            </li>
            <li>
              <span>火山引擎百炼：</span>
              <a href="https://console.volcengine.com" target="_blank" rel="noopener noreferrer">
                https://console.volcengine.com
              </a>
            </li>
            <li>
              <span>硅基流动：</span>
              <a href="https://cloud.siliconflow.cn" target="_blank" rel="noopener noreferrer">
                https://cloud.siliconflow.cn
              </a>
            </li>
          </ul>
        </a-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '@/stores/auth'
import { initLlm, type InitLlmBody } from '@/api/system'

const router = useRouter()
const authStore = useAuthStore()
const submitLoading = ref(false)

onMounted(() => {
  if (!authStore.isAuthenticated()) {
    router.replace({ name: 'login', query: { redirect: '/system-init' } })
  }
})

const form = reactive<InitLlmBody>({
  provider: '',
  model: '',
  api_key: '',
  base_url: '',
})

const formRules = {
  provider: [{ required: true, message: '请选择模型提供商' }],
  model: [{ required: true, message: '请输入模型名称' }],
  api_key: [{ required: true, message: '请输入 API 密钥' }],
  base_url: [{ required: true, message: '请输入 API 基础 URL' }],
}

const defaultUrls: Record<string, string> = {
  openai: 'https://api.openai.com/v1',
  bailian: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  bigmodel: 'https://open.bigmodel.cn/api/paas/v4',
  volcengine: 'https://ark.cn-beijing.volces.com/api/v3',
  siliconflow: 'https://api.siliconflow.cn/v1',
}

const handleProviderChange = () => {
  if (defaultUrls[form.provider]) {
    form.base_url = defaultUrls[form.provider]
  }
}

const handleSubmit = async () => {
  submitLoading.value = true
  try {
    await initLlm({
      provider: form.provider,
      model: form.model,
      api_key: form.api_key,
      base_url: form.base_url,
    })
    message.success('配置已保存')
    router.push('/')
  } catch {
    // 错误已由 request 拦截器提示
  } finally {
    submitLoading.value = false
  }
}
</script>

<style scoped>
.system-init-page {
  min-height: 100vh;
  background: #f0f2f5;
  padding: 32px 24px;
}

.page-body {
  max-width: 960px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 28px;
  text-align: center;
}

.page-title {
  margin: 0 0 10px;
  font-size: 22px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.88);
}

.page-desc {
  margin: 0;
  font-size: 14px;
  color: rgba(0, 0, 0, 0.65);
  line-height: 1.6;
  max-width: 560px;
  margin-left: auto;
  margin-right: auto;
}

.main-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  align-items: start;
}

@media (max-width: 768px) {
  .main-layout {
    grid-template-columns: 1fr;
  }
}

.form-card,
.guide-card {
  border-radius: 8px;
}

.form-card :deep(.ant-form-item:last-child) {
  margin-bottom: 0;
}

.guide-intro {
  margin: 0 0 12px;
  font-size: 13px;
  color: rgba(0, 0, 0, 0.65);
}

.guide-links {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  line-height: 1.8;
  color: rgba(0, 0, 0, 0.88);
}

.guide-links a {
  color: #1677ff;
  text-decoration: none;
}

.guide-links a:hover {
  text-decoration: underline;
}
</style>
