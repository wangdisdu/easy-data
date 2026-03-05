---
name: admin-ds-check-data-source-health
description: Checks data source health by ID or code—connection reachability and whether it has data models. Use when the user asks to check data source health, verify a data source, audit connection or model presence.
---

# 检查数据源健康

## 职责

- 对系统中已配置的**指定数据源**（按 **ID** 或 **编码**）做健康检查，包括：
  1. **连接是否可用**：该数据源对应的用户数据库是否可连通、可用
  2. **是否有关联数据模型**：该数据源下是否已导入表/视图（是否有数据模型记录）

## 标识符说明（ds_id_or_code）

- 若为**数字字符串**（如 `"1"`），视为数据源 **ID**；否则视为数据源 **编码（code）**（如 `"mysql01"`）。

## 执行方式

1. **检查连接**：调用保留工具 **tool_check_data_source_connection**(ds_id_or_code)。该工具会从系统库读取数据源配置并尝试连接用户库，返回连接是否成功及失败原因。将结果告知用户。
2. **检查是否有关联数据模型**：
   - 若用户给的是**编码**，先执行 `SELECT id FROM tb_data_source WHERE code = '<code>'`（tool_execute_system_sql）得到 ds_id；若给的是数字 id，则 ds_id 即该 id。
   - 执行 `SELECT COUNT(*) AS cnt FROM tb_data_model WHERE ds_id = <ds_id>`，调用 **tool_execute_system_sql(sql)**。
   - 根据 cnt 回复：有/无数据模型，或数量。
3. 可将连接检查与模型数量检查结果合并为一段健康检查结论回复用户。

## 可用工具

- `tool_check_data_source_connection`：检查指定数据源连接是否可用（保留工具，会连接用户数据库）
- `tool_execute_system_sql`：在系统库执行单条 SQL（查询 tb_data_source、tb_data_model）
