# Easy Data Frontend

Easy Data 前端应用，基于 Vue 3 + TypeScript 构建的现代化 Web 应用。

## 技术栈

- **框架**: Vue 3.5.25
- **语言**: TypeScript 5.9
- **构建工具**: Vite 7.2.4
- **UI组件库**: Ant Design Vue 4.2.6
- **图表库**: ECharts 6.0.0
- **状态管理**: Pinia 3.0.4
- **路由**: Vue Router 4.6.3
- **HTTP客户端**: Axios 1.13.2
- **代码规范**: ESLint + Prettier

## 项目结构

```
frontend/
├── public/                 # 静态资源
│   └── favicon.ico
├── src/
│   ├── api/               # API接口封装
│   │   ├── chat.ts        # 对话接口
│   │   ├── user.ts        # 用户接口
│   │   ├── workspace.ts   # 工作空间接口
│   │   ├── dataSource.ts  # 数据源接口
│   │   └── dataModel.ts   # 数据模型接口
│   ├── assets/            # 资源文件
│   │   ├── base.css
│   │   ├── main.css
│   │   └── logo.svg
│   ├── components/         # 公共组件
│   ├── layouts/           # 布局组件
│   │   └── AdminLayout.vue # 管理后台布局
│   ├── router/            # 路由配置
│   │   └── index.ts
│   ├── stores/            # 状态管理
│   │   ├── auth.ts        # 认证状态
│   │   └── counter.ts     # 示例状态（可删除）
│   ├── utils/             # 工具函数
│   │   └── request.ts     # Axios封装
│   ├── views/             # 页面组件
│   │   ├── auth/          # 认证页面
│   │   │   └── LoginView.vue
│   │   ├── chat/          # 对话域
│   │   │   └── ChatView.vue
│   │   └── admin/         # 管理域
│   │       ├── DashboardView.vue
│   │       ├── workspace/
│   │       ├── dataSource/
│   │       ├── dataModel/
│   │       └── user/
│   ├── App.vue            # 根组件
│   └── main.ts            # 入口文件
├── index.html             # HTML模板
├── package.json           # 项目配置
├── tsconfig.json          # TypeScript配置
├── vite.config.ts         # Vite配置
└── README.md              # 本文档
```

## 快速开始

### 1. 环境要求

- Node.js 20.19.0+ 或 22.12.0+
- npm 或 yarn 或 pnpm

### 2. 安装依赖

```bash
npm install
# 或
yarn install
# 或
pnpm install
```

### 3. 配置环境变量

创建 `.env.development` 文件：

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

创建 `.env.production` 文件：

```bash
VITE_API_BASE_URL=/api/v1
```

### 4. 启动开发服务器

```bash
npm run dev
```

应用将在 `http://localhost:5173` 启动。

### 5. 构建生产版本

```bash
npm run build
```

构建产物将输出到 `dist/` 目录。

### 6. 预览生产构建

```bash
npm run preview
```

### 7. Vite 缓存清理说明

如果遇到模块导入错误（如 Axios 类型导入问题），可以尝试以下方法：

#### 方法 1: 清除 Vite 缓存并重新启动

```bash
cd frontend
rm -rf node_modules/.vite
npm run dev
```

#### 方法 2: 完全重新安装依赖

```bash
cd frontend
rm -rf node_modules
rm -rf node_modules/.vite
npm install
npm run dev
```

#### 方法 3: 强制重新构建依赖

```bash
cd frontend
npm run dev -- --force
```

## 功能模块

### 对话域（Chat Domain）

**路径**: `/`

自然语言交互界面，用户可以通过自然语言与系统对话，进行数据分析。

**主要功能**:

- 多轮对话支持
- 消息历史记录
- 实时响应
- 支持 WebSocket 连接

**组件**: `src/views/chat/ChatView.vue`

### 管理域（Admin Domain）

**路径**: `/admin`

传统布局的管理后台，左侧导航菜单，右侧内容区域。

**主要功能**:

- 仪表盘：系统概览和统计
- 工作空间管理：创建、编辑、删除工作空间
- 数据源管理：配置和测试数据源连接
- 数据模型管理：管理数据模型和语义配置
- 用户管理：管理系统用户

**布局组件**: `src/layouts/AdminLayout.vue`

### 认证模块

**路径**: `/login`

用户登录和注册功能。

**功能**:

- 用户登录（JWT认证）
- 用户注册
- 自动跳转到管理后台

**组件**: `src/views/auth/LoginView.vue`

## 路由配置

路由定义在 `src/router/index.ts` 中：

```typescript
{
  path: '/',              // 对话域（默认入口）
  name: 'chat',
  component: ChatView,
  meta: { requiresAuth: false }
},
{
  path: '/login',         // 登录页面
  name: 'login',
  component: LoginView,
  meta: { requiresAuth: false }
},
{
  path: '/admin',         // 管理域
  component: AdminLayout,
  meta: { requiresAuth: true },
  children: [
    { path: 'dashboard', ... },
    { path: 'workspaces', ... },
    { path: 'data-sources', ... },
    { path: 'data-models', ... },
    { path: 'users', ... }
  ]
}
```

## 状态管理

使用 Pinia 进行状态管理。

### 认证状态（auth store）

**文件**: `src/stores/auth.ts`

**状态**:

- `token`: JWT令牌
- `user`: 当前用户信息

**方法**:

- `login()`: 用户登录
- `register()`: 用户注册
- `getUserInfo()`: 获取用户信息
- `logout()`: 退出登录
- `isAuthenticated()`: 检查是否已登录

**使用示例**:

```typescript
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
await authStore.login({ username: 'user', password: 'pass' })
```

## API 封装

所有 API 请求通过 `src/utils/request.ts` 封装，自动处理：

- JWT Token 注入
- 请求/响应拦截
- 错误处理
- 统一错误提示

**使用示例**:

```typescript
import { getWorkspaces } from '@/api/workspace'

const workspaces = await getWorkspaces({ skip: 0, limit: 10 })
```

## 开发指南

### 添加新页面

1. 在 `src/views/` 下创建页面组件
2. 在 `src/router/index.ts` 中添加路由配置
3. 如需认证，设置 `meta: { requiresAuth: true }`

### 添加新 API 接口

1. 在 `src/api/` 下创建接口文件
2. 使用 `request` 工具发送请求
3. 定义 TypeScript 类型

示例：

```typescript
// src/api/example.ts
import request from '@/utils/request'

export interface Example {
  id: number
  name: string
}

export const getExamples = () => {
  return request.get<Example[]>('/examples')
}
```

### 添加新组件

1. 在 `src/components/` 下创建组件
2. 使用 `<script setup lang="ts">` 语法
3. 使用 Ant Design Vue 组件

### 使用 Ant Design Vue

```vue
<template>
  <a-button type="primary" @click="handleClick">
    按钮
  </a-button>
  <a-table :columns="columns" :data-source="data" />
</template>

<script setup lang="ts">
import { Button as AButton, Table as ATable } from 'ant-design-vue'
</script>
```

### 使用 ECharts

```vue
<template>
  <div ref="chartRef" style="width: 100%; height: 400px;"></div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'

const chartRef = ref<HTMLDivElement>()

onMounted(() => {
  const chart = echarts.init(chartRef.value!)
  chart.setOption({
    // ECharts 配置
  })
})
</script>
```

## 代码规范

### TypeScript

- 使用 TypeScript 严格模式
- 为所有函数和变量定义类型
- 使用接口定义数据结构

### 代码格式化

```bash
# 格式化代码
npm run format

# 检查代码规范
npm run lint
```

### 类型检查

```bash
npm run type-check
```

## 环境变量

| 变量名                 | 说明       | 开发环境                         | 生产环境    |
|---------------------|----------|------------------------------|---------|
| `VITE_API_BASE_URL` | API基础URL | http://localhost:8000/api/v1 | /api/v1 |

**注意**: Vite 要求环境变量以 `VITE_` 开头才能在前端代码中访问。

## 构建和部署

### 开发环境

```bash
npm run dev
```

### 生产构建

```bash
npm run build
```

构建产物在 `dist/` 目录，可以部署到任何静态文件服务器。

## 常见问题

### 1. 跨域问题

确保后端 CORS 配置包含前端地址，或使用 Vite 代理（已配置）。

### 2. API 请求失败

检查 `VITE_API_BASE_URL` 配置是否正确，确保后端服务已启动。

### 3. 路由刷新 404

配置服务器将所有路由指向 `index.html`（见 Nginx 配置示例）。

### 4. TypeScript 类型错误

运行 `npm run type-check` 检查类型错误，确保所有类型定义正确。

## 浏览器支持

- Chrome (最新)
- Firefox (最新)
- Safari (最新)
- Edge (最新)

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
