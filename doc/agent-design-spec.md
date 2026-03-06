# 智能体开发规范

## 1. 目录结构

每个智能体对应 `agents/` 下的一个子目录，目录名即智能体 id（如 `admin`、`text_to_sql`、`main`）。

## 2. 必需与可选文件

| 文件 | 必需 | 说明 |
|------|------|------|
| **AGENT.md** | 是 | 智能体设定：名字、描述、能力范围等。作为智能体的系统提示词使用。 |
| **MEMORY.md** | 否 | 智能体长期记忆的静态文件，用于补充上下文。 |
| **skills/** | 否 | 技能目录，内含各 SKILL 子目录。不定义则智能体无 skill 能力。 |
| **TOOLS.json** | 否 | 智能体需要的系统工具列表。JSON 数组格式，如 `["tool_execute_system_sql", "tool_test_data_source_setting"]`。不定义则无系统工具。 |
| **SUB_AGENTS.json** | 否 | 多智能体协作时声明子智能体。JSON 数组格式，如 `["admin", "text_to_sql"]`。子智能体的 AGENT.md 内容作为其描述信息。 |

## 3. 文件说明

### 3.1 AGENT.md

- **用途**：智能体系统提示词，定义身份、职责与能力范围。
- **格式**：Markdown 文本。
- **建议内容**：名字、描述、能力范围（可引用 skills 下的 SKILL）、职责边界、决策方式等。

### 3.2 MEMORY.md

- **用途**：长期记忆的静态文件，作为可选补充上下文。
- **格式**：Markdown 文本。
- **可选**：不定义则仅使用 AGENT.md。

### 3.3 TOOLS.json

- **用途**：声明该智能体需要的系统工具。
- **格式**：JSON 数组，元素为工具名称字符串。
- **示例**：
  ```json
  ["tool_execute_system_sql", "tool_test_data_source_setting", "tool_check_data_source_connection"]
  ```
- **可选**：不定义或空数组表示无系统工具。工具名称需与项目代码中注册的名称一致。

### 3.4 SUB_AGENTS.json

- **用途**：多智能体协作时，声明需要调用的子智能体。
- **格式**：JSON 数组，元素为子智能体 id。
- **示例**：
  ```json
  ["admin", "text_to_sql"]
  ```
- **可选**：仅主智能体（如 `main`）需要时定义。子智能体的 AGENT.md 内容将作为其描述信息用于路由决策。

## 4. skills 目录（可选）

- 若存在 `skills/`，每个 skill 为独立子目录，如 `skills/admin-data-source-assistant/`。
- 子目录内需包含 `SKILL.md`，描述该 skill 的职责与使用方式。
- 智能体根据 AGENT.md 中的能力描述，选择并调用对应的 skill。不定义 skills/ 则智能体仅依赖 AGENT.md 与工具。

## 5. 加载顺序

1. 读取 `AGENT.md` 作为主系统提示词。
2. 若存在 `MEMORY.md`，追加为记忆上下文。
3. 若存在 `TOOLS.json`，按名称解析并绑定系统工具。
4. 若存在 `SUB_AGENTS.json`，仅加载并编排这些子智能体（主智能体场景）。
