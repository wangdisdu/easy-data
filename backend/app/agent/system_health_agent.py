"""
SystemHealthAgent - 系统健康检查Agent
使用LangGraph实现，专门处理系统健康检查任务
"""

from typing import Annotated, Any, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.agent.agent_utils import setup_langsmith_tracing
from app.agent.base_agent import BaseAgent
from app.agent.system_health_agent_prompts import SYSTEM_HEALTH_AGENT_PROMPT
from app.core.logging import get_logger
from app.tool import (
    tool_check_data_source_connection,
    tool_check_data_source_has_models,
    tool_check_data_sources_basic_info,
    tool_check_models_exist_in_database,
    tool_check_models_semantic,
    tool_check_semantic_freshness,
    tool_list_data_source,
)

logger = get_logger("system_health_agent")

# 在模块加载时设置 LangSmith 追踪
setup_langsmith_tracing()


class SystemHealthAgentState(TypedDict):
    """系统健康检查Agent状态定义"""

    messages: Annotated[list[BaseMessage], add_messages]  # 所有历史消息
    user_input: HumanMessage  # 用户输入
    session_id: str
    user_id: Optional[int]


class SystemHealthAgent(BaseAgent):
    """系统健康检查Agent，使用LangGraph实现"""

    def __init__(self, user_id: Optional[int] = None):
        super().__init__(user_id=user_id)

        # 定义工具
        self.tools = [
            tool_list_data_source,
            tool_check_data_sources_basic_info,
            tool_check_data_source_connection,
            tool_check_data_source_has_models,
            tool_check_models_exist_in_database,
            tool_check_models_semantic,
            tool_check_semantic_freshness,
        ]

        # 绑定工具到LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # 创建工具节点
        self.tool_node = ToolNode(self.tools)

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
        """构建LangGraph工作流"""
        workflow = StateGraph(SystemHealthAgentState)

        # 添加节点
        workflow.add_node("llm", self._llm_node)
        workflow.add_node("tools", self.tool_node)

        # 设置入口点
        workflow.set_entry_point("llm")

        # 添加条件边：根据消息类型决定下一步
        workflow.add_conditional_edges(
            "llm", self._should_continue, {"continue": "tools", "end": END}
        )

        # 工具执行后返回agent节点
        workflow.add_edge("tools", "llm")

        # 编译工作流
        graph = workflow.compile()
        print(graph.get_graph().draw_mermaid())
        return graph

    async def _llm_node(self, state: SystemHealthAgentState) -> SystemHealthAgentState:
        """Agent节点：处理消息并决定是否调用工具"""
        try:
            user_input = state["user_input"]

            # 获取历史消息
            his_messages = state.get("messages", [])

            # 构建消息列表：系统提示词 + 用户输入 + 历史消息
            messages = [
                SystemMessage(content=SYSTEM_HEALTH_AGENT_PROMPT),
                user_input,
                *his_messages,
            ]

            logger.info(f"[LLM-MESSAGES] {messages}")
            # 调用LLM（带工具绑定）
            response = await self.llm_with_tools.ainvoke(messages)

            # 返回新状态，添加AI响应
            return {**state, "messages": [*his_messages, response]}
        except Exception as e:
            error_msg = f"处理消息失败: {e!s}"
            logger.exception("处理消息失败")
            return {**state, "messages": [AIMessage(content=error_msg)]}

    def _should_continue(self, state: SystemHealthAgentState) -> str:
        """判断是否继续执行工具"""
        messages = state["messages"]
        if not messages:
            return "end"
        last_message = messages[-1]

        # 如果最后一条消息包含工具调用，则继续执行工具
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
        else:
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
