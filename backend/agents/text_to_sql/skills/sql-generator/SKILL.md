---
name: sql-generator
description: TextToSQL 之 SQL 生成。专职根据已获取的数据模型详细信息（semantic、summary、knowledge、platform、ds_id 等）与用户自然语言问题，按 Text2SQL 原则生成 SELECT 语句；不执行 SQL，执行与错误重试由 sql-executor 负责。不负责获取模型列表或选模型，该部分由 data-information-exploration 负责。关键词：生成SQL、SELECT、Text2SQL、platform。
---

# SQL 生成（Text2SQL）

## 职责与边界

- **职责**：在已获得目标数据模型详细信息（由 **data-information-exploration** 或上游提供：id、name、platform、ds_id、semantic、summary、knowledge）的前提下，根据用户问题按 Text2SQL 原则**仅生成** **SELECT** SQL，并明确数据源标识 **ds_id_or_code**（供 **sql-executor** 执行使用）。
- **前置依赖**：需已有涉及模型的信息（至少含 platform、ds_id、semantic），否则无法生成。
- **非职责**：不执行 SQL；不根据执行错误修正 SQL 或重试。执行及错误重试由 **sql-executor** 负责。不生成非 SELECT（INSERT/UPDATE/DELETE）；不涉及 DDL 或管理操作。
- **边界**：仅**生成** **SELECT 查询**语句。

## 工作流程

1. **确认输入**：确认已有所需模型的 name、platform、ds_id、semantic、summary、knowledge（若缺失则说明需先由 data-information-exploration 获取）。
2. **生成 SQL**：以 semantic（及 summary、knowledge）为背景知识，结合用户问题，按下文「Text2SQL 原则」与「SQL 生成最佳实践」生成 SELECT；须根据模型的 **platform** 使用对应数据库语法。
3. **产出**：输出生成的 **SELECT** 语句及 **ds_id_or_code**（使用模型信息中的 ds_id 或对应数据源的 code）。将二者交给 **sql-executor** 执行；执行失败时的修正与重试由 sql-executor 负责。

---

## Text2SQL 原则

### 1. 准确性原则

- **表名和字段名必须准确**：严格使用背景知识（semantic）中的表名和字段名，区分大小写。  
- **数据类型匹配**：WHERE 条件中的数据类型与字段类型匹配。  
- **关联关系正确**：JOIN 条件与关联字段类型一致。  
- **按数据源类型生成 SQL**：必须根据模型的 **platform** 生成符合该数据库语法的 SQL。

### 2. 安全性原则

- **只生成 SELECT**：禁止任何数据修改或 DDL。  
- **避免 SQL 注入**：参数化或适当转义。  
- **权限**：不访问未授权数据。

### 3. 性能优化原则

- **使用索引字段**：优先主键、外键，避免全表扫描。  
- **合理 LIMIT**：可能返回大量结果时使用 LIMIT（或 TOP/ROWNUM，见下）。  
- **优先 JOIN**：尽量用 JOIN 替代子查询。  
- **CTE**：控制在 3 个以内，优先简单子查询或 JOIN。

### 4. 可读性原则

- **有意义别名**：表、字段使用清晰别名。  
- **格式化**：SQL 格式清晰；在关键字（SELECT、FROM、WHERE、JOIN、GROUP BY、ORDER BY、HAVING 等）处换行。

---

## SQL 生成最佳实践

### 1. 表名和字段名

- 支持 schema 时使用 `schema.table_name`。  
- 按数据库类型使用引号（MySQL 反引号，PostgreSQL 双引号）；注意大小写。

### 2. WHERE 条件

- 精确匹配用 `=`；模糊用 `LIKE`（通配符）；范围用 `BETWEEN` 或 `>=`/`<=`；NULL 用 `IS NULL`/`IS NOT NULL`；多条件用 `AND`/`OR` 与括号明确优先级。

### 3. JOIN

- INNER JOIN / LEFT JOIN / RIGHT JOIN 按需选用；关联条件正确，避免笛卡尔积。

### 4. 聚合

- COUNT（注意 COUNT(*) 与 COUNT(column)）、SUM/AVG/MAX/MIN；GROUP BY 包含所有非聚合字段；过滤聚合结果用 HAVING。

### 5. 排序和分页（按 platform）

- ORDER BY 有意义的字段；分页：MySQL/PostgreSQL/SQLite/ClickHouse/Doris 用 `LIMIT n`，SQL Server 用 `TOP n`，Oracle 用 `ROWNUM <= n`。

### 6. 子查询

- EXISTS/NOT EXISTS、IN/NOT IN；注意性能，尽量用 JOIN 替代。

### 7. 简洁性

- SQL 简洁易读；嵌套不超过 3 层；单条 SQL 不宜过长（如超过 200 行考虑拆分）。

---

## 常见问题处理

### 模糊查询

- 「包含」→ `LIKE '%keyword%'`；「开头是」→ `LIKE 'keyword%'`；「结尾是」→ `LIKE '%keyword'`；注意 LIKE 对性能的影响。

### 时间范围

- **日期格式（按库）**：MySQL `DATE('YYYY-MM-DD')`；PostgreSQL `'YYYY-MM-DD'::DATE`；SQL Server `CAST('YYYY-MM-DD' AS DATE)`；Oracle `TO_DATE('YYYY-MM-DD', 'YYYY-MM-DD')`；SQLite `DATE('YYYY-MM-DD')`；ClickHouse/Doris `toDate('YYYY-MM-DD')`。  
- 范围用 `>=`/`<` 或 `BETWEEN`；相对时间如 MySQL `DATE_SUB(CURDATE(), INTERVAL 7 DAY)`。

### 多表关联

- 从 semantic 识别外键/语义关联；按业务选 INNER/LEFT JOIN；必要时 DISTINCT 去重。

---

## 示例

**输入**：用户问题“查询最近 7 天的订单数量”，且已由 data-information-exploration 提供模型详情（表名 orders，日期字段 created_at，platform 为 MySQL，ds_id=1）。  

**产出**：  
- **SQL**：  
```sql
SELECT COUNT(*) AS order_count
FROM orders
WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
```  
- **ds_id_or_code**：`"1"`（或该数据源在 tb_data_source 中的 code）。  

将上述 SQL 与 ds_id_or_code 交给 **sql-executor** 执行；执行与错误重试由 sql-executor 负责。

---

## 可用工具（本 skill 仅生成，不执行）

- **tool_execute_sql_on_system_db(sql)**（可选）  
  - 需要数据源 code 时：`SELECT code FROM tb_data_source WHERE id = ?`（仅允许白名单表及 SELECT）。  

执行 SQL 使用 **tool_execute_sql_on_data_source** 由 **sql-executor** skill 负责。

---

## 边界情况

- 多模型/多数据源：按当前提供的模型信息为每组生成相应 SQL 及 ds_id_or_code，交 sql-executor 分别执行；若需跨源则需上游提供多组模型信息。
