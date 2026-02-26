"""
DataSourceAgent - 数据源管理Agent
使用LangGraph实现，专门处理数据源相关的任务
重构为两个阶段:阶段一识别意图，阶段二主流程
"""

from typing import Annotated, Any, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.agent.agent_utils import setup_langsmith_tracing
from app.agent.base_agent import BaseAgent
from app.agent.data_source_agent_prompts import INTENT_ANALYSIS_PROMPT, MAIN_PROCESS_PROMPT
from app.core.logging import get_logger
from app.tool import (
    tool_create_data_source,
    tool_delete_data_source,
    tool_list_data_source,
    tool_test_data_source,
    tool_update_data_source,
)

logger = get_logger("data_source_agent")

# 在模块加载时设置 LangSmith 追踪
setup_langsmith_tracing()


class DataSourceAgentState(TypedDict):
    """数据源Agent状态定义"""

    messages: Annotated[list[BaseMessage], add_messages]  # 所有历史消息
    user_input: HumanMessage  # 用户输入
    session_id: str
    user_id: Optional[int]


class DataSourceAgent(BaseAgent):
    """数据源管理Agent，使用LangGraph实现"""

    def __init__(self, user_id: Optional[int] = None):
        super().__init__(user_id=user_id)

        # 为不同节点创建专用的llm_with_tool和独立的ToolNode
        # 阶段一:分析意图（只绑定 tool_list_data_source）
        self.llm_intent = self.llm.bind_tools([tool_list_data_source])
        self.tool_node_list_ds = ToolNode([tool_list_data_source])

        # 阶段二:主流程（绑定所有数据源操作工具）
        self.tools_main = [
            tool_test_data_source,
            tool_create_data_source,
            tool_delete_data_source,
            tool_update_data_source,
        ]
        self.llm_main = self.llm.bind_tools(self.tools_main)
        self.tool_node_main = ToolNode(self.tools_main)

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
        1. 阶段一:分析意图，判断是否符合agent能力，获取数据源列表
        2. 阶段二:主流程，支持新增、查询、测试数据源

        Returns:
            StateGraph: 编译后的工作流图
        """
        workflow = StateGraph(DataSourceAgentState)

        # ========== 添加节点 ==========
        # 阶段一:入口阶段节点
        workflow.add_node("analyze_intent", self._analyze_intent_node)
        workflow.add_node("tool_list_ds", self.tool_node_list_ds)

        # 阶段二:主流程节点
        workflow.add_node("main_process", self._process_main_node)
        workflow.add_node("main_tools", self.tool_node_main)

        # 设置入口点
        workflow.set_entry_point("analyze_intent")

        # ========== 工作流连接 ==========
        # 阶段一:分析意图后，如果有工具调用则继续，否则结束
        workflow.add_conditional_edges(
            "analyze_intent",
            self._route_after_intent,
            {
                "can_handle": "tool_list_ds",  # 有工具调用，执行工具
                "cannot_handle": END,  # 无工具调用，结束流程
            },
        )

        # 阶段一:工具执行后，进入主流程
        workflow.add_edge("tool_list_ds", "main_process")

        # 阶段二:主流程循环执行，直到没有工具调用
        workflow.add_conditional_edges(
            "main_process",
            self._should_continue_main,
            {
                "continue": "main_tools",  # 有工具调用，执行工具
                "end": END,  # 没有工具调用，结束流程
            },
        )
        workflow.add_edge("main_tools", "main_process")  # 工具执行后，再次进入主流程

        # 编译工作流
        graph = workflow.compile()
        print(graph.get_graph().draw_mermaid())
        return graph

    async def _analyze_intent_node(self, state: DataSourceAgentState) -> DataSourceAgentState:
        """
        阶段一节点:分析用户意图

        使用tool_list_data_source工具判断用户请求是否符合agent能力:
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
            logger.info(
                f"[INTENT] [LLM-OUTPUT] 响应类型: {type(response).__name__}, 工具调用数: {len(response.tool_calls) if hasattr(response, 'tool_calls') and response.tool_calls else 0}"
            )

            return {**state, "messages": [response]}
        except Exception as e:
            error_msg = f"分析意图失败: {e!s}"
            logger.exception("[INTENT] [ERROR] 分析意图失败")
            return {**state, "messages": [AIMessage(content=error_msg)]}

    def _current_is_tool_call(self, state: DataSourceAgentState) -> bool:
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

    def _route_after_intent(self, state: DataSourceAgentState) -> str:
        """
        阶段一路由:根据LLM响应判断是否符合agent能力

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

    async def _process_main_node(self, state: DataSourceAgentState) -> DataSourceAgentState:
        """
        阶段二节点:主流程处理

        处理新增数据源、查询数据源、测试数据源等操作。
        使用已获取的数据源列表信息（在阶段一已获取）.

        Args:
            state: 当前状态

        Returns:
            更新后的状态，包含LLM的响应消息（可能包含工具调用）
        """
        try:
            # 获取历史消息
            his_messages = state.get("messages", [])

            user_input = state["user_input"]

            # 如果 state 中有数据源列表信息，添加到系统提示词中
            main_prompt = MAIN_PROCESS_PROMPT

            messages = [SystemMessage(content=main_prompt), user_input, *his_messages]

            logger.info(f"[PROCESS-MAIN] [LLM-INPUT] : {messages}")
            response = await self.llm_main.ainvoke(messages)
            tool_calls_count = (
                len(response.tool_calls)
                if hasattr(response, "tool_calls") and response.tool_calls
                else 0
            )
            logger.info(f"[PROCESS-MAIN] [LLM-OUTPUT] 工具调用数: {tool_calls_count}")

            return {**state, "messages": [*his_messages, response]}
        except Exception as e:
            error_msg = f"主流程处理失败: {e!s}"
            logger.exception("[PROCESS-MAIN] [ERROR] 主流程处理失败")
            return {**state, "messages": [AIMessage(content=error_msg)]}

    def _should_continue_main(self, state: DataSourceAgentState) -> str:
        """
        阶段二路由:根据LLM响应判断是否继续执行工具

        Args:
            state: 当前状态

        Returns:
            "continue": 有工具调用，继续执行工具
            "end": 没有工具调用，结束流程
        """
        current_is_tool_call = self._current_is_tool_call(state)

        if current_is_tool_call:
            logger.info("[ROUTE-MAIN] [CONTINUE] 检测到工具调用，继续执行")
            return "continue"
        else:
            logger.info("[ROUTE-MAIN] [END] 未检测到工具调用，结束流程")
            return "end"

    def _build_initial_state(self, session_id: str, message: str) -> dict[str, Any]:
        """构建初始状态

        Args:
            session_id: 会话ID
            message: 用户消息

        Returns:
            初始状态字典
        """
        user_input = HumanMessage(content=message)
        return {
            "messages": [],
            "user_input": user_input,
            "session_id": session_id,
            "user_id": self.user_id,
        }
