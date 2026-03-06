---
name: data-information-exploration
description: TextToSQL数据信息分析。专职分析并获取用户问题所需的数据模型信息，用于在系统中维护的所有数据模型(表/视图)探索查找解决用户问题涉及数据模型。
---

# 数据信息分析（Text2SQL 前置）

## 职责与边界

- **职责**：在用户提出自然语言数据查询需求时，负责
  - （1）获取所有数据模型的基本信息（id、summary）；
  - （2）根据用户需求与各模型 summary 分析并决策需要用到哪些模型；
  - （3）获取这些模型的详细信息（id、name、platform、ds_id、semantic、summary、knowledge），作为后续 **sql-generator** 生成 SQL、**sql-executor** 执行 SQL 的输入。
- **不负责**：不生成 SQL、不执行 SQL；生成由 **sql-generator** 负责，执行由 **sql-executor** 负责。
- **边界**：仅查询系统表 tb_data_model；若无任何模型或无法从 summary 匹配到可解决用户问题的模型，应礼貌拒绝并建议用户先导入数据源、生成数据模型后再提问。

## 工作流程（三步）

**第一步：获取所有数据模型概要**  
通过 **tool_execute_system_sql** 执行：  
`SELECT id, summary FROM tb_data_model`  
得到所有数据模型的 id 与 summary，用于理解各模型对应的业务含义与数据范围。

**第二步：根据用户需求与 summary 决策所需模型 id**  
结合用户问题与第一步返回的各模型 **summary**，判断解决用户问题需要用到哪些模型的数据，确定**模型 id 列表**。  
- 能匹配到：得到 id 列表，进入第三步。  
- 匹配不到：判定为“不能解决”，礼貌说明当前没有与问题相关的数据模型，建议先导入数据源并生成数据模型后再提问，并可提示用户使用数据源/数据模型管理相关能力。

**第三步：获取涉及模型的详细信息**  
通过 **tool_execute_system_sql** 执行（将第二步得到的 id 列表填入 IN 子句）：  
`SELECT id, name, platform, ds_id, semantic, summary, knowledge FROM tb_data_model WHERE id IN (id1, id2, ...)`  
得到这些模型的 name、platform、ds_id、semantic、summary、knowledge。  
- **交付**：将上述详细信息（及模型列表）提供给 **sql-generator** 生成 SELECT，再由 **sql-executor** 在对应数据源上执行。  
- 执行时注意：IN 中为具体 id 值，多个用逗号分隔；仅查询白名单表 tb_data_model。

## 选模型与拒绝细则

- 第一步的 **id、summary** 用于理解每个模型对应的业务含义与数据范围。  
- 将用户问题映射到“涉及哪些表/模型”：能匹配则输出模型 id 列表并查详情；匹配不到则拒绝，说明系统中没有相关数据模型，建议先导入数据源并生成数据模型后再提问。

## 可用工具

- **tool_execute_system_sql(sql)**  
  - 用于查询系统表 **tb_data_model**（仅允许白名单表及 SELECT）。  
  - 第一步：`SELECT id, summary FROM tb_data_model` 获取所有模型基本信息。  
  - 第三步：`SELECT id, name, platform, ds_id, semantic, summary, knowledge FROM tb_data_model WHERE id IN (id1, id2, ...)` 获取涉及模型的详细信息；IN 中为具体 id，多个用逗号分隔。

## 边界情况

- 无任何数据模型或所有模型均无 summary：第一步结果为空或无效时，直接判定为“不能解决”，走拒绝与建议流程。  
- 用户问题含糊或跨多数据源：在现有 summary 下尽量匹配最相关模型，若无法确定则说明并请用户补充或缩小范围。
