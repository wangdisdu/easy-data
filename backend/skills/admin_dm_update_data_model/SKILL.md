---
name: admin-dm-update-data-model
description: Updates a data model by ID or code—semantic, summary, knowledge, and update_time. Use when the user asks to update model semantic, summary, or knowledge.
---

# 更新数据模型

## 职责

- 根据数据模型 **ID** 或 **编码** 更新已存在数据模型的部分信息。可更新：语义说明（semantic）、摘要说明（summary）、外部知识（knowledge）、update_time。语义说明通常为结构化信息（如 JSON），摘要说明建议为 Markdown 格式的字段说明与数据总结。

## 标识符说明（dm_id_or_code）

- 若为**数字字符串**（如 `"1"`），视为数据模型 **ID**；否则视为数据模型 **编码（code）**（如 `"public.users"`）。

## 使用场景

- 生成数据模型语义说明后，同时更新 semantic 与 summary
- 修改单个模型的 semantic、summary 或 knowledge

## 可更新字段说明

- **semantic**：语义说明，通常为 JSON 或结构化文本，便于后续解析与使用。
- **summary**：摘要说明，建议 **Markdown 格式**，包含字段说明和数据总结。
- **knowledge**：外部知识（长文本）。
- **update_time**：必须设置更新时间，使用当前时间的时间戳，如1772640000000

## 执行方式

1. 根据用户要更新的内容和目标模型 id/code，生成 **UPDATE** SQL，仅更新允许的列（semantic、summary、knowledge、update_time）。长字符串内单引号需转义为两个单引号。
2. 调用 **tool_execute_system_sql(sql)** 执行，根据影响行数回复用户。

## 更新记录 SQL 示例

**仅更新 semantic（按 ID）**
```sql
UPDATE tb_data_model SET semantic = '{"type":"table","fields":[]}', update_time = 1772640000000 WHERE id = 1;
```

**仅更新 semantic（按 code）**
```sql
UPDATE tb_data_model SET semantic = '{"type":"table","fields":[]}', update_time = 1772640000000 WHERE code = 'public.users';
```

**仅更新 summary**
```sql
UPDATE tb_data_model SET summary = '## users - 数据总结\n用户表，存储账号与基本信息。', update_time = 1772640000000 WHERE id = 1;
```

**仅更新 knowledge**
```sql
UPDATE tb_data_model SET knowledge = '该表与 orders 通过 user_id 关联。', update_time = 1772640000000 WHERE id = 1;
```

**同时更新 semantic 与 summary**
```sql
UPDATE tb_data_model SET semantic = '{"type":"table"}', summary = '## users - 数据总结\n用户表。', update_time = 1772640000000 WHERE id = 1;
```

**同时更新 semantic、summary、knowledge**
```sql
UPDATE tb_data_model SET semantic = '{"type":"table"}', summary = '## users - 数据总结\n用户表。', knowledge = '与 orders 关联。', update_time = 1772640000000 WHERE code = 'public.users';
```

## 可用工具

- `tool_execute_system_sql`：在系统库执行单条 SQL（UPDATE）
