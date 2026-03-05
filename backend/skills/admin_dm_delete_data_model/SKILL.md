---
name: admin-dm-delete-data-model
description: Deletes a single data model by ID or code. Irreversible; also removes workspace relations. Use when the user asks to delete a model, remove a table/view from data models, or drop a specific data model.
---

# 删除数据模型

## 职责

- 根据数据模型 **ID** 或 **编码** 删除指定的数据模型。**仅删除系统库中的模型记录**，不删用户库中的实际表/视图。删除时会同时删除关联的工作空间关系；**操作不可逆**，请谨慎使用。

## 标识符说明（dm_id_or_code）

- 若为**数字字符串**（如 `"1"`），视为数据模型 **ID**；否则视为数据模型 **编码（code）**（如 `"public.users"`）。必须是已存在的数据模型。

## 使用场景

- 删除不再需要的数据模型
- 清理错误导入的数据模型
- 删除关联的数据模型

## 执行方式

1. 根据用户给的 id 或 code，生成 **DELETE** SQL，然后调用 **tool_execute_system_sql(sql)** 执行。code 需正确转义。
2. 根据影响行数回复「数据模型删除成功」或失败原因（如模型不存在）。

## 删除记录 SQL 示例

**按 ID 删除**
```sql
DELETE FROM tb_data_model WHERE id = 1;
```

**按 code 删除**
```sql
DELETE FROM tb_data_model WHERE code = 'public.users';
```

**按 ID 删除（多个时逐条执行或使用 IN）**
```sql
DELETE FROM tb_data_model WHERE id IN (1, 2, 3);
```

**按 code 删除（单条，code 含单引号时转义为 ''）**
```sql
DELETE FROM tb_data_model WHERE code = 'schema1.my_table';
```

## 可用工具

- `tool_execute_system_sql`：在系统库执行单条 SQL
