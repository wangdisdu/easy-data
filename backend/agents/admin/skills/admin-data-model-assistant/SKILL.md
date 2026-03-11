---
name: admin-data-model-assistant
description: 数据模型管理助手。支持查询数据模型、创建数据模型、更新数据模型信息、删除数据模型以及从数据源导入表与视图；数据模型用于存储来自各数据源的表与视图的元数据（编码、名称、类型、所属数据源、语义说明、摘要等）。适用于用户要列出/查看/修改/删除数据模型、按数据源查看模型列表或从数据源导入表与视图
---

# 数据模型管理

## 能力

通过 SQL 操作表 **tb_data_model** 实现数据模型的**增、删、改、查**。执行 SQL 使用 **tool_execute_sql_on_system_db**。**批量从数据源导入**表/视图时，使用 **tool_import_data_models_by_data_source(ds_id_or_code)**，不手写批量 INSERT。

## 表 tb_data_model 字段

| 字段 | 类型 | 说明                                            |
|------|------|-----------------------------------------------|
| id | 主键 | 自增                                            |
| code | 字符串，唯一 | 如 public.users、database.table                 |
| name | 字符串 | 一般为表名或视图名                                     |
| platform | 字符串 | 同数据源类型                                        |
| type | 字符串 | table 或 view                                  |
| ds_id | 整型 | 所属数据源 ID，关联 tb_data_source.id                 |
| semantic | 长文本 | 语义说明（列表时勿 SELECT），数据模型字段级别的类型、业务含义、数据特征、数据分布等 |
| summary | 长文本 | 摘要说明（列表时勿 SELECT），数据模型的业务含义                     |
| knowledge | 长文本 | 外部知识                                          |
| description | 长文本 | 描述                                            |
| extend | 长文本 | 扩展                                            |
| create_time | 长整型 | 创建时间毫秒时间戳                                     |
| update_time | 长整型 | 更新时间毫秒时间戳                                     |

**查询约定**：查询多个数据模型（列表）时**不要 SELECT semantic、summary**；只查单条详情时可包含。列表建议查：id, code, name, platform, type, ds_id, create_time, update_time，或加 has_semantic/has_summary 标记。

---

## 步骤说明

### 1. 查询数据模型

- 按数据源列出：先 `SELECT id FROM tb_data_source WHERE id = <id> OR code = '<code>'` 得 ds_id，再 `SELECT id, code, name, platform, type, ds_id, ... FROM tb_data_model WHERE ds_id = <ds_id>`。
- 按 ID/code 查单条：`SELECT * FROM tb_data_model WHERE id = <id>` 或 `WHERE code = 'public.users'`（code 需转义）。

**示例**
```sql
SELECT id, code, name, platform, type, ds_id, create_time, update_time
FROM tb_data_model WHERE ds_id = 3;
```

### 2. 创建数据模型

- **常规**：批量导入时调用 **tool_import_data_models_by_data_source(ds_id_or_code)**，由工具连接用户库并写入，无需手写 INSERT。
- **手写 INSERT**（单条）：必填 code, name, platform, type, ds_id, create_time, update_time。code 唯一；时间用 `(strftime('%s','now') * 1000)`。插入前检查 code 是否已存在。

**示例**
```sql
INSERT INTO tb_data_model (code, name, platform, type, ds_id, create_time, update_time)
VALUES ('public.users', 'users', 'postgresql', 'table', 1, (strftime('%s','now') * 1000), (strftime('%s','now') * 1000));
```

### 3. 删除数据模型

- **单条**：先确认存在，再 `DELETE FROM tb_data_model WHERE id = <id>` 或 `WHERE code = '<code>'`。会影响工作空间关系，不可逆。
- **按数据源清空**：先得到 ds_id，再 `DELETE FROM tb_data_model WHERE ds_id = <ds_id>`。
- **边界**：数据源不存在时先提示；清空前可先查 `COUNT(*)` 告知将删除条数。

### 4. 更新数据模型

- 可更新：name, semantic, summary, knowledge, description, extend, update_time（不可改 code、platform、type、ds_id）。长文本单引号转义为 `''`；update_time 用当前时间函数。
- 示例：`UPDATE tb_data_model SET summary = '## users - 数据总结', update_time = (strftime('%s','now') * 1000) WHERE id = 1;`

---

## 可用工具

- **tool_execute_sql_on_system_db(sql)**：对 tb_data_model 的增删改查。
- **tool_import_data_models_by_data_source(ds_id_or_code)**：从数据源批量导入表/视图为数据模型，创建时优先使用。
