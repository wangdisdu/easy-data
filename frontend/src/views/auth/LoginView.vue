<template>
  <div class="login-container">
    <div class="login-box">
      <h1 class="login-title">Easy Data</h1>
      <p class="login-subtitle">致力于做真正的的智能平台</p>

      <a-form
        :model="form"
        :rules="rules"
        @finish="handleLogin"
        layout="vertical"
        class="login-form"
      >
        <a-form-item name="username" label="账号">
          <a-input v-model:value="form.username" size="large" placeholder="请输入账号" />
        </a-form-item>

        <a-form-item name="password" label="密码">
          <a-input-password
            v-model:value="form.password"
            size="large"
            placeholder="请输入密码"
          />
        </a-form-item>

        <a-form-item>
          <a-button
            type="primary"
            html-type="submit"
            size="large"
            block
            :loading="loading"
          >
            登录
          </a-button>
        </a-form-item>

        <a-form-item>
          <div class="login-footer">
            <a-button type="link" @click="showRegisterModal = true">
              注册账号
            </a-button>
          </div>
        </a-form-item>
      </a-form>
    </div>

    <!-- 注册弹窗 -->
    <a-modal
      v-model:open="showRegisterModal"
      title="注册账号"
      @ok="handleRegister"
      :confirm-loading="registerLoading"
    >
      <a-form :model="registerForm" layout="vertical">
        <a-form-item label="账号" required>
          <a-input v-model:value="registerForm.account" placeholder="请输入账号" />
        </a-form-item>
        <a-form-item label="姓名" required>
          <a-input v-model:value="registerForm.name" placeholder="请输入姓名" />
        </a-form-item>
        <a-form-item label="密码" required>
          <a-input-password v-model:value="registerForm.passwd" placeholder="请输入密码" />
        </a-form-item>
        <a-form-item label="邮箱">
          <a-input v-model:value="registerForm.email" placeholder="请输入邮箱" />
        </a-form-item>
        <a-form-item label="手机">
          <a-input v-model:value="registerForm.phone" placeholder="请输入手机号" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const form = reactive({
  username: '',
  password: '',
})

const registerForm = reactive({
  account: '',
  name: '',
  passwd: '',
  email: '',
  phone: '',
})

const loading = ref(false)
const registerLoading = ref(false)
const showRegisterModal = ref(false)

const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const handleLogin = async () => {
  loading.value = true
  try {
    await authStore.login({
      username: form.username,
      password: form.password,
    })

    message.success('登录成功')

    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch (error: any) {
    message.error(error.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}

const handleRegister = async () => {
  if (!registerForm.account || !registerForm.name || !registerForm.passwd) {
    message.error('请填写必填项')
    return
  }

  registerLoading.value = true
  try {
    await authStore.register(registerForm)
    message.success('注册成功，请登录')
    showRegisterModal.value = false
    // 清空注册表单
    Object.assign(registerForm, {
      account: '',
      name: '',
      passwd: '',
      email: '',
      phone: '',
    })
  } catch (error: any) {
    message.error(error.response?.data?.detail || '注册失败')
  } finally {
    registerLoading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-box {
  width: 400px;
  padding: 40px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.15);
}

.login-title {
  text-align: center;
  font-size: 32px;
  font-weight: bold;
  margin-bottom: 8px;
  color: #1890ff;
}

.login-subtitle {
  text-align: center;
  color: #666;
  margin-bottom: 32px;
}

.login-footer {
  display: flex;
  justify-content: space-between;
}
</style>

