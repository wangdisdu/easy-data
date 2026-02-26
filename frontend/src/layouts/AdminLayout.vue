<template>
  <a-layout class="admin-layout">
    <a-layout-sider v-model:collapsed="collapsed" :width="200" theme="light">
      <div class="logo">
        <h2 v-if="!collapsed">Easy Data</h2>
        <h2 v-else>ED</h2>
      </div>
      <a-menu
        v-model:selectedKeys="selectedKeys"
        v-model:openKeys="openKeys"
        theme="light"
        mode="inline"
        :items="menuItems"
        @click="handleMenuClick"
        @openChange="handleOpenChange"
      />
    </a-layout-sider>
    <a-layout>
      <a-layout-header class="admin-header">
        <div class="header-left">
          <a-button
            type="text"
            @click="collapsed = !collapsed"
            style="font-size: 16px"
          >
            <MenuUnfoldOutlined v-if="collapsed" />
            <MenuFoldOutlined v-else />
          </a-button>
        </div>
        <div class="header-right">
          <a-dropdown>
            <a class="user-info" @click.prevent>
              <a-avatar :size="32" style="background-color: #1890ff">
                {{ authStore.user?.name?.charAt(0) || 'U' }}
              </a-avatar>
              <span style="margin-left: 8px">{{ authStore.user?.name || '用户' }}</span>
            </a>
            <template #overlay>
              <a-menu>
                <a-menu-item key="profile">
                  <UserOutlined />
                  个人资料
                </a-menu-item>
                <a-menu-divider />
                <a-menu-item key="logout" @click="handleLogout">
                  <LogoutOutlined />
                  退出登录
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </a-layout-header>
      <a-layout-content>
        <div class="admin-content">
          <router-view />
        </div>
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed, watch, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  CloudServerOutlined,
  DatabaseOutlined,
  TableOutlined,
  SearchOutlined,
  TeamOutlined,
  UserOutlined,
  LogoutOutlined,
  RobotOutlined,
  ToolOutlined,
  ApiOutlined,
  SettingOutlined,
  AppstoreOutlined,
} from '@ant-design/icons-vue'
import { useAuthStore } from '@/stores/auth'
import type { MenuProps } from 'ant-design-vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const collapsed = ref(false)
const selectedKeys = ref<string[]>([])
const openKeys = ref<string[]>([])

const menuItems: MenuProps['items'] = [
  {
    key: 'agent',
    icon: () => h(RobotOutlined),
    label: '智能体',
    children: [
      {
        key: '/admin/agents',
        icon: () => h(RobotOutlined),
        label: '智能体',
      },
      {
        key: '/admin/tools',
        icon: () => h(ToolOutlined),
        label: '工具管理',
      },
      {
        key: '/admin/llms',
        icon: () => h(ApiOutlined),
        label: 'LLM模型',
      },
    ],
  },
  {
    key: 'data-modeling',
    icon: () => h(AppstoreOutlined),
    label: '数据建模',
    children: [
      {
        key: '/admin/data-sources',
        icon: () => h(DatabaseOutlined),
        label: '数据源',
      },
      {
        key: '/admin/data-models',
        icon: () => h(TableOutlined),
        label: '数据模型',
      },
      {
        key: '/admin/data-query',
        icon: () => h(SearchOutlined),
        label: '数据查询',
      },
    ],
  },
  {
    key: 'system',
    icon: () => h(SettingOutlined),
    label: '系统管理',
    children: [
      {
        key: '/admin/workspaces',
        icon: () => h(CloudServerOutlined),
        label: '工作空间',
      },
      {
        key: '/admin/users',
        icon: () => h(TeamOutlined),
        label: '用户管理',
      },
    ],
  },
]

const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
  // 只处理子菜单项的点击，父菜单项不跳转
  if (key && typeof key === 'string' && key.startsWith('/admin/')) {
    router.push(key as string)
  }
}

const handleOpenChange = (keys: string[]) => {
  openKeys.value = keys
}

const handleLogout = () => {
  authStore.logout()
}

// 根据路径获取对应的父菜单key
const getParentMenuKey = (path: string): string | null => {
  if (path.startsWith('/admin/agents') || path.startsWith('/admin/tools') || path.startsWith('/admin/llms')) {
    return 'agent'
  }
  if (path.startsWith('/admin/data-sources') || path.startsWith('/admin/data-models') || path.startsWith('/admin/data-query')) {
    return 'data-modeling'
  }
  if (path.startsWith('/admin/workspaces') || path.startsWith('/admin/users')) {
    return 'system'
  }
  return null
}

// 监听路由变化，更新选中的菜单项和展开的父菜单
watch(
  () => route.path,
  (path) => {
    selectedKeys.value = [path]
    const parentKey = getParentMenuKey(path)
    if (parentKey && !openKeys.value.includes(parentKey)) {
      openKeys.value = [...openKeys.value, parentKey]
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #e8e8e8;
  margin-bottom: 16px;
}

.logo h2 {
  margin: 0;
  color: #1890ff;
  font-size: 20px;
}

.admin-header {
  background: white;
  padding: 0 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
  color: #333;
}

.admin-content {
  margin: 24px;
  padding: 24px;
  background: white;
  min-height: calc(100vh - 112px);
}
</style>

