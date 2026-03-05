---
name: admin-ds-list-data-sources
description: Lists all configured data sources. Use when the user asks to list data sources, show all data sources, or query data source list.
---

# 列出所有数据源

## 职责

- 查询并展示系统中**所有已配置的数据源**列表。可用于查看已配置数据源、了解连接配置、查找编码/名称、检查数据源是否已存在、或查看语义说明等。

## 返回信息说明

- **数据源 ID**：系统内部唯一标识
- **编码（code）**：用户定义的唯一标识符
- **名称（name）**：数据源的显示名称
- **平台（platform）**：数据库类型（mysql、postgresql、sqlserver、oracle、clickhouse、doris、sqlite）
- **连接配置（setting）**：完整的连接配置 JSON 字符串，包含 host、port、username、password、database
- **语义说明（semantic）**、**外部知识（knowledge）**：若需在列表中展示可一并查询；若仅做简短列表可省略长文本以节省输出
- **创建时间（create_time）**、**更新时间（update_time）**：时间戳

## 执行方式

1. 生成 **SELECT** SQL 查询 `tb_data_source`，然后调用 **tool_execute_system_sql(sql)** 执行。
   - **简短列表**（适合列表展示）：只查 `id, code, name, platform, setting, create_time, update_time`，不查 semantic、knowledge 等长文本。
   - **完整列表**（需含语义/知识）：可查 `SELECT * FROM tb_data_source`。
2. 将工具返回的 JSON 结果整理后回复用户；若无数据源，可提示「当前系统内没有配置任何数据源。」

示例 SQL（简短列表）：

```sql
SELECT id, code, name, platform, setting, create_time, update_time
FROM tb_data_source
```

## 可用工具

- `tool_execute_system_sql`：在系统库执行单条 SQL
