# Easy Data Backend

Easy Data 后端服务，基于 FastAPI 构建的 RESTful API 服务，提供自然语言数据分析能力。

## 技术栈

- **语言**: Python 3.12+
- **Web 框架**: FastAPI
- **ORM**: SQLAlchemy 2.x
- **数据验证**: Pydantic 2.x
- **认证**: JWT (python-jose)
- **密码加密**: passlib[bcrypt]
- **AI Agent**: LangChain + LangGraph
- **数据库**: SQLite / PostgreSQL / MySQL
- **向量数据库**: Milvus (pymilvus)
- **缓存**: Redis
- **WebSocket**: websockets

## 项目结构

```
backend/
├── app/
│   ├── main.py              # 应用入口
│   ├── api/                 # API 路由
│   │   ├── auth.py, chat.py, users.py, workspaces.py
│   │   ├── data_sources.py, data_models.py, agents.py, llm.py, tools.py
│   ├── core/                # 核心配置与安全
│   ├── dao/                 # 数据访问（database、models）
│   ├── connector/           # 数据库连接器
│   ├── services/            # 业务服务与 Agent 执行
│   ├── agent/               # 智能体实现
│   └── tool/                # 工具函数
├── pyproject.toml
├── run.py
└── README.md
```

## 快速开始

### 1. 环境要求

- Python 3.12 或更高版本
- conda

#### 推荐使用conda

```bash
# 创建虚拟环境（推荐）
conda create --name easy-data python=3.12
conda activate easy-data
```

### 2. 安装依赖

项目使用 `pyproject.toml` 管理依赖，推荐使用国内镜像源加速安装。

#### 安装步骤

```bash
# 安装项目依赖
pip install -e .

# 安装开发环境（Black、isort、ruff 等），推荐使用 Makefile
make develop
# 或：pip install -e ".[dev]"
```

#### 使用国内镜像源（推荐）

**配置PIP国内镜像源（永久配置）**

```bash
# 使用清华大学镜像源（推荐）
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 或使用阿里云镜像源
# pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# 或使用腾讯云镜像源
# pip config set global.index-url https://mirrors.cloud.tencent.com/pypi/simple/

# 或使用中科大镜像源
# pip config set global.index-url https://pypi.mirrors.ustc.edu.cn/simple/
```

**临时使用镜像源（单次安装）**

```bash
# 使用清华大学镜像源
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装开发依赖
pip install -e ".[dev]" -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**注意**：如果已配置永久镜像源，直接运行 `pip install -e .` 和 `pip install -e ".[dev]"` 即可，无需添加 `-i` 参数。

### 3. 配置环境变量

创建 `.env` 文件（可参考 `.env.example`）：

```bash
# 应用配置
APP_NAME=Easy Data
APP_VERSION=1.0.0
DEBUG=True
SECRET_KEY=your-secret-key-here-change-in-production

# 数据库配置
DATABASE_URL=sqlite:///./easy_data.db
# 或使用 PostgreSQL
# DATABASE_URL=postgresql://user:password@localhost:5432/easy_data

# JWT配置
JWT_SECRET_KEY=your-jwt-secret-key-here-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=720

# CORS配置
CORS_ORIGINS=["http://localhost:5173"]

# Redis配置（可选）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Milvus配置（可选）
MILVUS_HOST=localhost
MILVUS_PORT=19530

# LLM配置
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1

# LangSmith 配置（可选）
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_PROJECT=your-project-name
```

### 4. 启动服务

#### 方式一：使用启动脚本

```bash
python run.py
```

#### 方式二：使用 uvicorn 直接启动

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 方式三：生产环境启动

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

服务启动后，访问：

- API 文档（Swagger）: http://localhost:8000/api/docs
- API 文档（ReDoc）: http://localhost:8000/api/redoc
- 健康检查: http://localhost:8000/health

## 开发指南

### Makefile 命令（推荐）

在 `backend` 目录下执行：

| 命令 | 说明 |
|------|------|
| `make develop` | 安装开发环境依赖（Black、isort、ruff 等） |
| `make code-format` | 使用 Black、isort、ruff 自动格式化代码 |
| `make code-check`   | 使用 Black、isort、ruff 检查代码（不修改） |

```bash
make develop   # 首次或依赖变更后
make code-format    # 提交前格式化
make code-check     # CI 或提交前检查
```

### IDE 集成

**VS Code**
- 安装扩展：Black Formatter、isort、Ruff
- 在 `.vscode/settings.json` 中配置：
```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

**PyCharm**
- 安装插件：Black、isort、Ruff
- 配置 External Tools 来运行这些工具

### 添加新的 API 端点

1. 在 `app/api/` 下新增或修改端点模块
2. 定义路由与业务逻辑
3. 在 `app/main.py` 中挂载路由

## 环境变量说明

| 变量名                               | 说明            | 默认值                       | 必填        |
|-----------------------------------|---------------|---------------------------|-----------|
| `APP_NAME`                        | 应用名称          | Easy Data                 | 否         |
| `APP_VERSION`                     | 应用版本          | 1.0.0                     | 否         |
| `DEBUG`                           | 调试模式          | True                      | 否         |
| `SECRET_KEY`                      | 应用密钥          | -                         | 是         |
| `DATABASE_URL`                    | 数据库连接URL      | sqlite:///./easy_data.db  | 是         |
| `JWT_SECRET_KEY`                  | JWT密钥         | -                         | 是         |
| `JWT_ALGORITHM`                   | JWT算法         | HS256                     | 否         |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token过期时间(分钟) | 30                        | 否         |
| `CORS_ORIGINS`                    | CORS允许的源      | ["http://localhost:5173"] | 否         |
| `OPENAI_API_KEY`                  | OpenAI API密钥  | -                         | 是（如需AI功能） |
| `OPENAI_BASE_URL`                 | OpenAI API地址  | https://api.openai.com/v1 | 否         |

## 数据库迁移

项目使用 SQLAlchemy 的自动建表功能。如需使用 Alembic 进行数据库迁移：

```bash
# 初始化 Alembic
alembic init alembic

# 创建迁移
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head
```

## 常见问题

### 1. 数据库连接失败

检查 `DATABASE_URL` 配置是否正确，确保数据库服务已启动。

### 2. JWT Token 验证失败

确保 `JWT_SECRET_KEY` 已正确配置，且前后端使用相同的密钥。

### 3. CORS 错误

检查 `CORS_ORIGINS` 配置，确保前端地址在允许列表中。

### 4. AI Agent 服务不可用

确保已配置 `OPENAI_API_KEY`，或安装相应的 LangChain 依赖。

### 5. pkg_resources 弃用警告

如果看到 `pkg_resources is deprecated` 警告，这是 PyCharm 调试器插件的问题，不影响项目运行。

**注意**：所有命令都需要先激活 conda 环境：

```bash
conda activate easy-data
```

## 部署

### Docker 部署

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 使用国内镜像源加速安装（可选）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装项目依赖
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 生产环境建议

1. 使用 PostgreSQL 或 MySQL 替代 SQLite
2. 配置 Redis 用于缓存和会话存储
3. 使用环境变量管理敏感配置
4. 配置 HTTPS
5. 使用进程管理器（如 systemd、supervisor）
6. 配置日志收集和监控

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

