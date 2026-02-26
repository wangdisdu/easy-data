"""智能体初始化数据: [admin]系统管理助手（含本 agent 的节点与边）"""

import json

DESCRIPTION = """系统管理智能体，专门负责根据用户问题选择合适的系统管理子智能体来处理。
"""

CONFIG = None

ROW = {
    "name": "[admin]系统管理助手",
    "description": DESCRIPTION,
    "config": json.dumps(CONFIG) if CONFIG else "",
    "status": "active",
    "extend": "",
    "id": 5,
}

# 节点 config 以独立变量声明（仅对有 config 的节点），script 用三引号
NODE2_CONFIG = {
    "llm_id": 1,
    "script": '''async def execute(state, llm, tools):
    from langchain_core.messages import SystemMessage, AIMessage
    SYS_PROMPT = """你是一个系统管理助手，专门负责根据用户问题选择合适的子智能体来处理。

## 你的职责
根据用户问题的意图，判断应该由哪个子智能体来处理：
1. **DataSourceAgent**：数据源管理相关任务
2. **DataModelAgent**：数据模型管理相关任务
3. **DataModelAnalysisAgent**：数据模型分析相关任务
4. **SystemHealthAgent**：系统健康检查相关任务

## 可用子智能体及其能力

### 1. DataSourceAgent（数据源管理智能体）
**职责范围**：
- ✅ 新增数据源：创建新的数据源配置
- ✅ 查询数据源：查看或查找已存在的数据源信息
- ✅ 测试数据源：测试某个数据源的连接是否正常
- ✅ 删除数据源：删除数据源及其关联的数据模型
- ✅ 更新数据源：更新数据源的名称、账号密码等信息

**非职责范围**：
- ❌ 数据模型相关操作（导入、创建、查询数据模型等）
- ❌ 数据查询和分析（执行SQL查询等）
- ❌ 其他与数据源管理无关的请求

**用户示例输入**：
- "添加一个MySQL数据源"
- "查询所有数据源"
- "测试数据源连接"
- "删除数据源1"
- "更新数据源1的名称"

### 2. DataModelAgent（数据模型管理智能体）
**职责范围**：
- ✅ 查阅数据模型：查看指定数据源下的所有模型信息（简化信息：id、code、name、是否已有语义说明、是否已有总结说明）或指定模型的明细信息（模型全部信息）
- ✅ 导入数据模型：从数据源自动导入表和视图为数据模型
- ✅ 删除数据模型：删除指定数据源下的指定模型或所有模型

**非职责范围**：
- ❌ 数据源相关操作（创建、查询、测试数据源等）
- ❌ 数据查询和分析（执行SQL查询等）
- ❌ 数据模型分析（应使用DataModelAnalysisAgent）
- ❌ 其他与数据模型管理无关的请求

**用户示例输入**：
- "查看数据源1下的所有模型"
- "列出mysql01数据源下的模型"
- "查询数据源下的模型信息"
- "查看模型public.users的详细信息"
- "从mysql01数据源导入数据模型"
- "删除模型public.users"
- "删除数据源1下的所有模型"
- "清空数据源下的模型"

### 3. DataModelAnalysisAgent（数据模型分析智能体）
**职责范围**：
- ✅ 分析指定数据模型的数据
- ✅ 利用多个探索SQL分析数据模型中的数据特征、分布、统计信息等
- ✅ 总结数据模型中的数据信息、业务含义和数据用途
- ✅ 如果用户有要求，支持将分析结果更新保存到数据库中

**非职责范围**：
- ❌ 导入数据模型
- ❌ 创建数据模型
- ❌ 查询数据模型列表
- ❌ 删除数据模型
- ❌ 其他与数据模型分析无关的请求

**用户示例输入**：
- "分析数据模型1的数据"
- "分析public.users表的数据"
- "分析users表的数据特征和业务含义"

### 4. SystemHealthAgent（系统健康检查智能体）
**职责范围**：
- ✅ 检查系统内是否创建了数据源，数据源的基础信息不能缺少
- ✅ 检查已创建的数据源是否能连接成功
- ✅ 检查数据源下是否已有模型
- ✅ 检查数据源下的模型是否在数据库的表/视图中存在
- ✅ 检查数据源下的模型是否已经生成了语义说明
- ✅ 检查数据源下的模型的语义说明的更新时间是否太旧了，至少一周更新一次

**非职责范围**：
- ❌ 数据源管理操作（创建、删除、更新数据源等）
- ❌ 数据模型管理操作（导入、删除数据模型等）
- ❌ 数据模型分析操作
- ❌ 其他与系统健康检查无关的请求

**用户示例输入**：
- "检查系统健康状态"
- "系统健康检查"
- "检查系统是否正常"
- "运行系统健康检查"

## 你的工作方式
1. **分析用户意图**：理解用户问题的意图，确定应该由哪个子智能体处理
2. **路由到子智能体**：如果匹配某个子智能体的能力，返回对应的子智能体名称（"DataSourceAgent"、"DataModelAgent"、"DataModelAnalysisAgent" 或 "SystemHealthAgent"）
3. **礼貌拒绝**：如果用户问题不属于任何子智能体的能力范围，礼貌地拒绝并说明原因

## 判断标准
- **DataSourceAgent**：如果用户问题涉及数据源的创建、查询、测试、删除、更新等操作
- **DataModelAgent**：如果用户问题涉及数据模型的查阅、导入、删除、清空等管理操作
- **DataModelAnalysisAgent**：如果用户问题涉及数据模型的数据分析、特征总结、业务含义分析等
- **SystemHealthAgent**：如果用户问题涉及系统健康检查、系统状态检查等

## 拒绝话术
如果用户问题不属于任何子智能体的能力范围，请使用以下话术：
"抱歉，我无法处理您的问题。当前系统提供了以下智能体服务：

1. **数据源管理**：创建、查询、测试、删除、更新数据源
2. **数据模型管理**：查阅、导入、删除数据模型
3. **数据模型分析**：分析数据模型的数据特征和业务含义
4. **系统健康检查**：检查系统健康状态

请根据您的需求，明确选择相应的服务。如果您需要帮助，我可以为您提供更详细的使用说明。"

## 输出格式
请直接返回子智能体的名称（"DataSourceAgent"、"DataModelAgent"、"DataModelAnalysisAgent" 或 "SystemHealthAgent"），如果无法处理，请礼貌拒绝。

请分析用户问题，选择合适的子智能体或礼貌拒绝。
"""
    try:
        messages = state["messages"]
        messages = [SystemMessage(content=SYS_PROMPT), *messages]
        response = await llm.ainvoke(messages)

        selected_agent = None
        content = response.content
        content_lower = content.lower()
        if "datasourceagent" in content_lower:
            selected_agent = "data_source"
        elif "datamodelagent" in content_lower:
            selected_agent = "data_model"
        elif "datamodelanalysisagent" in content_lower:
            selected_agent = "data_model_analysis"
        elif "systemhealthagent" in content_lower:
            selected_agent = "system_health"

        return {
            "messages": [response],
            "data": {
                "selected_agent": selected_agent,
            },
        }
    except Exception as e:
        error_msg = f"处理消息失败: {e!s}"
        return {
            "messages": [AIMessage(content=error_msg)],
        }
''',
    "tool_ids": [],
}

NODE3_CONFIG = {
    "script": """def execute(state):
    data = state.get("data")
    selected_agent = data.get("selected_agent")
    return selected_agent
""",
    "route_mapping": ["data_source", "data_model", "data_model_analysis", "system_health"],
}

NODE4_CONFIG = {"agent_id": 1}

NODE5_CONFIG = {"agent_id": 2}

NODE6_CONFIG = {"agent_id": 3}

NODE7_CONFIG = {"agent_id": 4}

NODE_ROWS = [
    {
        "agent_id": 5,
        "name": "起始点",
        "node_type": "start",
        "config": None,
        "description": None,
        "extend": None,
        "id": 40,
    },
    {
        "agent_id": 5,
        "name": "LLM意图识别",
        "node_type": "llm",
        "config": json.dumps(NODE2_CONFIG),
        "description": None,
        "extend": None,
        "id": 41,
    },
    {
        "agent_id": 5,
        "name": "条件分支",
        "node_type": "condition",
        "config": json.dumps(NODE3_CONFIG),
        "description": None,
        "extend": None,
        "id": 42,
    },
    {
        "agent_id": 5,
        "name": "子图节点",
        "node_type": "subgraph",
        "config": json.dumps(NODE4_CONFIG),
        "description": None,
        "extend": None,
        "id": 43,
    },
    {
        "agent_id": 5,
        "name": "子图节点",
        "node_type": "subgraph",
        "config": json.dumps(NODE5_CONFIG),
        "description": None,
        "extend": None,
        "id": 44,
    },
    {
        "agent_id": 5,
        "name": "子图节点",
        "node_type": "subgraph",
        "config": json.dumps(NODE6_CONFIG),
        "description": None,
        "extend": None,
        "id": 45,
    },
    {
        "agent_id": 5,
        "name": "子图节点",
        "node_type": "subgraph",
        "config": json.dumps(NODE7_CONFIG),
        "description": None,
        "extend": None,
        "id": 46,
    },
    {
        "agent_id": 5,
        "name": "结束点",
        "node_type": "end",
        "config": None,
        "description": None,
        "extend": None,
        "id": 47,
    },
    {
        "agent_id": 5,
        "name": "结束点",
        "node_type": "end",
        "config": None,
        "description": None,
        "extend": None,
        "id": 48,
    },
    {
        "agent_id": 5,
        "name": "结束点",
        "node_type": "end",
        "config": None,
        "description": None,
        "extend": None,
        "id": 49,
    },
    {
        "agent_id": 5,
        "name": "结束点",
        "node_type": "end",
        "config": None,
        "description": None,
        "extend": None,
        "id": 50,
    },
]

EDGE_ROWS = [
    {
        "agent_id": 5,
        "from_node_id": 40,
        "from_node_slot": 0,
        "to_node_id": 41,
        "to_node_slot": 0,
        "id": 40,
    },
    {
        "agent_id": 5,
        "from_node_id": 41,
        "from_node_slot": 0,
        "to_node_id": 42,
        "to_node_slot": 0,
        "id": 41,
    },
    {
        "agent_id": 5,
        "from_node_id": 42,
        "from_node_slot": 0,
        "to_node_id": 43,
        "to_node_slot": 0,
        "id": 42,
    },
    {
        "agent_id": 5,
        "from_node_id": 42,
        "from_node_slot": 1,
        "to_node_id": 44,
        "to_node_slot": 0,
        "id": 43,
    },
    {
        "agent_id": 5,
        "from_node_id": 42,
        "from_node_slot": 2,
        "to_node_id": 45,
        "to_node_slot": 0,
        "id": 44,
    },
    {
        "agent_id": 5,
        "from_node_id": 42,
        "from_node_slot": 3,
        "to_node_id": 46,
        "to_node_slot": 0,
        "id": 45,
    },
    {
        "agent_id": 5,
        "from_node_id": 43,
        "from_node_slot": 0,
        "to_node_id": 47,
        "to_node_slot": 0,
        "id": 46,
    },
    {
        "agent_id": 5,
        "from_node_id": 44,
        "from_node_slot": 0,
        "to_node_id": 48,
        "to_node_slot": 0,
        "id": 47,
    },
    {
        "agent_id": 5,
        "from_node_id": 45,
        "from_node_slot": 0,
        "to_node_id": 49,
        "to_node_slot": 0,
        "id": 48,
    },
    {
        "agent_id": 5,
        "from_node_id": 46,
        "from_node_slot": 0,
        "to_node_id": 50,
        "to_node_slot": 0,
        "id": 49,
    },
]
