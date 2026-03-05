---
name: admin-ds-update-data-source
description: Updates a data source by ID or code—name, connection config (setting), semantic, and external knowledge (knowledge). Use when the user asks to update data source settings, change semantic, or edit knowledge.
---

# 更新数据源

## 职责

- 根据数据源 **ID** 或 **编码** 更新已存在数据源的部分信息。可更新：显示名称（name）、连接配置（setting）、语义说明（semantic）、外部知识（knowledge）。**不能修改**数据源编码（code）、平台类型（platform）等核心标识。

## 标识符说明（ds_id_or_code）

- **数据源标识符**（必填）：若为**数字字符串**（如 `"1"`）视为数据源 **ID**，否则视为**编码（code）**（如 `"mysql01"`）。必须是已存在的数据源。

## 使用场景

- 修改数据源的显示名称
- 更新数据源的账号密码或完整连接配置（通过 setting）
- 修改数据源的语义说明（semantic）、外部知识（knowledge）

## 可更新字段说明

- **name**：数据源显示名称（人类可读）。
- **setting**：连接配置，为 **JSON 字符串**（不是对象）。内容通常包含 host、port、username、password、database。若只改账号密码，需先 SELECT 当前行的 setting，解析后修改 username/password 再序列化写回；写 SQL 时注意字符串内引号、反斜杠的转义。
- **semantic**：语义说明（长文本）。
- **knowledge**：外部知识（长文本）。
- **update_time**：必须设置更新时间，使用当前时间的时间戳，如1772640000000

**重要**：必须提供至少一个要更新的字段；更新 setting 时若只改密码，需保留原有 host、port、database 等，仅替换 username/password 后重新组成 JSON 字符串。

## 执行方式

1. 根据用户给的 id 或 code，确定目标记录（可先 `SELECT * FROM tb_data_source WHERE id = <id> OR code = '<code>'` 获取当前行；code 需转义）。
2. 根据用户要更新的内容，生成 **UPDATE** SQL，仅更新允许的列（name、setting、semantic、knowledge、update_time）。**update_time 使用 SQL 当前时间函数**（如 SQLite：`(strftime('%s','now') * 1000)`；MySQL：`(UNIX_TIMESTAMP() * 1000)`）。长字符串内的单引号需转义为两个单引号。
3. 调用 **tool_execute_system_sql(sql)** 执行，根据影响行数回复「数据源更新成功」或失败原因。

## 更新记录 SQL 示例

以下多个示例；字符串内单引号写为 `''`。

**仅更新名称（按 ID）**
```sql
UPDATE tb_data_source SET name = 'MySQL生产环境-新名称', update_time = 1772640000000 WHERE id = 1;
```

**仅更新名称（按 code）**
```sql
UPDATE tb_data_source SET name = 'MySQL生产环境-新名称', update_time = 1772640000000 WHERE code = 'mysql01';
```

**仅更新连接配置 setting（完整 JSON 字符串，如修改密码后）**
```sql
UPDATE tb_data_source SET setting = '{"host":"192.168.1.100","port":3306,"username":"root","password":"newpass","database":"mydb"}', update_time = 1772640000000 WHERE id = 1;
```

**仅更新语义说明 semantic（长文本需转义单引号）**
```sql
UPDATE tb_data_source SET semantic = '本数据源为生产环境MySQL，存储用户与订单数据。', update_time = 1772640000000 WHERE id = 1;
```

**仅更新外部知识 knowledge**
```sql
UPDATE tb_data_source SET knowledge = '连接前请确认 VPN 已开启。', update_time = 1772640000000 WHERE id = 1;
```

**同时更新名称与 setting**
```sql
UPDATE tb_data_source SET name = 'MySQL生产-新名称', setting = '{"host":"192.168.1.100","port":3306,"username":"root","password":"newpass","database":"mydb"}', update_time = 1772640000000 WHERE id = 1;
```

**同时更新 semantic 与 knowledge（内容中含单引号时写为 ''）**
```sql
UPDATE tb_data_source SET semantic = '生产MySQL库。', knowledge = '注意：仅内网可访问。', update_time = 1772640000000 WHERE id = 1;
```

## 可用工具

- `tool_execute_system_sql`：在系统库执行单条 SQL（UPDATE）
