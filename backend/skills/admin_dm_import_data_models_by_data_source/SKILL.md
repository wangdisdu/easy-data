---
name: admin-dm-import-data-models-by-data-source
description: Imports all tables and views from a data source (by ID or code) as data models. New models have no semantic initially; guide user to generate semantic. Use when the user asks to import models from a data source, sync tables/views, or load data models.
---

# 自动将指定数据源的表和视图生成数据模型

## 职责

- 按数据源 **ID** 或 **编码**，将该数据源（用户数据库）下的**所有表与视图**自动扫描并创建为系统内的数据模型，可一次性批量创建多个数据模型。

## 标识符说明（ds_id_or_code）

- 若为**数字字符串**（如 `"1"`、`"123"`），视为数据源 **ID**；否则视为数据源 **编码（code）**（如 `"mysql01"`）。数据源必须已配置且具备 database 信息，否则会返回错误。

## 重要提示

- 数据模型的 **code 必须唯一**；若已存在相同 code 的模型，该条会跳过并记录错误，不影响其他记录。
- 批量创建时单条失败不影响其他记录；返回结果会包含成功与失败的详细信息（成功数量、失败数量、成功/失败列表）。
- 生成的新模型**没有语义说明**，需引导用户后续为模型生成语义说明。

## 模型 code / name 生成说明

- **code**：有 schema 时格式为 `{database}.{schema}.{table或view}`；无 schema 时为 `{database}.{table或view}`。
- **name**：直接使用表名或视图名。

## 使用场景

- 从数据源自动生成数据模型
- 批量导入数据库表和视图为数据模型
- 快速建立数据模型目录

## 执行方式

- 直接调用保留工具 **tool_import_data_models_by_data_source**(ds_id_or_code)。该工具会连接用户数据库获取表/视图列表并写入系统库，不在此 SKILL 内生成 INSERT SQL。
- 导入完成后根据返回的成功/失败摘要回复用户，并提示可为新模型生成语义说明。

## 可用工具

- `tool_import_data_models_by_data_source`：从数据源导入表/视图为数据模型（保留工具，会连接用户数据库）
