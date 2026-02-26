import { createRouter, createWebHistory } from 'vue-router'
import { getLlmDefaultStatus } from '@/api/system'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'chat',
      component: () => import('@/views/chat/ChatView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/system-init',
      name: 'system-init',
      component: () => import('@/views/system/SystemInitView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/auth/LoginView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/admin/agents/:id/edit',
      name: 'admin-agent-edit',
      component: () => import('@/views/admin/agent/AgentEditorView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/agents/new',
      name: 'admin-agent-new',
      component: () => import('@/views/admin/agent/AgentEditorView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin',
      component: () => import('@/layouts/AdminLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          redirect: '/admin/workspaces',
        },
        {
          path: 'workspaces',
          name: 'admin-workspaces',
          component: () => import('@/views/admin/workspace/WorkspaceView.vue'),
        },
        {
          path: 'data-sources',
          name: 'admin-data-sources',
          component: () => import('@/views/admin/dataSource/DataSourceView.vue'),
        },
        {
          path: 'data-models',
          name: 'admin-data-models',
          component: () => import('@/views/admin/dataModel/DataModelView.vue'),
        },
        {
          path: 'data-query',
          name: 'admin-data-query',
          component: () => import('@/views/admin/dataQuery/DataQueryView.vue'),
        },
        {
          path: 'users',
          name: 'admin-users',
          component: () => import('@/views/admin/user/UserView.vue'),
        },
        {
          path: 'agents',
          name: 'admin-agents',
          component: () => import('@/views/admin/agent/AgentView.vue'),
        },
        {
          path: 'tools',
          name: 'admin-tools',
          component: () => import('@/views/admin/tool/ToolView.vue'),
        },
        {
          path: 'llms',
          name: 'admin-llms',
          component: () => import('@/views/admin/llm/LlmView.vue'),
        },
      ],
    },
  ],
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  // 进入首页（对话页）时检查默认 LLM 是否已配置，未配置则跳转系统初始化页
  if (to.path === '/') {
    getLlmDefaultStatus()
      .then((res) => {
        if (res.data?.configured) {
          next()
        } else {
          next({ path: '/system-init' })
        }
      })
      .catch(() => next())
    return
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated()) {
    next({ name: 'login', query: { redirect: to.fullPath } })
  } else {
    next()
  }
})

export default router
