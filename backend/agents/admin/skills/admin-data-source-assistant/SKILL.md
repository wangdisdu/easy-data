---
name: admin-data-source-assistant
description: 数据源管理助手。支持查询数据源、创建数据源、更新数据源信息、删除数据源；数据源用于存储多个外部数据库（mysql、postgresql、sqlserver、oracle、clickhouse、doris、sqlite 等）的连接信息。适用于用户要新增/列出/查看/修改/删除数据源、登记数据库连接或管理连接配置
---

# 数据源管理

## 能力

通过 SQL 操作表 **tb_data_source** 实现数据源的**增、删、改、查**。执行 SQL 使用 **tool_execute_sql_on_system_db**。

## 表 tb_data_source 字段

| 字段 | 类型 | 说明                                                                                                              |
|------|------|-----------------------------------------------------------------------------------------------------------------|
| id | 主键 | 自增                                                                                                              |
| code | 字符串，唯一 | 数据源编码，小写字母/数字/下划线，如 mysql01                                                                                     |
| name | 字符串 | 数据源名称，可中文                                                                                                       |
| platform | 字符串 | mysql, postgresql, sqlserver, oracle, clickhouse, doris, sqlite                                                 |
| setting | 长文本，必填 | 连接配置 **JSON 字符串**，格式如：{"host":"127.0.0.1","port":3306,"username":"root","password":"passxxx","database":"mydb"} |
| semantic | 长文本 | 语义说明                                                                                             |
| knowledge | 长文本 | 外部知识                                                                                                            |
| description | 长文本 | 描述                                                                                                              |
| create_time | 长整型 | 创建时间毫秒时间戳                                                                                                       |
| update_time | 长整型 | 更新时间毫秒时间戳                                                                                                       |

**查询约定**：查询多个数据源（列表）时**不要 SELECT semantic**；只查单条详情时可包含。列表建议查：id, code, name, platform, setting, create_time, update_time。

---

## 前置必须步骤（防重复与误操作）

在执行**创建、删除、更新**任一动作之前，**必须先**执行一次「查询所有数据源」，
用于：防止重复创建（校验 code、name、setting 是否与已有重复）、防止删除/更新不存在的数据源（校验目标 id 或 code 是否存在）。

- **必做**：先执行 `SELECT id, code, name, platform, setting, create_time, update_time FROM tb_data_source;` 获取当前全量列表。
- **创建前**：根据上述结果判断是否重复。满足以下**任一**即视为重复，需提示并拒绝创建：
  - **code** 已存在：已有数据源使用相同 code；
  - **name** 已存在：已有数据源使用相同 name；
  - **setting** 已存在：已有数据源的连接配置（setting 字符串）与待创建的一致，即指向同一库/同一连接。
- **删除/更新前**：根据上述结果确认目标 id 或 code 在列表中，不存在则提示「数据源不存在」并拒绝操作。

仅当用户仅做**查询**（列出、按 id/code 查单条）时，无需此前置；一旦涉及增删改，必须先查全量。

---

## 步骤说明

### 1. 创建数据源

- **前置 1**：先执行「查询所有数据源」（见上文），根据结果做**重复校验**：若已有数据源的 **code**、**name** 或 **setting**（连接配置）与待创建者任一相同，则视为重复，提示（如「该 code 已存在」「该名称已存在」或「该连接配置已存在」）并**拒绝创建**。
- **前置 2**：**必须先**调用 **tool_test_data_source_setting**(platform, host, port, username, password, database) 验证连接成功，否则不执行 INSERT。
- 不再单独查 code/name/setting（已由前置 1 的全量查询覆盖）。
- code 建议格式 `{platform}{序号}`（如 mysql01）；name 建议人类可读（如「MySQL生产环境-用户库」）
- 必填字段：code, name, platform, setting, create_time, update_time。
- create_time/update_time 用当前时间函数，如 SQLite：`(strftime('%s','now') * 1000)`。
- setting 为 JSON 字符串：
    - host: 数据库服务器的主机地址，例如：localhost, 192.168.1.100, db.example.com。注意：SQLite不需要此参数，可以传空字符串
    - port: 数据库服务器的端口号。MySQL默认3306,PostgreSQL默认5432,SQL Server默认1433,Oracle默认1521,ClickHouse默认9000,Doris默认9030。注意：SQLite不需要此参数，可以传0。
    - username: 用于连接数据库的用户名。注意：SQLite不需要此参数，可以传空字符串
    - password: 对应用户名的密码。注意：SQLite不需要此参数，可以传空字符串
    - database: 要连接的数据库名称。对于SQLite，此参数为文件路径（相对于backend/local_sqlite目录，如：chinook.sqlite），或绝对路径

**示例（MySQL）**
```sql
INSERT INTO tb_data_source (code, name, platform, setting, create_time, update_time)
VALUES ('mysql01', 'MySQL生产环境-用户库', 'mysql', '{"host":"192.168.1.100","port":3306,"username":"root","password":"xxx","database":"mydb"}', (strftime('%s','now') * 1000), (strftime('%s','now') * 1000));
```

**示例（SQLite）**
```sql
INSERT INTO tb_data_source (code, name, platform, setting, create_time, update_time)
VALUES ('sqlite01', 'SQLite - Chinook数据库', 'sqlite', '{"host":"","port":0,"username":"","password":"","database":"chinook.sqlite"}', (strftime('%s','now') * 1000), (strftime('%s','now') * 1000));
```

### 2. 删除数据源

- **前置**：依赖「查询所有数据源」结果，确认目标 **id 或 code** 在列表中；不存在则提示「数据源不存在」并**拒绝删除**。
- **边界**：检查关联模型 `SELECT COUNT(*) AS cnt FROM tb_data_model WHERE ds_id = <ds_id>`；若 cnt > 0，**拒绝删除**并提示先处理关联模型。
- 无关联时：`DELETE FROM tb_data_source WHERE id = <id>`。删除不可逆。

### 3. 更新数据源

- **前置**：依赖「查询所有数据源」结果，确认目标 **id 或 code** 在列表中；不存在则提示「数据源不存在」并**拒绝更新**。
- 可更新：name, setting, semantic, knowledge, update_time（不可改 code、platform）。setting 为 JSON 字符串；长文本内单引号转义为 `''`。update_time 用当前时间函数。
- 示例：`UPDATE tb_data_source SET name = '新名称', update_time = (strftime('%s','now') * 1000) WHERE id = 1;`

---

## 常见查询示例

- 列表（不查 semantic）：`SELECT id, code, name, platform, setting, create_time, update_time FROM tb_data_source;`
- 按 ID 查单条：`SELECT * FROM tb_data_source WHERE id = 1;`
- 按 code 查单条：`SELECT * FROM tb_data_source WHERE code = 'mysql01';`

---

## 可用工具

- **tool_execute_sql_on_system_db(sql)**：执行对 tb_data_source 的增删改查。
- **tool_test_data_source_setting(platform, host, port, username, password, database)**：创建前必须验证连接。
