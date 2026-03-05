---
name: admin-dm-analysis-data-model
description: Analyzes a single data model with exploratory SQL (structure, sample, count, time, numeric, dimension, dimension_top5, null_ratio), then generates a Markdown report; optionally saves semantic and summary to the model. Use when the user asks to analyze a table/model, generate semantic, or update model semantic/summary for one model.
---

# 数据分析（单模型）

## 职责范围

- ✅ 分析**指定单个**数据模型的数据（仅支持单个模型，不支持批量）
- ✅ 利用多个探索 SQL 分析数据模型中的数据特征、分布、统计信息等
- ✅ 总结数据模型中的数据信息、业务含义和数据用途，生成 Markdown 报告
- ✅ 若用户要求保存，将分析结果（semantic、summary）更新到数据库

## 非职责范围

- 导入数据模型、创建/删除数据模型、查询数据模型列表
- **批量处理多个数据模型**（仅支持单模型分析）

## 执行流程概览

1. **获取模型信息**：根据用户提供的模型 ID 或编码，用 `tool_execute_system_sql` 执行 `SELECT * FROM tb_data_model WHERE id = ? OR code = ?`，得到目标模型的 id、code、name、platform、ds_id 等；若无结果则提示模型不存在并结束。
2. **执行 8 个数据分析 SQL 任务**：按顺序调用 `tool_execute_sql_data_model(dm_id_or_code, sql)`，依次完成下方「八项分析任务」；每个任务的结果作为后续任务的上下文。
3. **生成报告**：汇总所有 SQL 结果，按「输出格式要求」生成 Markdown 格式的数据分析报告（字段说明 + 数据总结）。
4. **可选保存**：仅当用户明确要求保存/更新语义说明时，用 `tool_execute_system_sql` 执行 UPDATE tb_data_model SET semantic=?, summary=?, update_time=? WHERE id=?（或 WHERE code=?），将报告写入该模型。

## 可用工具

- `tool_execute_system_sql(sql)`：系统库执行 SQL，用于查询/更新 tb_data_model（获取模型信息、保存 semantic/summary）
- `tool_execute_sql_data_model(dm_id_or_code, sql)`：在用户数据源上执行分析 SQL，参数为数据模型标识符与生成的 SQL

---

## 八项分析任务（必须按顺序执行）

**重要**：根据数据源类型 `platform` 使用正确 SQL 语法：MySQL/PostgreSQL/SQLite/ClickHouse/Doris 用 `LIMIT`，SQL Server 用 `TOP`，Oracle 用 `ROWNUM`。表名从模型信息中的表名/编码取得，注意 schema 前缀（如 PostgreSQL 的 schema.table）。

### 任务1：structure - 获取表/视图结构

- **目标**：获取表的完整结构（字段名、数据类型、是否可空、主键、外键等）。
- **SQL 示例**：
  - MySQL/ClickHouse/Doris：`SHOW CREATE TABLE 表名`
  - PostgreSQL：`SELECT column_name, data_type, is_nullable, column_default, character_maximum_length FROM information_schema.columns WHERE table_name = '表名' ORDER BY ordinal_position`
  - SQL Server：`SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, CHARACTER_MAXIMUM_LENGTH FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '表名' ORDER BY ORDINAL_POSITION`
  - Oracle：`SELECT column_name, data_type, nullable, data_default, data_length FROM all_tab_columns WHERE table_name = UPPER('表名') ORDER BY column_id`
  - SQLite：`PRAGMA table_info(表名)`

### 任务2：sample - 获取样例数据

- **目标**：获取 3 行样例数据。
- **SQL**：MySQL/PostgreSQL/SQLite/ClickHouse/Doris 用 `SELECT * FROM 表名 LIMIT 3`；SQL Server 用 `SELECT TOP 3 * FROM 表名`；Oracle 用 `SELECT * FROM 表名 WHERE ROWNUM <= 3`。

### 任务3：count - 获取数据总量

- **目标**：总记录数，供后续占比计算。
- **SQL**：`SELECT COUNT(*) as total_count FROM 表名`（通用）。**重要**：total_count 用于任务 7、8 的占比计算。

### 任务4：time - 分析时间字段格式

- **目标**：从 structure 结果识别所有时间类型字段，取样例值并分析时间格式。
- **要求**：推荐用 UNION ALL 将各时间字段的查询合并为一条 SQL 执行。
- **示例**（MySQL/PostgreSQL/SQLite/ClickHouse/Doris，多时间字段 field1, field2, field3）：
```sql
SELECT * FROM (SELECT 'field1' as field_name, field1 as field_value FROM 表名 WHERE field1 IS NOT NULL LIMIT 10) AS t1
UNION ALL
SELECT * FROM (SELECT 'field2' as field_name, field2 as field_value FROM 表名 WHERE field2 IS NOT NULL LIMIT 10) AS t2
UNION ALL
SELECT * FROM (SELECT 'field3' as field_name, field3 as field_value FROM 表名 WHERE field3 IS NOT NULL LIMIT 10) AS t3
```
- SQL Server 用 `TOP 10`，Oracle 用 `ROWNUM <= 10`。

### 任务5：numeric - 数值字段统计

- **目标**：从 structure 识别数值类型字段（int、bigint、decimal、float、double、numeric 等），计算最小值、最大值、平均值。
- **排除**：主键、唯一索引、字段名含 id/guid/uuid/pk 等唯一标识的字段不参与统计。
- **要求**：用 UNION ALL 将符合条件的数值字段合并为一条 SQL。
- **示例**：`SELECT 'field2' as field_name, MIN(field2) as min_val, MAX(field2) as max_val, AVG(field2) as avg_val FROM 表名 WHERE field2 IS NOT NULL UNION ALL ...`

### 任务6：dimension - 识别维度字段

- **目标**：识别可能维度字段（非主键、非唯一、非数值、非时间、非 UUID、非描述/备注类），分析去重数量。
- **排除**：主键、唯一索引、数值类型、时间类型、字段名含 id/guid/uuid、description/desc/comment/note/remark/memo 等。
- **要求**：用 UNION ALL 合并为一条 SQL：`SELECT 'field1' as field_name, COUNT(DISTINCT field1) as distinct_count FROM 表名 WHERE field1 IS NOT NULL UNION ALL ...`

### 任务7：dimension_top5 - 维度字段 Top5 与占比

- **目标**：对任务6得到的维度字段，取 Top5 值及占比，用任务3的 total_count 计算占比。
- **要求**：用 UNION ALL 合并各维度字段的 SQL；MySQL/PostgreSQL/SQLite/ClickHouse/Doris 用 LIMIT 5，SQL Server 用 TOP 5，Oracle 用 ROWNUM <= 5。
- **示例**（MySQL 等）：子查询中 `GROUP BY field1 ORDER BY cnt DESC LIMIT 5`，占比为 `COUNT(*) * 100.0 / total_count`（total_count 需为标量或子查询可得）。

### 任务8：null_ratio - 可空字段 NULL 比率

- **目标**：从 structure 识别可空字段（is_nullable 为 true），计算 NULL 占比，用 total_count 计算。
- **要求**：用 UNION ALL 合并：`SELECT 'field1' as field_name, (COUNT(*) - COUNT(field1)) * 100.0 / total_count as null_percentage FROM 表名 UNION ALL ...`

---

## 执行顺序与依赖

1. **顺序**：structure → sample → count → time → numeric → dimension → dimension_top5 → null_ratio。
2. **依赖**：structure 用于识别字段类型（时间、数值、可空、维度等）；count 的 total_count 用于任务 7、8；dimension 的结果用于任务 7 的维度字段列表。
3. 对 time、numeric、dimension、dimension_top5、null_ratio，尽量用 UNION ALL 合并为单条 SQL 执行，减少调用次数。

---

## 输出格式要求（Markdown 报告）

**必须使用 Markdown，禁止 JSON。**

### 语义说明结构

```markdown
## {表名} - 字段说明

### {字段名1}
{字段类型，字段描述：含义、数据特征、数据分布等}

### {字段名2}
...

## {表名} - 数据总结
{表的数据特征、业务含义、数据用途等}
```

- **字段名**：必须从 structure 结果中准确提取，与库表一致。
- **字段描述**：结合 structure、sample、numeric、dimension、dimension_top5、null_ratio 等结果总结含义、数据特征与分布。
- **数据总结**：概括表的数据特征、业务含义和用途；报告总长建议在 4096 字符以内。

---

## 保存规则

- **需要保存时**：用户明确说「保存」「更新」「保存到数据库」「更新语义说明」等时，用 `tool_execute_system_sql` 执行 UPDATE tb_data_model SET semantic=?, summary=?, update_time=? WHERE id=?（或 WHERE code=?）。semantic 为完整 Markdown 报告（含字段说明+数据总结），summary 为仅「## 表名 - 数据总结」部分；注意长文本中的引号转义。
- **仅分析不保存**：用户只要求分析、未要求保存时，只返回 Markdown 报告，不执行 UPDATE。

---

## 用户表达示例

- 符合职责：「分析数据模型 1 的数据」「分析 public.users 表的数据分布」「分析 users 表并保存」「更新数据模型 1 的语义说明」「生成 public.users 的语义说明并保存」
- 不符合/需拒绝：「批量分析所有数据模型」「分析数据源 1 下所有模型」「同时分析多个模型」

若用户请求为批量或多模型，礼貌说明本能力仅支持单模型分析，请指定一个模型后再执行。
