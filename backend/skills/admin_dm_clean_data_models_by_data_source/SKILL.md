---
name: admin-dm-clean-data-models-by-data-source
description: Deletes all data models under a data source by ID or code. Irreversible; removes workspace relations. Use when the user asks to clear all models of a data source, delete all models under a data source, or re-import after cleanup.
---

# 删除/清空指定数据源下的所有数据模型

## 职责

- 按数据源 **ID** 或 **编码** 删除该数据源下的**全部**数据模型。仅删除系统库中的模型记录，不删用户库中的实际表/视图；删除时会同时删除关联的工作空间关系。**操作不可逆**，请确认后再执行。

## 标识符说明（ds_id_or_code）

- 若为**数字字符串**（如 `"1"`），视为数据源 **ID**；否则视为数据源 **编码（code）**（如 `"mysql01"`）。必须是已存在的数据源。

## 使用场景

- 清空数据源下的所有数据模型
- 重新导入数据源的数据模型前，先清空旧模型
- 清理数据源关联的所有数据模型

## 执行方式

1. 根据用户给的数据源 id 或 code，先得到 **ds_id**：执行 `SELECT id FROM tb_data_source WHERE id = <id> OR code = '<code>'`（tool_execute_system_sql）。无结果则提示数据源不存在。
2. 执行：`DELETE FROM tb_data_model WHERE ds_id = <ds_id>`，调用 **tool_execute_system_sql(sql)**。
3. 根据返回的影响行数回复用户（如「已删除数据源 X 下的 N 个数据模型」）。若该数据源下没有数据模型，影响行数为 0，可提示「数据源 X 下没有数据模型」。

## 可用工具

- `tool_execute_system_sql`：在系统库执行单条 SQL
