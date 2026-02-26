# Easy Data 项目 AI Coding 开发规范

本文档为使用 AI Coding 时的项目规范，按**前端**与**后端**两部分说明。 代码布局：
- `doc/` 文档；
- `backend/` FastAPI 后端；
- `frontend/` Vue 3 + TypeScript 前端。

---

## 一、后端

### 1.1 技术栈

| 类别     | 选型 |
|----------|------|
| 语言     | Python 3.12 |
| Web 框架 | FastAPI |
| ORM      | SQLAlchemy 2.x |
| 数据验证 | Pydantic 2.x |
| 认证     | JWT（python-jose） |
| AI/Agent | LangChain + LangGraph |
| 构建/规范 | pyproject.toml，Black + isort + Ruff |

开发命令（在 backend 目录）：`make develop`（安装开发依赖）、`make code-format`（格式化）、`make code-check`（检查）。

### 1.2 分层与职责

- **API 层**（`app/api/`）：路由、参数校验、调用服务、返回 `Resp`/`PagedResp`；**获取当前用户**在 API 层完成（如 `get_current_user`），不放到 service。
- **服务层**（`app/services/`）：业务逻辑、事务、调用 DAO；服务层获取数据库会话，不依赖「当前用户」从哪来。
- **DAO 层**（`app/dao/`）：数据库模型与访问，表名以 `Tb` 开头（如 `TbAgent`、`TbDataSource`）。
- **连接器**（`app/connector/`）：只读访问外部数据源，**禁止在 connector 中修改数据**；提供测试连接、获取库/表信息、执行查询等。

服务层所需的请求/响应模型（Pydantic）定义在服务包下或与接口共享，不散落在 API 里。

### 1.3 统一响应与异常

- **HTTP 响应体**：统一为 `Resp[T]` 或分页 `PagedResp[T]`（`app/core/models.py`）：
  - `code`：字符串，`"0000"` 表示成功，其它为失败。
  - `msg`：提示信息；失败时由前端展示。
  - `data`：业务数据；分页时 `data` 为列表，且带有 `total`。

- **业务异常**：使用 `BizError`（`app/core/biz_error.py`），传入 `BizErrorCode` 与 `message`。API 和 service 中不直接抛 `ValueError`、`HTTPException` 等，由全局异常处理将 `BizError` 转为 HTTP 200 + `Resp(code!=0000, msg=...)`。

- **错误码**：在 `BizErrorCode` 中按模块分段定义（如 1000+ 通用、1100+ 认证、1400+ 数据源等），新增能力时在此扩展。

### 1.4 日志

- **统一使用** `from app.core.logging import get_logger`，`logger = get_logger(__name__)`。
- 不在 `app/api`、`app/connector`、`app/services` 下使用 `import logging` 或 `logging.getLogger`。
- 异常处优先使用 `logger.exception` 等规范写法，避免仅用 `print`。

### 1.5 智能体（Agent）与 LangGraph

- **可运行智能体**：由 `app/services/agent_executor.py` 中的 `AgentExecutor` 根据 DB 中的智能体配置（节点、边）动态构建 LangGraph 并执行。
- **节点类型**：start、end、llm、tool、python、subgraph、condition 等，对应 `app/graph/` 下各 builder（如 `llm_node`、`tool_node`、`condition_node`、`python_node`）。
- **持久化**：`tb_agent`、`tb_agent_node`、`tb_agent_edge`、`tb_agent_tool`、`tb_tool` 等；编辑在管理端「智能体」模块，DAG 使用 AntV X6。

**设计原则**（来自 ai-coding-wangdi 的提炼）：
- **入口设计**：第一个节点通常包含「能力说明 + 一个用于确认目标的 tool」。若用户意图不在能力范围内，模型不发起工具调用，流程直接结束；若发起工具调用，则视为进入主流程。
- **节点粒度**：不宜过细（否则像固定工作流），也不宜过粗（复杂推理全压给模型效果差）。同一类小步骤可放在一个 node 内（例如多步 SQL 探索在一个「执行 SQL」节点内循环）。
- **状态与工具**：关键上下文可由 tool 通过 Command 的 `update` 写回 GraphState，避免仅从 ToolMessage 里解析。
- **流式输出**：智能体对外统一用 `astream`，返回结构为 `{"chunk": "..."}`，必要时带 `tool_call_id` / `tool_result_id`。
- **提示词**：按职责拆文件（如 `*_agent_prompts.py`），用模版生成动态部分；每个 node 的 system prompt 只关注本节点目标，意图识别节点的提示词可包含全局能力说明。

### 1.6 数据源与连接器

- **connector**：仅负责连接与只读操作（测试连接、库/表/视图信息、执行查询）；**禁止在 connector 中写库**。
- **测试连接**：由前端传参（如数据源配置），调用类似 `POST /data-sources/{id}/test` 的接口；失败时 HTTP 仍为 200，失败原因放在 `Resp.msg` 或约定字段中。
- **多库支持**：MySQL、PostgreSQL、SQL Server、Oracle、ClickHouse、Doris、SQLite 等，各连接器在 `app/connector/` 下实现统一接口（测试连接、执行查询、结果归一化为可 JSON 序列化的结构）。

### 1.7 数据库与初始化

- 表结构变更需同步考虑：DAO 模型、迁移（若有）、API 入参/出参、前端表单与列表。
- 初始化数据：种子数据在 `app/dao/data/` 包中声明（tb_llm、tool_rows + tools/*、agent_rows + agents/*、tb_agent），可由 scripts/generate_export_data.py 生成 init_db_data.py 后再用 scripts/split_seed_data.py 拆分为 data 包；初始化逻辑在 `app/dao/init_db.py` 中，通过可执行脚本或启动时触发，不在业务接口里散落。

---

## 二、前端

### 2.1 技术栈

| 类别     | 选型 |
|----------|------|
| 框架     | Vue 3（Composition API） |
| 语言     | TypeScript |
| 构建     | Vite |
| UI       | Ant Design Vue |
| 状态     | Pinia |
| 路由     | Vue Router |
| HTTP     | Axios（封装在 `src/utils/request.ts`） |

### 2.2 与后端的对接

- 所有 HTTP API 返回均为 `Resp`：成功时 `code === '0000'`，`data` 为有效负载；失败时 `code !== '0000'`，`msg` 为错误原因。
- 前端在 `request` 拦截器中统一处理：`code !== '0000'` 时弹出错误提示（`message.error(res.msg)`），**只弹一次**，不重复弹窗。
- 分页接口：`data` 为列表，并带 `total`；前端按 `data` + `total` 做列表与分页。

### 2.3 页面与路由

- 视图放在 `src/views/`，按模块分子目录（如 `admin/agent/`、`chat/`）。
- 管理域使用 `AdminLayout`，左侧菜单、右侧内容；对话域、登录页为独立布局。对话域入口：`/`；管理域：`/admin`（需登录）；登录：`/login`。
- 新增页面：在 `src/views/` 增加组件，在 `src/router/index.ts` 中注册；需要登录的设 `meta: { requiresAuth: true }`。

### 2.4 样式与组件

- 全局样式保持简洁，页面级样式尽量少、必要即可。
- 优先使用 Ant Design Vue 组件，减少自定义样式；长文案（如列表「描述」）考虑截断或 Tooltip。

### 2.5 Chat 与 WebSocket

- 对话使用 WebSocket（如 `/ws/chat/{agent_id}`），需认证；token 校验通过后与 user_id 绑定，长连接内不再重复认证。
- 流式结果需支持 Markdown 渲染及「工具调用/结果」的折叠展示（如灰色、可展开）。

---

## 三、AI Coding

- **持续更新**: 当遇遇到新的重要约定时，记得更新本文档 doc/project-ai-coding-guidelines.md
