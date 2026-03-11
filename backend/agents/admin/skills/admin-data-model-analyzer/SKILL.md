---
name: admin-data-model-analyzer
description: 数据模型数据分析助手。对单个数据模型执行 8 项探索 SQL（表结构、样例、总量、时间格式、数值统计、维度识别、维度 Top5 与占比、可空字段 NULL 比率），汇总结果生成 Markdown 报告。适用于用户要求分析某张表/某个模型的数据、做探索性分析或生成数据报告时。关键词：分析数据模型、分析表数据、单表、探索 SQL。
---

# 数据模型数据分析（单模型）

## 职责与边界

- **职责**：对**指定单个**数据模型执行 8 项探索 SQL，汇总结果生成 Markdown 报告（字段说明 + 数据总结）。
- **边界**：仅支持单模型；不支持批量、列表导入、创建/删除模型。批量或多模型请求时礼貌拒绝并说明仅支持单模型。
- **保存结果**：如果用户要求保存分析结果，请务必使用`admin-data-model-assistant`技能保存分析结果和总结信息到数据模型的semantic和字段summary，切勿使用文件保存。

## 执行步骤

1. **获取模型信息及已有参考**：用 tool_execute_sql_on_system_db 执行 `SELECT id, code, name, platform, ds_id, semantic, summary, knowledge FROM tb_data_model WHERE id = ? OR code = ?`，得到表名、platform、ds_id 等基础信息，以及**已有的 semantic、summary、knowledge** 作为数据分析前的参考信息（用于理解既有语义/摘要/外部知识，生成报告时可与之衔接或区分）；无结果则提示模型不存在并结束。
2. **执行 8 项分析 SQL**：按顺序调用 **tool_execute_sql_on_data_source(ds_id_or_code, sql)**，其中 **ds_id_or_code** 为数据源标识（即该模型所属数据源的 id 或 code，即 **tb_data_model.ds_id** 对应的数据源）。顺序为：structure → sample → count → time → numeric → dimension → dimension_top5 → null_ratio。每步结果作为下一步上下文。
3. **生成报告**：汇总所有 SQL 结果，结合步骤 1 获取的已有 semantic、summary、knowledge 参考信息，按下方「输出格式」生成 Markdown（字段说明 + 数据总结）；可参考既有描述保持衔接或注明与本次分析结论的差异。

## 执行流程要求

- **必须按顺序执行 8 个任务**：structure → sample → count → time → numeric → dimension → dimension_top5 → null_ratio。
- **上下文依赖**：structure 结果用于识别字段类型（时间、数值、可空等）；count 的 total_count 用于任务 7、8 的占比计算；dimension 结果用于确定哪些字段需要分析 Top5。
- **time、numeric、dimension、dimension_top5、null_ratio** 必须用 **UNION ALL** 将多字段合并为**一条 SQL** 执行，不要按字段多次调用。
- **按数据源类型使用正确语法**：MySQL/PostgreSQL/SQLite/ClickHouse/Doris 用 `LIMIT`；SQL Server 用 `TOP`；Oracle 用 `ROWNUM`。表名从模型 code/name 取，注意 schema。

---

## 任务 1：structure — 获取表/视图结构信息

**目标**：获取表的完整结构信息，包括字段名、数据类型、是否可空、主键、外键等。

**SQL 语法（按数据源 platform 选择）**：

- **MySQL/ClickHouse/Doris**：`SHOW CREATE TABLE 表名`
- **PostgreSQL**：`SELECT column_name, data_type, is_nullable, column_default, character_maximum_length FROM information_schema.columns WHERE table_name = '表名' ORDER BY ordinal_position`
- **SQL Server**：`SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, CHARACTER_MAXIMUM_LENGTH FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '表名' ORDER BY ORDINAL_POSITION`
- **Oracle**：`SELECT column_name, data_type, nullable, data_default, data_length FROM all_tab_columns WHERE table_name = UPPER('表名') ORDER BY column_id`
- **SQLite**：`PRAGMA table_info(表名)`

**执行要求**：生成并执行 SQL，获取表结构信息；后续任务依赖此结果识别字段类型与可空性。

---

## 任务 2：sample — 获取样例数据

**目标**：获取 3 行样例数据，了解表的数据内容和格式。

**SQL 语法（按 platform 选择）**：

- **MySQL/PostgreSQL/SQLite/ClickHouse/Doris**：`SELECT * FROM 表名 LIMIT 3`
- **SQL Server**：`SELECT TOP 3 * FROM 表名`
- **Oracle**：`SELECT * FROM 表名 WHERE ROWNUM <= 3`

**执行要求**：生成并执行 SQL，获取 3 行样例数据。

---

## 任务 3：count — 获取数据总量

**目标**：获取表的总记录数，供后续占比计算使用。

**SQL 语法（通用）**：`SELECT COUNT(*) AS total_count FROM 表名`

**执行要求**：执行后得到 total_count；**重要**：该值用于任务 7（dimension_top5）和任务 8（null_ratio）的占比计算。

---

## 任务 4：time — 分析时间字段格式

**目标**：识别所有时间类型字段（datetime、timestamp、date、time 等），取样例值并分析时间格式。

**要求**：**推荐使用 UNION ALL 将所有时间字段合并为一条 SQL 执行**，避免按字段多次执行。

**SQL 示例（多个时间字段 field1, field2, field3）**：

- **MySQL/PostgreSQL/SQLite/ClickHouse/Doris**：
```sql
SELECT * FROM (SELECT 'field1' AS field_name, field1 AS field_value FROM 表名 WHERE field1 IS NOT NULL LIMIT 10) AS t1
UNION ALL
SELECT * FROM (SELECT 'field2' AS field_name, field2 AS field_value FROM 表名 WHERE field2 IS NOT NULL LIMIT 10) AS t2
UNION ALL
SELECT * FROM (SELECT 'field3' AS field_name, field3 AS field_value FROM 表名 WHERE field3 IS NOT NULL LIMIT 10) AS t3
```
- **SQL Server**：子查询内用 `SELECT TOP 10 ...`。
- **Oracle**：子查询内用 `WHERE ... AND ROWNUM <= 10`。

**执行要求**：1）从 structure 结果识别所有时间类型字段；2）用 UNION ALL 合并为一条 SQL；3）分析时间格式（如 YYYY-MM-DD HH:MM:SS）。

---

## 任务 5：numeric — 分析数值字段统计信息

**目标**：识别数值类型字段（int、bigint、decimal、float、double、numeric 等），求最小值、最大值、平均值。

**重要**：  
1）**必须用 UNION ALL 将所有数值字段合并为一条 SQL 执行**。  
2）**必须排除具有唯一特性的数值字段**（不计算统计意义）：主键、唯一索引、字段名包含 id/guid/uuid/pk 等唯一标识关键词的字段（不区分大小写，可结合样例数据判断）。

**排除规则**：从 structure 中排除 — 主键（is_primary_key 为 true）、唯一索引（is_unique 为 true）、字段名含 id/guid/uuid/pk 等的字段。

**SQL 示例（数值字段 field2, field3，field1 为主键已排除）**：

```sql
SELECT 'field2' AS field_name, MIN(field2) AS min_val, MAX(field2) AS max_val, AVG(field2) AS avg_val FROM 表名 WHERE field2 IS NOT NULL
UNION ALL
SELECT 'field3' AS field_name, MIN(field3) AS min_val, MAX(field3) AS max_val, AVG(field3) AS avg_val FROM 表名 WHERE field3 IS NOT NULL
```

**执行要求**：从 structure 识别数值类型 → 排除唯一特性字段 → 用 UNION ALL 合并执行，得到 min/max/avg。

---

## 任务 6：dimension — 识别维度字段

**目标**：识别可能的维度字段（非主键、非数值、非唯一、非外键、非 UUID 等），分析去重数量。

**重要**：**必须用 UNION ALL 将所有维度字段合并为一条 SQL 执行**；排除主键、唯一索引字段。

**排除规则**：从 structure 中**必须排除** — 主键、唯一索引、数值类型、UUID/GUID 类（字段名含 id/guid/uuid）、**时间类型**（datetime/timestamp/date/time）、**描述/备注类**（字段名含 description/desc/comment/note/remark/memo 等）。

**SQL 示例（维度字段 field1, field2, field3）**：

```sql
SELECT 'field1' AS field_name, COUNT(DISTINCT field1) AS distinct_count FROM 表名 WHERE field1 IS NOT NULL
UNION ALL
SELECT 'field2' AS field_name, COUNT(DISTINCT field2) AS distinct_count FROM 表名 WHERE field2 IS NOT NULL
UNION ALL
SELECT 'field3' AS field_name, COUNT(DISTINCT field3) AS distinct_count FROM 表名 WHERE field3 IS NOT NULL
```

**执行要求**：从 structure 识别候选维度字段（排除上述类型）→ UNION ALL 合并 → 若去重数量较少（如 &lt; 总数据量 10%）则可能是维度字段；结果供任务 7 使用。

---

## 任务 7：dimension_top5 — 分析维度字段 Top5 值与占比

**目标**：对任务 6 识别出的维度字段，各取 Top5 值及占比；占比分母使用任务 3 的 total_count。

**重要**：**必须用 UNION ALL 将所有维度字段合并为一条 SQL 执行**。

**说明**：以下 SQL 中的 `total_count` 须替换为任务 3 查询得到的实际数值。

**SQL 示例（维度字段 field1, field2, field3）**：

- **MySQL/PostgreSQL/SQLite/ClickHouse/Doris**（子查询内 ORDER BY ... LIMIT 5）：
```sql
SELECT * FROM (SELECT 'field1' AS field_name, field1 AS field_value, COUNT(*) AS cnt, COUNT(*) * 100.0 / total_count AS percentage FROM 表名 WHERE field1 IS NOT NULL GROUP BY field1 ORDER BY cnt DESC LIMIT 5) AS t1
UNION ALL
SELECT * FROM (SELECT 'field2' AS field_name, ... LIMIT 5) AS t2
UNION ALL
SELECT * FROM (SELECT 'field3' AS field_name, ... LIMIT 5) AS t3
```
- **SQL Server**：子查询内用 `SELECT TOP 5 ... ORDER BY cnt DESC`。
- **Oracle**：子查询外包装 `WHERE ROWNUM <= 5` 或等效写法。

**执行要求**：从 dimension 结果取维度字段列表 → 用 total_count 计算占比 → UNION ALL 合并执行，得到各字段 Top5 及 percentage。

---

## 任务 8：null_ratio — 分析可空字段 NULL 比率

**目标**：识别所有可空字段（structure 中 is_nullable 为 true），计算 NULL 占比；分母使用 total_count。

**重要**：**必须用 UNION ALL 将所有可空字段合并为一条 SQL 执行**。

**说明**：SQL 中的 `total_count` 须替换为任务 3 得到的实际数值。

**SQL 示例（可空字段 field1, field2, field3）**：

```sql
SELECT 'field1' AS field_name, (COUNT(*) - COUNT(field1)) * 100.0 / total_count AS null_ratio FROM 表名
UNION ALL
SELECT 'field2' AS field_name, (COUNT(*) - COUNT(field2)) * 100.0 / total_count AS null_ratio FROM 表名
UNION ALL
SELECT 'field3' AS field_name, (COUNT(*) - COUNT(field3)) * 100.0 / total_count AS null_ratio FROM 表名
```

**执行要求**：从 structure 识别可空字段 → 用 total_count 计算 NULL 占比 → UNION ALL 合并执行。

---

## 任务 9：report — 生成报告和摘要

- 汇总所有SQL执行结果（包括表结构、样例数据、统计信息等）
- 分析这些数据，根据数据特征推理每个字段的业务含义，总结表的业务含义、数据用途等
- 生成Markdown格式的数据分析报告，包含字段信息和数据总结
- 生成数据模型的摘要信息，纯文本格式，摘要需要包括下面的信息：
  - 业务含义：表里存储了什么业务数据
  - 数据用途：可以用于解决什么问题
- **如果用户有要求保存**，请使用技能`admin-data-model-assistant`保存：
  - 报告完整内容保存到 tb_data_model 数据模型表的`semantic`字段
  - 摘要信息保存到 tb_data_model 数据模型表的`summary`字段

## 报告输出格式（Markdown）

**必须使用 Markdown**，禁止 JSON。严格按以下结构生成报告：

```
## {表名} - 字段说明

### {字段名1}

{字段类型，字段描述总结，包括：字段含义、数据特征、数据分布等}

### {字段名2}

{字段类型，字段描述总结，包括：字段含义、数据特征、数据分布等}

...

## {表名} - 数据总结

{表/视图里数据的总结，包括数据特征、业务含义、数据用途等}
```

- 字段名须与 structure 结果一致；每个 `### {字段名}` 下为一段描述，含字段类型及含义、数据特征、数据分布等。
- 报告长度建议 ≤4096 字符。

## 边界情况

- 无时间字段：任务 4 可跳过或返回空。
- 无数值/维度字段：任务 5、6、7 相应跳过或返回空。
- 表为空：count 为 0，占比类任务注意除零；仍可输出 structure 与报告框架。

## 可用工具

- **tool_execute_sql_on_system_db(sql)**：使用 sql 查询 tb_data_model 数据模型表。
- **tool_execute_sql_on_data_source(ds_id_or_code, sql)**：在指定数据源上执行上述 8 项分析 SQL。**ds_id_or_code** 为数据源 id 或 code（即该模型表 **tb_data_model.ds_id** 字段对应的数据源标识）。
