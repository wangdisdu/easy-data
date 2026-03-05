---
name: admin-ds-create-data-source
description: Creates a new data source with code, name, platform, and connection config (setting). Use when the user asks to add a data source, create a data source, or register a new database connection.
---

# 新增数据源

## 职责

- 创建新的数据源：编码(code)、名称(name)、数据库类型(platform)、连接配置(setting)、创建时间(create_time)与更新时间(update_time)

## 字段说明

### code（数据源编码）

- **唯一标识符**，表中必须唯一，不能与已有数据源重复。
- 格式要求：**只能包含小写字母、数字和下划线**，不能包含空格和特殊字符。
- 生成建议：可使用格式 `{platform}{序号}` 或 `{platform}_{环境}_{库名}`，例如 `mysql01`、`postgresql_local_dev`、`sqlite_chinook`。

### name（数据源显示名称）

- **人类可读的描述性名称**，用于界面展示，可以是中文、英文或混合。
- 建议命名规则：**{平台类型} {环境/位置} - {数据库名}**。
- 示例："MySQL生产环境-测试数据库"、"PostgreSQL本地开发库"、"SQL Server销售数据库（192.168.1.100）"、"SQLite - Chinook数据库"。

### setting（连接配置）

- **必须是 JSON 字符串**：入库时 `setting` 存的是**序列化后的 JSON 字符串**，不是 JSON 对象。构造 INSERT 时需将连接配置用 `json.dumps` 或等价方式转成字符串；字符串内的双引号、反斜杠等需正确转义（在 SQL 中单引号需转义为两个单引号）。
- 结构固定为包含以下键的对象序列化结果：`host`, `port`, `username`, `password`, `database`。
- **按数据源类型的说明**：
  - **MySQL**：常用端口 3306。
  - **PostgreSQL**：常用端口 5432。
  - **SQL Server**：常用端口 1433。
  - **Oracle**：常用端口 1521。
  - **ClickHouse**：常用端口 9000。
  - **Doris**：常用端口 9030。
  - **SQLite**：无需网络连接，`host`/`username`/`password` 传空字符串 `""`，`port` 传 `0`；`database` 为库文件路径（相对 backend/local_sqlite 的如 `chinook.sqlite`，或绝对路径）。

### create_time（创建时间）

必须设置创建时间，使用当前时间的时间戳，如1772640000000

### update_time（更新时间）

必须设置更新时间，使用当前时间的时间戳，如1772640000000。

## 执行方式

1. **建议先测试连接**：若用户提供了连接参数，先调用保留工具 **tool_test_data_source_setting**(platform, host, port, username, password, database) 测试是否可连；失败则直接返回错误，不创建。
2. **检查是否已存在**：生成并执行 `SELECT id FROM tb_data_source WHERE code = '<code>'`（调用 tool_execute_system_sql）。若有结果则提示已存在，不重复创建。
3. **插入新记录**：生成 **INSERT** SQL 插入 `tb_data_source`，必填字段包括：code, name, platform, setting, create_time, update_time。其中 **setting 为 JSON 字符串**；**create_time、update_time 使用 SQL 当前时间函数**得到毫秒时间戳（见下方示例）。然后调用 **tool_execute_system_sql(sql)** 执行。
4. 插入成功后从结果或后续查询中取得新数据源 id，回复用户。

## 插入新记录 SQL 示例（按数据源类型）

以下是不同数据源类型的示例

**MySQL**
```sql
INSERT INTO tb_data_source (code, name, platform, setting, create_time, update_time)
VALUES ('mysql01', 'MySQL生产环境-用户库', 'mysql', '{"host":"192.168.1.100","port":3306,"username":"root","password":"xxx","database":"mydb"}', 1772640000000, 1772640000000);
```

**PostgreSQL**
```sql
INSERT INTO tb_data_source (code, name, platform, setting, create_time, update_time)
VALUES ('postgresql01', 'PostgreSQL本地开发库', 'postgresql', '{"host":"localhost","port":5432,"username":"postgres","password":"xxx","database":"devdb"}', 1772640000000, 1772640000000);
```

**SQL Server**
```sql
INSERT INTO tb_data_source (code, name, platform, setting, create_time, update_time)
VALUES ('sqlserver01', 'SQL Server销售库', 'sqlserver', '{"host":"192.168.1.101","port":1433,"username":"sa","password":"xxx","database":"sales"}', 1772640000000, 1772640000000);
```

**Oracle**
```sql
INSERT INTO tb_data_source (code, name, platform, setting, create_time, update_time)
VALUES ('oracle01', 'Oracle业务库', 'oracle', '{"host":"192.168.1.102","port":1521,"username":"system","password":"xxx","database":"orcl"}', 1772640000000, 1772640000000);
```

**ClickHouse**
```sql
INSERT INTO tb_data_source (code, name, platform, setting, create_time, update_time)
VALUES ('clickhouse01', 'ClickHouse分析库', 'clickhouse', '{"host":"localhost","port":9000,"username":"default","password":"xxx","database":"analytics"}', 1772640000000, 1772640000000);
```

**Doris**
```sql
INSERT INTO tb_data_source (code, name, platform, setting, create_time, update_time)
VALUES ('doris01', 'Doris数仓', 'doris', '{"host":"192.168.1.103","port":9030,"username":"root","password":"xxx","database":"warehouse"}', 1772640000000, 1772640000000);
```

**SQLite**
```sql
INSERT INTO tb_data_source (code, name, platform, setting, create_time, update_time)
VALUES ('sqlite_chinook', 'SQLite - Chinook数据库', 'sqlite', '{"host":"","port":0,"username":"","password":"","database":"chinook.sqlite"}', 1772640000000, 1772640000000);
```

## 可用工具

- `tool_execute_system_sql`：在系统库执行单条 SQL（INSERT 需包含必填字段）
- `tool_test_data_source_setting`：测试连接参数（保留工具，连接用户数据库）
