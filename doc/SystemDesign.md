# Easy Data 系统技术设计文档

本文档包含 Easy Data 系统的技术实现细节，包括技术栈选型、数据模型设计、API设计、安全设计、性能设计等。

## 1. 技术栈选型

采用前后分离开发模式，分为前端项目frontend和后端项目backend。

### 1.1 后端服务技术选型

**核心框架：**

- **语言**：Python 3.12
- **Web框架**：FastAPI + Pydantic + SQLAlchemy
- **认证**：JWT
- **模版引擎**：jinja

**Agent开发：**

- **开发框架**：LangGraph + LangChain
- **运行监控框架**：LangSmith

**数据存储：**

- **主数据库**：Sqlite、Postgresql、Mysql
- **向量数据库**：Milvus

### 1.2 前端技术选型

**前端框架：**

- **框架**：Vue 3 + TypeScript
- **UI组件库**：Ant Design Vue
- **图表库**：ECharts
- **实时通信**：WebSocket
- **状态管理**：Pinia
- **路由**：Vue Router
- **HTTP客户端**：Axios

### 1.3 前端说明

整个前端分为两个部分：对话域和管理域

#### 对话域

系统对外接口，用户使用该页面和系统交互，默认入口

#### 管理域

运维管理系统的入口，管理员通过该功能运维整个系统，比如用户管理、数据源管理、数据模型管理等等。
该域下的页面使用传统的布局，左侧为导航菜单，右侧为内容区域。

## 2. 数据库设计

### 数据库规范

#### 表名规范

- 使用下划线命名法（low_snake_case）
- 统一使用小写字母
- 表使用`tb_`前缀
- 视图使用`tv_`前缀

#### 字段命名规范

- 使用下划线命名法（low_snake_case）
- 使用小写英文字母
- 使用有意义的单词或缩写
- 禁止使用数字开头
- 禁止使用特殊字符
- 避免使用数据库关键字（select、update、delete、insert、create、drop、alter、truncate、grant、database、table、column、index、view等）
- 需要考虑兼容不同的数据库（mysql、sqlserver、oracle、postgresql、dm、oceanbase、gaussdb等）
- 避免使用不通用的字段类型（json等）

#### 字段类型选择

| 用途   | 字段类型          | 描述              |
|:-----|:--------------|:----------------|
| 主键   | bigint        | 长整型             |
| 时间   | bigint        | unix_ms，长整型     |
| 状态标识 | int           | 使用0/1表示布尔型      |
| 整数   | int           | 一般整数数值          |
| 短文本  | varchar(255)  | 一般文本字段          |
| 中文本  | varchar(1024) | 较长的文本字段，如描述信息字段 |
| 长文本  | text          | 长文本，如日志信息字段     |

#### 字段注释规范

- 所有字段建议有 COMMENT 注释
- 使用中文注释，简洁明了
- 如有枚举值，在注释中说明，如：COMMENT '状态：DRAFT草稿，RUNNING运行中，STOPPED已停

#### 必要的审计字段

- 创建时间，create_time
- 修改时间，update_time
- 创建人，create_user
- 修改人，update_user

```sql
create_time bigint NOT NULL COMMENT '创建时间',
update_time bigint NOT NULL COMMENT '更新时间',
create_user bigint DEFAULT NULL COMMENT '创建人',
update_user bigint DEFAULT NULL COMMENT '更新人',
```

#### 常用字段设计

- ID：id，主键，bigint类型，使用snowflake算法生成
- 编码：code，唯一标识，通常要求符合low_snake_case
- 名称：name，显示名称，通常要求唯一性，无格式要求
- 描述：description，描述信息，varchar(1024)类型

### 用户 - tb_user

- id: '主键ID',
- guid: '唯一编码',
- name: '名字',
- account: '账号',
- passwd: '密码',
- email: '邮箱',
- phone: '手机',

### 工作空间 - tb_work_space

- id: '主键ID',
- code: '唯一编码',
- name: '空间名称',
- description: '空间说明',
- extend: '扩展信息',

### 数据源 - tb_data_source

- id: '主键ID',
- code: '唯一编码',
- name: '地址名称',
- platform: '数据库类型',
- setting: '数据库配置信息',
- description: '地址说明',
- extend: '扩展信息',

### 数据模型 - tb_data_model

- id: '主键ID',
- code: '唯一编码',
- name: '地址名称',
- platform: '数据库类型',
- smantic: '数据模型语义模型',
- description: '数据模型说明',
- extend: '扩展信息',

