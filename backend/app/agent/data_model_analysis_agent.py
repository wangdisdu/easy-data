"""
DataModelAnalysisAgent - 数据模型分析Agent
使用LangGraph实现，专门处理数据模型分析任务
主要功能:利用多个探索SQL分析总结数据模型中的数据
支持将分析结果更新保存到数据库中（根据用户需求）
单一目标Agent，不维持会话状态
"""

import json
from typing import Annotated, Any, Optional, TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, StateGraph
from langgraph.graph.message import REMOVE_ALL_MESSAGES, add_messages
from langgraph.prebuilt import ToolNode

from app.agent.agent_utils import setup_langsmith_tracing
from app.agent.base_agent import BaseAgent
from app.agent.data_model_analysis_agent_prompts import (
    ANALYSIS_MODEL_DATA_PROMPT,
    EXECUTE_SQL_ANALYSIS_PROMPT,
    INTENT_ANALYSIS_PROMPT,
)
from app.core.logging import get_logger
from app.tool import (
    tool_execute_sql_data_model,
    tool_get_data_model,
    tool_update_data_model_semantic_and_summary,
)

logger = get_logger("data_model_analysis_agent")

# 在模块加载时设置 LangSmith 追踪
setup_langsmith_tracing()


class DataModelAnalysisAgentState(TypedDict):
    """数据模型分析Agent状态定义"""

    messages: Annotated[list[BaseMessage], add_messages]  # 所有历史消息
    user_input: HumanMessage  # 用户输入
    sql_messages: []  # SQL子流程的历史消息
    session_id: str
    user_id: Optional[int]
    model_info: Optional[
        dict
    ]  # 模型信息（字典格式，包含 dm_id_or_code, id, name, code, platform, ds_id 等字段）


class DataModelAnalysisAgent(BaseAgent):
    """数据模型分析Agent，使用LangGraph实现

    主要功能:利用多个探索SQL分析总结数据模型中的数据
    支持将分析结果更新保存到数据库中（根据用户需求）
    """

    def __init__(self, user_id: Optional[int] = None):
        super().__init__(user_id=user_id)

        # 为4个节点创建专用的llm_with_tool和独立的ToolNode
        # 节点1:分析意图
        self.llm_intent = self.llm.bind_tools([tool_get_data_model])
        # 使用自定义工具节点来处理 tool_get_data_model 的 Command 更新
        self.tool_node_get_model = ToolNode([tool_get_data_model])

        # 节点3:执行数据分析SQL
        self.llm_execute_sql = self.llm.bind_tools([tool_execute_sql_data_model])
        self.tool_node_execute_sql = ToolNode([tool_execute_sql_data_model])

        # 节点4:分析数据模型数据（绑定工具，可选保存）
        self.llm_analyze_model_data = self.llm.bind_tools(
            [tool_update_data_model_semantic_and_summary]
        )
        self.tool_node_update_semantic_and_summary = ToolNode(
            [tool_update_data_model_semantic_and_summary]
        )

        # 构建LangGraph工作流
        self.workflow = self._build_workflow()

    def build_subgraph(self) -> StateGraph:
        """
        构建子图，供 AdminAgent 使用

        Returns:
            StateGraph: 编译后的工作流图
        """
        return self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """
        构建LangGraph工作流

        工作流包含以下阶段:
        1. 入口阶段:分析意图，判断是否符合agent能力
        2. 校验分支:获取并提取模型信息
        3. SQL阶段:循环执行SQL分析任务
        4. 分析总结阶段:汇总SQL结果生成分析报告（如果用户要求，可保存到数据库）

        Returns:
            StateGraph: 编译后的工作流图
        """
        workflow = StateGraph(DataModelAnalysisAgentState)

        # ========== 添加节点 ==========
        # 入口阶段节点
        workflow.add_node("analyze_intent", self._analyze_intent_node)
        workflow.add_node("tools_get_model", self.tool_node_get_model)
        workflow.add_node(
            "extract_model_info", self._extract_model_info_node
        )  # 从ToolMessage中提取model_info

        # SQL阶段节点
        workflow.add_node(
            "begin_execute_sql", self._begin_execute_sql_node
        )  # SQL阶段开始前的整理工作
        workflow.add_node("execute_sql_loop", self._execute_sql_loop_node)
        workflow.add_node("execute_sql_tool", self.tool_node_execute_sql)

        # 分析总结阶段节点
        workflow.add_node(
            "analyze_model_data", self._analyze_model_data_node
        )  # 生成分析报告（如果用户要求，可保存）
        workflow.add_node(
            "tools_update_semantic_and_summary", self.tool_node_update_semantic_and_summary
        )  # 保存分析结果（可选）

        # 设置入口点
        workflow.set_entry_point("analyze_intent")

        # ========== 工作流连接 ==========
        # 入口阶段:分析意图后，如果有工具调用则继续，否则结束
        workflow.add_conditional_edges(
            "analyze_intent",
            self._route_after_intent,
            {
                "can_handle": "tools_get_model",  # 有工具调用，执行工具
                "cannot_handle": END,  # 无工具调用，结束流程
            },
        )

        # 工具执行后，提取模型信息
        workflow.add_edge("tools_get_model", "extract_model_info")

        # 校验分支:从ToolMessage中提取模型信息后，判断是否成功
        workflow.add_conditional_edges(
            "extract_model_info",
            self._route_after_get_model,
            {
                "model_found": "begin_execute_sql",  # 模型信息提取成功，进入SQL阶段开始前的整理工作
                "model_not_found": END,  # 模型信息提取失败，结束流程
            },
        )

        # SQL阶段开始前的整理工作
        workflow.add_edge("begin_execute_sql", "execute_sql_loop")

        # SQL阶段:循环执行SQL，直到没有工具调用
        # 在execute_sql节点后判断LLM输出是否有工具调用
        workflow.add_conditional_edges(
            "execute_sql_loop",
            self._should_continue_sql,
            {
                "continue": "execute_sql_tool",  # 有工具调用，执行工具后继续循环
                "analyze": "analyze_model_data",  # 没有工具调用，进入分析总结阶段
            },
        )
        workflow.add_edge(
            "execute_sql_tool", "execute_sql_loop"
        )  # 工具执行后，继续循环到execute_sql

        # 分析总结阶段:生成分析报告 -> 如果用户要求则保存 -> 结束
        workflow.add_conditional_edges(
            "analyze_model_data",
            self._should_save_analysis_result,
            {
                "save": "tools_update_semantic_and_summary",  # 用户要求保存，执行保存工具
                "end": END,  # 用户未要求保存，直接结束
            },
        )
        workflow.add_edge("tools_update_semantic_and_summary", "analyze_model_data")

        # 编译工作流
        graph = workflow.compile()
        print(graph.get_graph().draw_mermaid())
        return graph

    async def _analyze_intent_node(
        self, state: DataModelAnalysisAgentState
    ) -> DataModelAnalysisAgentState:
        """
        入口阶段节点:分析用户意图

        使用tool_get_data_model工具判断用户请求是否符合agent能力:
        - 如果符合:LLM会返回工具调用，进入正式流程
        - 如果不符合:LLM会礼貌拒绝，结束流程

        Args:
            state: 当前状态

        Returns:
            更新后的状态，包含LLM的响应消息
        """
        try:
            user_input = state["user_input"]
            # 构建消息列表:系统提示词（职责说明）+ 用户消息
            messages = [SystemMessage(content=INTENT_ANALYSIS_PROMPT), user_input]

            logger.info(f"[INTENT] [LLM-INPUT] 用户输入: {user_input.content[:100]}...")
            response = await self.llm_intent.ainvoke(messages)
            tool_call_count = (
                len(response.tool_calls)
                if hasattr(response, "tool_calls") and response.tool_calls
                else 0
            )
            logger.info(
                f"[INTENT] [LLM-OUTPUT] 响应类型: {type(response).__name__}, 工具调用数: {tool_call_count}"
            )

            return {**state, "messages": [response]}
        except Exception as e:
            error_msg = f"分析意图失败: {e!s}"
            logger.exception("[INTENT] [ERROR] 分析意图失败")
            return {**state, "messages": [AIMessage(content=error_msg)]}

    def _current_is_tool_call(self, state: DataModelAnalysisAgentState) -> bool:
        """
        检查最新消息是否为工具调用

        Args:
            state: 当前状态

        Returns:
            True: 最新消息包含工具调用
            False: 最新消息不包含工具调用
        """
        messages = state.get("messages", [])
        if not messages:
            return False

        last_message = messages[-1]
        return hasattr(last_message, "tool_calls") and bool(last_message.tool_calls)

    def _route_after_intent(self, state: DataModelAnalysisAgentState) -> str:
        """
        入口阶段路由:根据LLM响应判断是否符合agent能力

        Args:
            state: 当前状态

        Returns:
            "can_handle": 检测到工具调用，符合能力，继续处理
            "cannot_handle": 未检测到工具调用，不符合能力，结束流程
        """
        current_is_tool_call = self._current_is_tool_call(state)

        if current_is_tool_call:
            logger.info("[ROUTE-INTENT] [SUCCESS] 检测到工具调用，符合agent能力，继续处理")
            return "can_handle"
        else:
            logger.info("[ROUTE-INTENT] [REJECT] 未检测到工具调用，不符合agent能力，结束流程")
            return "cannot_handle"

    async def _extract_model_info_node(
        self, state: DataModelAnalysisAgentState
    ) -> DataModelAnalysisAgentState:
        """
        从ToolMessage中提取model_info并保存到state

        该节点从 tools_get_model 节点执行后的 ToolMessage 中提取模型信息，
        解析JSON格式的返回结果，提取关键字段构建 model_info 字典并保存到 state.

        Args:
            state: 当前状态

        Returns:
            更新后的状态，包含提取的 model_info
        """
        try:
            messages = state.get("messages", [])
            if not messages:
                error_msg = "消息列表为空，无法提取模型信息"
                logger.error(f"[EXTRACT-MODEL-INFO] [ERROR] {error_msg}")
                return {**state, "model_info": None}

            # 查找最新的 ToolMessage（tool_get_data_model 的返回结果）
            tool_message = None
            for message in reversed(messages):
                if isinstance(message, ToolMessage):
                    tool_message = message
                    break

            if not tool_message or not tool_message.content:
                error_msg = "未找到 ToolMessage 或内容为空，无法提取模型信息"
                logger.error(f"[EXTRACT-MODEL-INFO] [ERROR] {error_msg}")
                return {**state, "model_info": None}

            # 解析 ToolMessage 中的 JSON 内容
            try:
                result = json.loads(tool_message.content)
            except json.JSONDecodeError as e:
                error_msg = f"解析 ToolMessage JSON 失败: {e!s}"
                logger.exception("[EXTRACT-MODEL-INFO] [ERROR] 解析 ToolMessage JSON 失败")
                return {**state, "model_info": None}

            # 提取关键字段构建 model_info 字典
            # 根据 tool_get_data_model 的返回格式，提取 id, code, name, platform, ds_id 等字段
            model_info = {
                "dm_id_or_code": (
                    str(result.get("id")) if result.get("id") else result.get("code", "")
                ),
                "id": result.get("id"),
                "code": result.get("code"),
                "name": result.get("name"),
                "platform": result.get("platform"),
                "ds_id": result.get("ds_id"),
            }

            # 验证必要字段是否存在
            if (
                not model_info.get("id")
                or not model_info.get("name")
                or not model_info.get("code")
                or not model_info.get("platform")
            ):
                error_msg = "模型信息缺少必要字段（id、name、code、platform）"
                logger.error(f"[EXTRACT-MODEL-INFO] [ERROR] {error_msg}")
                return {**state, "model_info": None}

            logger.info(
                f"[EXTRACT-MODEL-INFO] [SUCCESS] 已从 ToolMessage 提取模型信息: {model_info.get('code')} ({model_info.get('platform')})"
            )

            return {**state, "model_info": model_info}
        except Exception as e:
            error_msg = f"提取模型信息失败: {e!s}"
            logger.exception("[EXTRACT-MODEL-INFO] [ERROR] 提取模型信息失败")
            return {**state, "model_info": None}

    def _route_after_get_model(self, state: DataModelAnalysisAgentState) -> str:
        """
        校验分支路由:根据 state 中的模型信息判断下一步

        extract_model_info 节点已从 ToolMessage 中提取模型信息并保存到 state["model_info"] 中，
        本函数直接从 state 中读取模型信息，判断是否成功提取。

        Args:
            state: 当前状态

        Returns:
            "model_found": 模型信息存在，进入SQL阶段
            "model_not_found": 模型信息不存在，结束流程
        """
        model_info = state.get("model_info")
        if model_info and isinstance(model_info, dict):
            logger.info(
                f"[ROUTE-MODEL] [SUCCESS] 模型信息已从 state 获取: {model_info.get('code')} ({model_info.get('platform')})，进入SQL阶段"
            )
            return "model_found"
        else:
            logger.warning("[ROUTE-MODEL] [FAILED] state 中未找到模型信息，结束流程")
            return "model_not_found"

    async def _begin_execute_sql_node(
        self, state: DataModelAnalysisAgentState
    ) -> DataModelAnalysisAgentState:
        """
        SQL阶段开始前的整理节点:清空历史消息

        在正式进入SQL执行循环前，清空之前的消息历史，为SQL阶段准备干净的消息历史。
        因为模型信息已经保存在 state 中，不需要保留 tool_get_data_model 的结果。

        Args:
            state: 当前状态

        Returns:
            更新后的状态，messages 被清空
        """
        try:
            logger.debug("[BEGIN-EXECUTE-SQL] [INTERNAL] 清空消息历史，为SQL阶段准备干净的消息历史")

            return {**state, "messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES)]}  # 清空历史消息
        except Exception as e:
            error_msg = f"SQL阶段开始前的整理工作失败: {e!s}"
            logger.exception("[BEGIN-EXECUTE-SQL] [ERROR] 整理工作失败")
            return {**state, "messages": [AIMessage(content=error_msg)]}

    def _build_model_info_prompt(self, model_info: dict) -> str:
        """
        构建模型信息的固定背景提示词

        该提示词会在SQL阶段和语义生成阶段作为系统提示词的一部分，
        为LLM提供数据模型的基本信息。

        Args:
            model_info: 模型信息字典，包含 dm_id_or_code, id, name, code, platform, ds_id 等字段

        Returns:
            格式化的模型信息提示词字符串
        """
        return f"""## 数据模型信息（固定背景）
- 数据模型标识符: {model_info.get("dm_id_or_code")}
- 表名: {model_info.get("name")}
- 数据库类型: {model_info.get("platform")}
- 数据模型编码: {model_info.get("code")}
- 数据模型ID: {model_info.get("id")}
- 数据源ID: {model_info.get("ds_id")}

**重要提示**:表名是 `{model_info.get("name")}`，数据库类型是 `{model_info.get("platform")}`，请根据数据库类型使用正确的SQL语法。

"""

    async def _execute_sql_loop_node(
        self, state: DataModelAnalysisAgentState
    ) -> DataModelAnalysisAgentState:
        """
        SQL阶段节点:LLM决策执行哪些SQL分析任务

        构建消息列表包含:
        1. 模型信息背景
        2. SQL分析任务要求
        3. 历史消息（之前执行的SQL任务结果）

        LLM会根据历史消息决定下一步要执行哪些SQL任务，并返回工具调用。

        注意:历史消息已在 begin_execute_sql 节点中清空，这里直接使用当前 messages.

        Args:
            state: 当前状态

        Returns:
            更新后的状态，包含LLM的响应消息（可能包含工具调用）
        """
        try:
            model_info = state.get("model_info")
            if not model_info:
                error_msg = "模型信息不存在，无法执行SQL分析"
                logger.error(f"[EXECUTE-SQL] [ERROR] {error_msg}")
                return {**state, "messages": [AIMessage(content=error_msg)]}

            # 获取历史消息（已在 begin_execute_sql 节点中清空，这里直接使用）
            his_messages = state.get("messages", [])

            model_info_prompt = self._build_model_info_prompt(model_info)

            # 构建消息列表:模型信息背景 + 任务要求 + 历史消息
            messages = [
                SystemMessage(content=model_info_prompt),
                SystemMessage(content=EXECUTE_SQL_ANALYSIS_PROMPT),
                *his_messages,
            ]

            logger.info(f"[EXECUTE-SQL] [LLM-INPUT] : {messages}")
            response = await self.llm_execute_sql.ainvoke(messages)
            tool_calls_count = (
                len(response.tool_calls)
                if hasattr(response, "tool_calls") and response.tool_calls
                else 0
            )
            logger.info(f"[EXECUTE-SQL] [LLM-OUTPUT] 工具调用数: {tool_calls_count}")

            return {**state, "messages": [*his_messages, response]}
        except Exception as e:
            error_msg = f"执行SQL分析失败: {e!s}"
            logger.exception("[EXECUTE-SQL] [ERROR] 执行SQL分析失败")
            return {**state, "messages": [AIMessage(content=error_msg)]}

    def _should_continue_sql(self, state: DataModelAnalysisAgentState) -> str:
        """
        SQL阶段路由:根据LLM响应判断是否继续执行SQL工具

        Args:
            state: 当前状态

        Returns:
            "continue": 检测到工具调用，继续执行SQL工具
            "analyze": 未检测到工具调用，SQL任务完成，进入分析总结阶段
        """
        current_is_tool_call = self._current_is_tool_call(state)

        if current_is_tool_call:
            logger.info("[ROUTE-SQL] [CONTINUE] 检测到工具调用，继续执行SQL任务")
            return "continue"
        else:
            logger.info("[ROUTE-SQL] [COMPLETE] 未检测到工具调用，SQL任务完成，进入分析总结阶段")
            return "analyze"

    def _should_save_analysis_result(self, state: DataModelAnalysisAgentState) -> str:
        """
        分析总结阶段路由:根据LLM响应和用户要求判断是否需要保存分析结果

        Args:
            state: 当前状态

        Returns:
            "save": 检测到工具调用（用户要求保存），执行保存工具
            "end": 未检测到工具调用（用户未要求保存），直接结束流程
        """
        current_is_tool_call = self._current_is_tool_call(state)

        if current_is_tool_call:
            logger.info("[ROUTE-ANALYSIS] [SAVE] 检测到工具调用，用户要求保存分析结果")
            return "save"
        else:
            logger.info("[ROUTE-ANALYSIS] [END] 未检测到工具调用，用户未要求保存，直接结束流程")
            return "end"

    async def _analyze_model_data_node(
        self, state: DataModelAnalysisAgentState
    ) -> DataModelAnalysisAgentState:
        """
        分析总结阶段节点:汇总所有SQL结果生成分析报告

        构建消息列表包含:
        1. 模型信息背景
        2. 分析总结任务要求
        3. 历史消息（所有SQL执行的结果）

        LLM会分析所有SQL结果，生成Markdown格式的分析报告。
        如果用户要求保存，LLM会调用工具将分析结果保存到数据库。

        Args:
            state: 当前状态

        Returns:
            更新后的状态，包含LLM生成的分析报告（如果用户要求保存，可能包含工具调用）
        """
        try:
            model_info = state.get("model_info")
            if not model_info:
                error_msg = "模型信息不存在，无法生成分析报告"
                logger.error(f"[ANALYZE-MODEL-DATA] [ERROR] {error_msg}")
                return {**state, "messages": [AIMessage(content=error_msg)]}

            user_input = state["user_input"]

            history_messages = state.get("messages", [])

            model_info_prompt = self._build_model_info_prompt(model_info)

            # 构建消息列表:模型信息背景 + 任务要求 + 历史消息（包含所有SQL结果）
            messages = [
                SystemMessage(content=model_info_prompt),
                SystemMessage(content=ANALYSIS_MODEL_DATA_PROMPT),
                user_input,
                *history_messages,
            ]

            logger.info(
                f"[ANALYZE-MODEL-DATA] [LLM-INPUT] 模型: {model_info.get('name')}, 历史消息数: {len(history_messages)}"
            )
            response = await self.llm_analyze_model_data.ainvoke(messages)
            response_length = len(response.content) if response.content else 0
            tool_calls_count = (
                len(response.tool_calls)
                if hasattr(response, "tool_calls") and response.tool_calls
                else 0
            )
            logger.info(
                f"[ANALYZE-MODEL-DATA] [LLM-OUTPUT] 响应长度: {response_length} 字符，工具调用数: {tool_calls_count}"
            )

            return {**state, "messages": [response]}
        except Exception as e:
            error_msg = f"生成分析报告失败: {e!s}"
            logger.exception("[ANALYZE-MODEL-DATA] [ERROR] 生成分析报告失败")
            return {**state, "messages": [AIMessage(content=error_msg)]}

    def _build_initial_state(self, session_id: str, message: str) -> dict[str, Any]:
        """构建初始状态

        Args:
            session_id: 会话ID
            message: 用户消息

        Returns:
            初始状态字典
        """
        human_message = HumanMessage(content=message)
        return {
            "messages": [],
            "user_input": human_message,
            "session_id": session_id,
            "user_id": self.user_id,
            "model_info": None,
        }

    def _get_workflow_config(self) -> dict[str, Any]:
        """获取工作流配置

        Returns:
            工作流配置字典，包含 recursion_limit
        """
        return {"recursion_limit": 100}
