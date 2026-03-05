---
name: admin-dm-check-data-model-health
description: Checks whether data models under a data source have semantic and summary. For data model health checks. Use when the user asks if models have semantic/summary, whether descriptions are filled, or to audit semantic coverage.
---

# 检查数据模型是否有语义说明和摘要说明

## 职责

- 检查指定数据源下的数据模型是否已填写语义说明(semantic)和摘要说明(summary)，用于**健康检查**

## 执行方式

1. 根据用户给的数据源 id 或 code，先得到 **ds_id**：执行 `SELECT id FROM tb_data_source WHERE id = <id> OR code = '<code>'`（tool_execute_system_sql）。无结果则提示数据源不存在。
2. 执行查询：`SELECT id, code, CASE WHEN semantic IS NOT NULL AND semantic != '' THEN 1 ELSE 0 END AS has_semantic, CASE WHEN summary IS NOT NULL AND summary != '' THEN 1 ELSE 0 END AS has_summary FROM tb_data_model WHERE ds_id = <ds_id>`，调用 **tool_execute_system_sql(sql)**。
3. 根据返回结果汇总：哪些模型已有 semantic/summary、哪些缺失，并回复用户。

## 可用工具

- `tool_execute_system_sql`：在系统库执行单条 SQL
