# 后台管理领域智能体 Agent 实现规范

本文档基于 `app/agent/` 下的管理域智能体Agent实现实践，总结了后台管理领域智能体 Agent 的设计规范和最佳实践。

## 一、总体架构

### 1.1 技术选型
- **框架**：使用 LangGraph 实现智能体 Agent
- **上下文管理**：通过 LangGraph 的 StateGraph 状态维持一次对话的上下文

### 1.2 设计原则
- **单一职责**：每个 Agent 专注于一个特定的业务领域（如数据模型语义生成、数据源管理等）
- **无会话状态**：后台管理领域的 Agent 通常是解决一个目标明确的问题，这种情况只需要流程内的上下文，不需要维持会话状态
- **状态驱动**：通过 GraphState 管理整个一次工作流执行需要的上下文

## 二、LangGraph节点拆分实践

### 2.1 拆分原则

**❌ 不能拆分太细太多节点**
- 问题：导致智能不够，变成了固定的工作流，容易死板不灵活
- 示例：如果为每个 SQL 任务创建一个节点，会导致工作流过于复杂

**❌ 不能拆分太粗节点太少**
- 问题：实现全部依赖大模型的推理能力，对于复杂问题效果会很差
- 问题场景：需要的推理链很长或者很复杂分支很多

**✅ 最佳实践：把同一个问题的放在一个节点内解决**
- 示例：`DataModelSemanticAgent` 的 SQL 执行节点，虽然需要执行 8 个 SQL 任务，但它们都是"执行一个 SQL 获得 SQL 结果"的相同逻辑，并且是一步一步执行的
- 好处：即使有多个步骤，对大模型来说也非常简单，对大模型能力要求也非常低

## 三、LangGraph入口流程设计

### 3.1 标准入口行为模式

后台管理领域的智能体 Agent 通常有一个目标对象(比如更新数据模型、创建数据模型)，入口阶段应包含两个能力：

1. **Agent 能力的系统提示词**：描述智能体能力，如果不能解决用户问题，直接礼貌拒绝并解释原因和引导用户如何使用
2. **一个确认目标的 tool**：用于确认目标对象是否存在

### 3.2 实现示例

```python
# 系统提示词示例
INTENT_ANALYSIS_PROMPT = """你是一个数据模型语义生成助手，专门负责为数据模型生成语义说明。

## DataModelSemanticAgent的职责范围
- ✅ 为指定数据模型生成语义说明
- ✅ 更新已存在语义说明的模型
- ✅ 重新生成语义说明

## 你的任务
分析用户的请求，判断是否属于 DataModelSemanticAgent 的职责范围。

## 工作方式
- **如果用户的请求属于职责范围**：使用 `tool_get_data_model` 工具获取数据模型信息，开始后续处理流程
- **如果用户的请求不属于职责范围**：礼貌地拒绝用户，说明你的职责范围，不要调用任何工具

## 可用工具
- `tool_get_data_model`: 根据ID或编码获取指定数据模型的详细信息，可以用于确实确认目标对象存在

请分析用户请求，如果不属于职责范围则礼貌拒绝；如果属于职责范围则调用工具，则使用工具tool_get_data_model确认目标模型存在。
"""


# 分析意图（入口阶段）
async def _analyze_intent_node(self, state: DataModelSemanticAgentState):
    """
    入口阶段节点：分析用户意图
    
    使用 tool_get_data_model 工具判断用户请求是否符合 graph 能力：
    - 如果符合：LLM 会返回工具调用，进入正式流程
    - 如果不符合：LLM 会礼貌拒绝，结束流程
    """
    user_input = state["user_input"]
    # 构建消息列表：系统提示词（职责说明）+ 用户消息
    messages = [SystemMessage(content=INTENT_ANALYSIS_PROMPT), user_input]
    
    # 调用 LLM（绑定工具）
    response = await self.llm_intent.ainvoke(messages)
    
    return {
        **state,
        "messages": [response]
    }
```

### 3.3 路由逻辑

**核心设计思想**：能力 + 工具的设计

- **如果用户的请求属于智能体能力范围**：大模型会决策使用工具（如 `tool_get_data_model`）
- **如果用户的请求不属于智能体能力范围**：大模型不会决策使用工具，而是礼貌拒绝

**路由判断**：
```python
def _route_after_intent(self, state: DataModelSemanticAgentState) -> str:
    """
    入口阶段路由：根据LLM响应判断是否符合agent能力
    
    核心逻辑：
    - 有工具调用 = 符合能力，继续处理
    - 无工具调用 = 不符合能力，结束流程
    """
    current_is_tool_call = self._current_is_tool_call(state)
    
    if current_is_tool_call:
        return "can_handle"  # 继续处理
    else:
        return "cannot_handle"  # 结束流程
```

**优势**：
- 使用了尽量少的 LangGraph 图和非常简洁的分支逻辑
- 解决了意图识别 + 分支判断
- 大模型推理的步骤只有 2 个逻辑：
  1. 是否能力范围内
  2. 如果能力范围内，使用工具确认目标存在

## 四、状态管理最佳实践

### 4.1 上下文

通常只需要流程内的上下文，不需要维持会话状态，简化智能体的状态管理

## 五、工作流构建模式

### 5.1 标准工作流结构

```python
def _build_workflow(self) -> StateGraph:
  """
  构建LangGraph工作流
  
  工作流包含以下阶段：
  1. 入口阶段：分析意图，判断是否符合agent能力
  2. 校验分支：获取并提取模型信息
  3. 执行阶段：循环执行任务（如SQL分析）
  4. 生成阶段：汇总结果生成输出
  """
  workflow = StateGraph(DataModelSemanticAgentState)

  # ========== 添加节点 ==========
  # 入口阶段节点
  workflow.add_node("analyze_intent", self._analyze_intent_node)
  workflow.add_node("tools_get_model", self.tool_node_get_model)

  # 执行阶段节点
  workflow.add_node("execute_sql", self._execute_sql_loop_node)
  workflow.add_node("tools_execute_sql", self.tool_node_execute_sql)

  # 生成阶段节点
  workflow.add_node("generate_semantic", self._generate_semantic_node)
  workflow.add_node("extract_semantic", self._extract_semantic_node)
  workflow.add_node("save_semantic", self._save_semantic_node)

  # ========== 工作流连接 ==========
  # 入口阶段：分析意图后，如果有工具调用则继续，否则结束
  workflow.add_conditional_edges(
    "analyze_intent",
    self._route_after_intent,
    {
      "can_handle": "tools_get_model",
      "cannot_handle": END
    }
  )

  # 校验分支：工具执行后，直接从 state 中读取模型信息
  workflow.add_conditional_edges(
    "tools_get_model",
    self._route_after_get_model,
    {
      "model_found": "execute_sql",
      "model_not_found": END
    }
  )

  # 执行阶段：循环执行SQL，直到没有工具调用
  workflow.add_conditional_edges(
    "execute_sql",
    self._should_continue_sql,
    {
      "continue": "tools_execute_sql",
      "semantic": "generate_semantic"
    }
  )
  workflow.add_edge("tools_execute_sql", "execute_sql")  # 工具执行后，继续循环

  # 生成阶段：生成 -> 提取 -> 保存 -> 结束
  workflow.add_edge("generate_semantic", "extract_semantic")
  workflow.add_edge("extract_semantic", "save_semantic")
  workflow.add_edge("save_semantic", END)

  return workflow.compile()
```

### 5.2 循环执行模式

对于需要循环执行的任务（如多个 SQL 任务），使用以下模式：

```python
# 执行节点：LLM 决策执行哪些任务
async def _execute_sql_node(self, state: DataModelSemanticAgentState):
    """
    SQL阶段节点：LLM决策执行哪些SQL分析任务
    
    构建消息列表包含：
    1. 模型信息背景（固定系统提示词）
    2. SQL分析任务要求（HumanMessage）
    3. 历史消息（之前执行的SQL任务结果）
    
    LLM会根据历史消息决定下一步要执行哪些SQL任务，并返回工具调用。
    """
    model_info = state.get("model_info")
    history_messages = state.get("messages", [])
    
    # 构建消息列表：模型信息背景 + 任务要求 + 历史消息
    messages = [
        SystemMessage(content=model_info_prompt),
        HumanMessage(content=EXECUTE_SQL_ANALYSIS_PROMPT)
    ] + history_messages
    
    response = await self.llm_execute_sql.ainvoke(messages)
    return {
        **state,
        "messages": [response]
    }

# 路由判断：是否继续执行
def _should_continue_sql(self, state: DataModelSemanticAgentState) -> str:
    """
    SQL阶段路由：根据LLM响应判断是否继续执行SQL工具
    """
    current_is_tool_call = self._current_is_tool_call(state)
    
    if current_is_tool_call:
        return "continue"  # 继续执行工具
    else:
        return "semantic"  # SQL任务完成，进入语义生成阶段
```

## 六、LLM 和工具绑定

### 6.1 为不同节点创建专用的 LLM 绑定

```python
def __init__(self):
    # 初始化基础 LLM
    self.llm = ChatOpenAI(**init_kwargs)
    
    # 为不同节点创建专用的 llm_with_tool 和独立的 ToolNode
    # 节点1：分析意图
    self.llm_intent = self.llm.bind_tools([tool_get_data_model])
    self.tool_node_get_model = ToolNode([tool_get_data_model])
    
    # 节点2：执行数据分析SQL
    self.llm_execute_sql = self.llm.bind_tools([tool_execute_sql_data_model])
    self.tool_node_execute_sql = ToolNode([tool_execute_sql_data_model])
    
    # 节点3：生成语义说明（不绑定工具，避免参数截断）
    self.llm_update_semantic = self.llm  # 不绑定工具，让LLM生成完整语义说明
```

## 七、日志规范

### 7.1 Agent 日志格式

```python
# 节点输入日志
logger.info(f"[NODE-NAME] [LLM-INPUT] 描述信息")

# 节点输出日志
logger.info(f"[NODE-NAME] [LLM-OUTPUT] 描述信息")

# 路由决策日志
logger.info(f"[ROUTE-NAME] [SUCCESS] 描述信息")
logger.warning(f"[ROUTE-NAME] [FAILED] 描述信息")

# 错误日志
logger.error(f"[NODE-NAME] [ERROR] 错误信息", exc_info=True)
```

### 7.2 工具日志格式

```python
# 工具调用日志
logger.info(f"[TOOL-CALL] tool_name - {format_tool_params(...)}")

# 工具结果日志
logger.info(f"[TOOL-RESULT] tool_name - 成功: 描述信息")
logger.error(f"[TOOL-RESULT] tool_name - 失败: 错误信息", exc_info=True)

# 工具内部调试日志
logger.debug(f"[TOOL-INTERNAL] tool_name - 调试信息")
```

## 八、完整示例

参考 `backend/app/agent/data_model_semantic_agent.py` 的完整实现，该实现遵循了以上所有规范：

1. ✅ 使用 LangGraph 的节点组合实现
2. ✅ 入口阶段包含系统提示词 + 确认目标的工具
3. ✅ 通过工具调用判断是否符合能力范围
4. ✅ 将相同逻辑的任务放在一个节点内（SQL 执行节点）
5. ✅ 工具直接修改 GraphState 状态（model_info）
6. ✅ 使用简洁的分支逻辑实现意图识别和路由

## 九、总结

后台管理领域的智能体 Agent 实现应遵循以下核心原则：

1. **简洁的工作流**：使用尽量少的节点和分支逻辑
2. **智能的意图识别**：通过工具调用判断是否符合能力范围
3. **合理的节点拆分**：将相同逻辑的任务放在一个节点内
4. **直接的状态管理**：关键信息由工具直接保存到 GraphState
5. **清晰的日志规范**：统一的日志格式便于调试和监控

遵循这些规范，可以构建出既灵活又可靠的智能体 Agent。

