---
name: admin-data-source-analyzer
description: 数据源级数据分析。根据数据源下的数据模型的摘要生成该数据源的整体语义说明报告，支持保存分析结果到数据源上。关键词：分析数据源，生成数据源报告、分析数据源数据，生成数据源数据报告、保存到数据源。
---

# 数据源摘要分析

## 职责与边界

- **职责**：针对**指定数据源**（通过 id 或 code），查询其下所有数据模型的 **summary** 字段（`tb_data_model.ds_id` 关联），综合这些 summary 内容生成该数据源的**语义说明**（semantic）；若用户明确要求保存，则将该摘要写入 **tb_data_source.semantic** 并更新 update_time。
- **前置依赖**：数据源需已存在；该数据源下已有数据模型及摘要summary（无模型或 summary 全空时，可生成简要说明或提示用户先完善模型摘要）。
- **非职责**：不创建/删除/修改数据源本身（除保存分析结果到数据源 semantic）；不执行单表探索分析（由 admin-data-model-analyzer 负责）；不管理数据模型列表的增删改（由 admin-data-model-assistant 负责）。
- **边界**：仅基于已有模型 summary 做汇总与可选持久化到数据源semantic字段上。

## 工作流程

1. **确定数据源**：根据用户指定或上下文确定目标数据源（id 或 code）。若未指定，可先列出数据源供用户选择，或按 code/name 查询 `tb_data_source` 取得 id。
2. **查询该数据源下所有模型的 summary**：  
   使用 **tool_execute_sql_on_system_db** 执行：  
   `SELECT id, name, summary FROM tb_data_model WHERE ds_id = ?`  
   （参数为数据源 id；仅允许白名单表 tb_data_model，SELECT。）
3. **生成数据源摘要**：根据上一步结果，汇总各条 **summary** 内容，生成一段连贯的、描述该数据源下所有模型整体情况的**数据库语义说明**（建议 Markdown，简明扼要；若无 summary 可注明“暂无模型摘要”或仅列模型名）。
4. **可选保存**：仅当用户明确要求保存时，执行：  
   `UPDATE tb_data_source SET semantic = ?, update_time = ? WHERE id = ?`  
   将生成的数据源语义说明写入 **tb_data_source.semantic**，update_time 用当前时间（如 SQLite：`(strftime('%s','now') * 1000)`）。长文本内单引号需转义为 `''`。
5. **回复用户**：返回生成的数据源摘要内容，并说明是否已保存到该数据源上。

## 表与字段说明

- **tb_data_model**：ds_id 关联数据源；summary 为模型摘要，本 skill 只读并用于汇总。
- **tb_data_source**：id、code 用于定位数据源；**semantic** 为本 skill 可更新的“数据库语义说明”字段；update_time 在保存时一并更新。

## 可用工具

- **tool_execute_sql_on_system_db(sql)**  
  - 查询：`SELECT id, name, summary FROM tb_data_model WHERE ds_id = ?`（获取指定数据源下所有模型及其 summary）。  
  - 更新：`UPDATE tb_data_source SET semantic = ?, update_time = ? WHERE id = ?`（仅在用户要求保存时执行；仅允许白名单表及上述字段）。
- **tool_execute_sql_on_data_source(ds_id_or_code, sql)**  
  - 在指定数据源上执行 SELECT。**ds_id_or_code** 为数据源 id 或 code（即 **tb_data_model.ds_id** 字段对应的数据源标识）。

## 与其它 skill 的协作

- **admin-data-source-assistant**：负责数据源的增删改查；本 skill 仅更新数据源的 semantic（及 update_time）。
- **admin-data-model-analyzer**：负责单模型探索分析与报告；本 skill 不做单表分析，只汇总已有 summary 并生成数据库语义说明。
