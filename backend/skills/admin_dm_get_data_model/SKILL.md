---
name: admin-dm-get-data-model
description: Gets full details of a single data model by ID or code, including semantic, description, extend, create_time, update_time. Use when the user asks to view a model's details, get model info, or show full details of a specific table/view.
---

# 获取单个数据模型详情

## 职责

- 根据数据模型 **ID** 或 **编码** 获取该模型的**完整信息**，包括 id、code、name、platform、type、ds_id、semantic、description、extend、create_time、update_time 等，用于查看详情或验证模型是否存在。

## 标识符说明（dm_id_or_code）

- 若为**数字字符串**（如 `"1"`），视为数据模型 **ID**；否则视为数据模型 **编码（code）**（如 `"public.users"`）。

## 使用场景

- 根据 ID 或编码查找特定数据模型
- 获取数据模型的详细信息（含 ds_id、platform、type、semantic 等）
- 验证数据模型是否存在

## 执行方式

1. 根据用户提供的 id 或 code，生成 **SELECT** SQL，然后调用 **tool_execute_system_sql(sql)** 执行。
   - 若为数字 id：`SELECT * FROM tb_data_model WHERE id = <id>`
   - 若为编码：`SELECT * FROM tb_data_model WHERE code = '<code>'`（**code 需正确转义**，避免 SQL 注入）
2. 若返回为空则提示模型不存在；否则将单条结果整理后回复用户。

## 可用工具

- `tool_execute_system_sql`：在系统库执行单条 SQL
