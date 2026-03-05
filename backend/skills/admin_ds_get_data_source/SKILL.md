---
name: admin-ds-get-data-source
description: Gets full details of a single data source by ID or code, including semantic and knowledge. Use when the user asks for details of a data source, get data source by id/code, or view one data source info.
---

# 获取单个数据源详情

## 职责

- 根据数据源 **ID** 或 **编码（code）** 获取该数据源的完整信息，包括：id、code、name、platform、setting（连接配置）、语义说明（semantic）、外部知识（knowledge）等。获取正确的 **code** 很重要，后续执行 SQL 等操作常需使用数据源 code。

## 标识符说明（ds_id_or_code）

- **数据源标识符**（必填）：
  - 若为**数字字符串**（如 `"1"`），视为数据源 **ID**。
  - 否则视为数据源 **编码（code）**（如 `"mysql01"`、`"mysql_prod_192_168_1_100_users"`）。

## 使用场景

- 从数据模型中拿到 ds_id 后，需要查对应数据源的 code 或完整信息
- 验证数据源是否存在
- 获取数据源的基本信息（code、platform、setting、semantic、knowledge 等）

## 执行方式

1. 根据用户提供的 id 或 code，生成一条 **SELECT** SQL，然后调用 **tool_execute_system_sql(sql)** 执行。
   - 若用户给的是数字 id：`SELECT * FROM tb_data_source WHERE id = <id>`
   - 若用户给的是编码：`SELECT * FROM tb_data_source WHERE code = '<code>'`（**code 需正确转义**，避免 SQL 注入）
2. 若返回为空，说明数据源不存在，回复用户；否则将单条结果（含 id、code、name、platform、setting、semantic、knowledge 等）整理后回复。

## 可用工具

- `tool_execute_system_sql`：在系统库执行单条 SQL
