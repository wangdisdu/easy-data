# Easy Data

Easy Data 是一个可以使用自然语言与数据对话的智能平台，让数据分析变得简单、直观、高效。

## 项目概述

Easy Data 革命性地改变了数据分析的交互模式。用户所有操作全部通过自然语言与系统交互，不再受限于传统的Web交互方式（如点击按钮、填写表单、选择下拉菜单等）。用户只需用自然语言描述需求，系统即可理解并执行，真正实现了"说人话，做分析"的智能化体验。

## 技术栈

### 后端
- **语言**: Python 3.12
- **Web框架**: FastAPI + Pydantic + SQLAlchemy
- **认证**: JWT
- **AI Agent**: LangGraph + LangChain
- **数据库**: SQLite / PostgreSQL / MySQL
- **向量数据库**: Milvus

### 前端
- **框架**: Vue 3 + TypeScript
- **UI组件库**: Ant Design Vue
- **图表库**: ECharts
- **状态管理**: Pinia
- **路由**: Vue Router
- **HTTP客户端**: Axios

## 项目结构

```
easy-data/
├── backend/              # 后端服务
│   ├── app/
│   │   ├── api/         # API路由
│   │   ├── core/        # 核心配置
│   │   ├── db/          # 数据库模型
│   │   ├── services/    # 业务服务
│   │   └── main.py      # 应用入口
│   └── requirements.txt # Python依赖
├── frontend/            # 前端项目
│   ├── src/
│   │   ├── api/         # API接口
│   │   ├── components/  # 组件
│   │   ├── layouts/     # 布局
│   │   ├── router/      # 路由
│   │   ├── stores/      # 状态管理
│   │   ├── utils/       # 工具函数
│   │   └── views/       # 页面
│   └── package.json     # Node依赖
└── doc/                 # 文档
```

## 快速开始

### 后端启动

1. 安装依赖
```bash
cd backend
pip install -r requirements.txt
```

2. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库、JWT密钥等
```

3. 启动服务
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端服务将运行在 `http://localhost:8000`

API文档可在 `http://localhost:8000/api/docs` 查看

### 前端启动

1. 安装依赖
```bash
cd frontend
npm install
```

2. 启动开发服务器
```bash
npm run dev
```

前端应用将运行在 `http://localhost:5173`

### 访问应用

- **对话域（默认入口）**: http://localhost:5173/
- **管理域**: http://localhost:5173/admin
- **登录页面**: http://localhost:5173/login

## Docker 部署

项目支持使用 Docker 一键构建并运行，同时提供后端 API 与前端静态资源，无需单独部署 Nginx。

**前提**：已安装 Docker。

```bash
# 构建前请先将前端构建产物放入 backend/www（如：cd frontend && npm run build && cp -r dist ../backend/www）
# 构建镜像（基础镜像为 python:3.12-slim-bookworm）
make docker-build

# 后台运行容器，映射端口 8000
make docker-run
```

访问 **http://localhost:8000** 即可使用（API 文档：http://localhost:8000/api/docs）。

停止并删除容器：

```bash
make docker-stop
```

如需持久化数据（如 SQLite），可在 `docker run` 时挂载卷并设置环境变量 `DATABASE_URL` 指向卷内路径。

## 功能特性

### 对话域（Chat Domain）
- 自然语言交互界面
- 支持多轮对话
- 智能数据分析
- 结果可视化展示

### 管理域（Admin Domain）
- 工作空间管理
- 数据源管理
- 数据模型管理
- 用户管理

## 数据库设计

系统包含以下核心表：
- `tb_user`: 用户表
- `tb_work_space`: 工作空间表
- `tb_data_source`: 数据源表
- `tb_data_model`: 数据模型表

## API接口

### 认证接口
- `POST /api/v1/auth/register`: 用户注册
- `POST /api/v1/auth/login`: 用户登录
- `GET /api/v1/auth/me`: 获取当前用户信息

### 对话接口
- `POST /api/v1/chat/message`: 发送消息（同步）
- `WS /api/v1/chat/ws`: WebSocket对话接口

### 工作空间接口
- `GET /api/v1/workspaces`: 获取工作空间列表
- `POST /api/v1/workspaces`: 创建工作空间
- `GET /api/v1/workspaces/{id}`: 获取工作空间详情
- `PUT /api/v1/workspaces/{id}`: 更新工作空间
- `DELETE /api/v1/workspaces/{id}`: 删除工作空间

### 数据源接口
- `GET /api/v1/data-sources`: 获取数据源列表
- `POST /api/v1/data-sources`: 创建数据源
- `POST /api/v1/data-sources/{id}/test`: 测试数据源连接

### 数据模型接口
- `GET /api/v1/data-models`: 获取数据模型列表
- `POST /api/v1/data-models`: 创建数据模型

### 用户管理接口
- `GET /api/v1/users`: 获取用户列表
- `PUT /api/v1/users/{id}`: 更新用户
- `DELETE /api/v1/users/{id}`: 删除用户

## 开发说明

### 后端开发
- 使用 FastAPI 构建 RESTful API
- 使用 SQLAlchemy 进行数据库ORM操作
- 使用 Pydantic 进行数据验证
- 使用 LangChain/LangGraph 构建 AI Agent

### 前端开发
- 使用 Vue 3 Composition API
- 使用 TypeScript 进行类型检查
- 使用 Ant Design Vue 组件库
- 使用 Pinia 进行状态管理

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

