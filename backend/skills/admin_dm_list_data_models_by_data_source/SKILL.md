---
name: admin-dm-list-data-models-by-data-source
description: Lists data models under a data source by ID or code (simplified info: id, code, name, has_semantic, has_summary). Use when the user asks to list models under a data source, view models of a data source, or check semantic/summary coverage.
---

# 列出指定数据源下的所有数据模型

## 职责

- 按数据源 **ID** 或 **编码** 查询该数据源下的所有数据模型，返回**简化信息**（不含完整 semantic 等长文本），便于列表展示与检查是否已生成语义/摘要。

## 标识符说明（ds_id_or_code）

- 若为**数字字符串**（如 `"1"`），视为数据源 **ID**；否则视为数据源 **编码（code）**（如 `"mysql01"`）。

## 返回信息说明

- **id**：数据模型 ID
- **code**：数据模型编码
- **name**：数据模型名称
- **has_semantic**：是否已有语义说明（semantic 不为空）
- **has_summary**：是否已有摘要说明（summary 不为空）

（可选一并查询 platform、type、ds_id 等，便于展示。）

## 使用场景

- 查看数据源下有哪些数据模型
- 检查数据模型的语义说明和总结说明是否已生成
- 批量查看数据模型的基本信息

## 执行方式

1. 根据用户给的数据源 id 或 code，先得到 **ds_id**：执行 `SELECT id FROM tb_data_source WHERE id = <id> OR code = '<code>'`（tool_execute_system_sql）。无结果则提示数据源不存在。
2. 执行查询：`SELECT id, code, name, platform, type, ds_id, CASE WHEN semantic IS NOT NULL AND semantic != '' THEN 1 ELSE 0 END AS has_semantic, CASE WHEN summary IS NOT NULL AND summary != '' THEN 1 ELSE 0 END AS has_summary FROM tb_data_model WHERE ds_id = <ds_id>`。调用 **tool_execute_system_sql(sql)**。
3. 将返回的 JSON 整理后回复用户。若数据源下没有数据模型，返回空数组 []。如需某条模型的完整详情，可引导用户使用「获取单个数据模型详情」。

## 可用工具

- `tool_execute_system_sql`：在系统库执行单条 SQL
