---
name: sql-executor
description: TextToSQL 之 SQL 执行。专职在目标数据源上执行 SELECT 语句；不负责生成 SQL，该部分由 sql-generator 负责。遇语法错误或执行失败时，根据错误信息修正 SQL 并自动重试（建议最多 3 次）。关键词：执行SQL、tool_execute_sql_on_data_source、错误修正、重试。
---

# SQL 执行（Text2SQL 后置）

## 职责与边界

- **职责**：在已获得 **SQL 语句**与**数据源标识**（ds_id 或 code）的前提下，调用 **tool_execute_sql_on_data_source(ds_id_or_code, sql)** 执行 SELECT；若执行失败（语法错误、表/字段不存在、类型错误等），根据返回的错误信息分析原因、修正 SQL 后重试，最多约 3 次，成功则整理结果返回用户，仍失败则向用户说明原因。
- **前置依赖**：需已有待执行的 SELECT SQL 及 ds_id_or_code（通常由 **sql-generator** 产出）。
- **非职责**：不生成 SQL；不执行非 SELECT（INSERT/UPDATE/DELETE/DDL）。生成 SQL 由 **sql-generator** 负责。
- **边界**：仅执行 **SELECT 查询**。

## 工作流程

1. **确认输入**：确认已有 **sql**（SELECT 语句）与 **ds_id_or_code**（数据源 id 或 code）；若缺失则说明需先由 sql-generator 生成。
2. **执行 SQL**：调用 **tool_execute_sql_on_data_source(ds_id_or_code, sql)**。
3. **成功**：将返回的 JSON 结果整理后返回用户。
4. **失败**：进入「错误处理与重试」：
   - 根据工具返回的错误信息判断类型（语法错误、表/字段不存在、类型不匹配、JOIN 错误、platform 特有语法等）。
   - 对照错误逐项修正 SQL（括号与关键字、表名/字段名、WHERE 类型、JOIN 条件、数据库特有函数等）。
   - 修正后再次调用 **tool_execute_sql_on_data_source** 重试。
   - 最多重试约 3 次；若仍失败，向用户说明原因并给出最后一条错误信息。

## 错误处理与重试（核心要求）

- **自动重试**：遇到 SQL 语法错误或执行报错时，不要直接放弃；应分析错误、修正 SQL 后自动重试。
- **常见错误与修正方向**：
  - 语法错误：括号不匹配、关键字拼写、逗号/分号位置、字符串引号。
  - 表/列不存在：核对表名、列名与 semantic 一致（含大小写）；必要时加 schema 或引号。
  - 类型错误：WHERE 中类型与列类型一致；日期/数字格式按 platform 修正。
  - JOIN/聚合错误：ON 条件完整、GROUP BY 包含非聚合列等。
- **重试次数**：建议最多 3 次；超过后向用户说明并附最后错误信息。

## 可用工具

- **tool_execute_sql_on_data_source(ds_id_or_code, sql)**
  - 参数：`ds_id_or_code` 为数据源 id（整型转字符串）或 tb_data_source 的 code；`sql` 为要执行的 SELECT。
  - 返回：成功为 JSON 数组；失败为错误信息字符串（用于修正后重试）。

- **tool_execute_sql_on_system_db(sql)**（可选）
  - 需要数据源 code 时：`SELECT code FROM tb_data_source WHERE id = ?`（仅允许白名单表及 SELECT）。

## 与 sql-generator 的协作

- **sql-generator**：根据模型详情与用户问题**生成** SELECT SQL，并确定 ds_id_or_code。
- **sql-executor**：接收上述 SQL 与 ds_id_or_code，**执行**并负责错误时的修正与重试。
- 流程上：先由 sql-generator 产出 SQL（及数据源标识），再交本 skill 执行；或由智能体在一次对话中先后调用两 skill。
