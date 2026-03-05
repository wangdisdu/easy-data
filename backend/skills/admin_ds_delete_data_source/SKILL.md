---
name: admin-ds-delete-data-source
description: Deletes a data source by ID or code. Use when the user asks to delete a data source, remove a data source, or unregister a database connection.
---

# 删除数据源

## 职责

- 根据数据源 **ID** 或 **编码** 删除指定数据源；若该数据源下存在关联数据模型（tb_data_model.ds_id = 数据源ID），则**拒绝删除**并提示先处理关联模型。删除不可逆，且会同时删除关联的工作空间关系。

## 标识符说明（ds_id_or_code）

- **数据源标识符**：用户可提供 ID 或编码（code）。
  - 若为**数字字符串**（如 `"1"`），视为数据源 **ID**。
  - 否则视为数据源 **编码（code）**（如 `"mysql01"`、`"mysql_prod_192_168_1_100_users"`）。

## 使用场景

- 删除不再需要的数据源配置
- 清理无关联模型的数据源

## 执行方式

1. 根据用户给的 id 或 code，先查该数据源是否存在并得到其 **id**（用 tool_execute_system_sql 执行 `SELECT id FROM tb_data_source WHERE id = <id> OR code = '<code>'`，code 需正确转义）。不存在则直接提示「数据源不存在」。
2. 检查是否有关联模型：执行 `SELECT COUNT(*) AS cnt FROM tb_data_model WHERE ds_id = <ds_id>`。若 cnt > 0，则**拒绝删除**并提示「数据源下存在 X 个关联的数据模型，无法删除，请先删除关联模型」。
3. 若无关联模型，执行 `DELETE FROM tb_data_source WHERE id = <id>`，然后调用 **tool_execute_system_sql(sql)**。根据影响行数回复「数据源删除成功」或失败原因。

## 可用工具

- `tool_execute_system_sql`：在系统库执行单条 SQL
