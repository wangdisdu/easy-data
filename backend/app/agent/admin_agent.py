"""
AdminAgent - 系统管理智能体
使用LangGraph实现，通过Subgraphs实现多Agent协作
综合子智能体DataSourceAgent、DataModelAgent、DataModelAnalysisAgent三者的能力
"""

from typing import Annotated, Any, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from app.agent.admin_agent_prompts import ADMIN_AGENT_INTENT_PROMPT
from app.agent.agent_utils import setup_langsmith_tracing
from app.agent.base_agent import BaseAgent
from app.agent.data_model_agent import DataModelAgent
from app.agent.data_model_analysis_agent import DataModelAnalysisAgent
from app.agent.data_source_agent import DataSourceAgent
from app.agent.system_health_agent import SystemHealthAgent
from app.core.logging import get_logger

logger = get_logger("admin_agent")

# 在模块加载时设置 LangSmith 追踪
setup_langsmith_tracing()


class AdminAgentState(TypedDict):
    """系统管理Agent状态定义"""

    messages: Annotated[list[BaseMessage], add_messages]  # 所有历史消息
    user_input: HumanMessage  # 用户输入
    session_id: str
    user_id: Optional[int]
    selected_agent: Optional[str]  # 选中的子智能体名称


class AdminAgent(BaseAgent):
    """系统管理智能体，使用LangGraph实现，通过Subgraphs实现多Agent协作"""

    def __init__(self, user_id: Optional[int] = None):
        super().__init__(user_id=user_id)

        # 标记此 Agent 包含子图
        self.has_subgraphs = True

        # 初始化子智能体
        self.data_source_agent = DataSourceAgent(user_id=user_id)
        self.data_model_agent = DataModelAgent(user_id=user_id)
        self.data_model_analysis_agent = DataModelAnalysisAgent(user_id=user_id)
        self.system_health_agent = SystemHealthAgent(user_id=user_id)

        # 构建子图
        self.data_source_agent_graph = self.data_source_agent.build_subgraph()
        self.data_model_agent_graph = self.data_model_agent.build_subgraph()
        self.data_model_analysis_agent_graph = self.data_model_analysis_agent.build_subgraph()
        self.system_health_agent_graph = self.system_health_agent.build_subgraph()

        # 构建LangGraph工作流
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """
        构建LangGraph工作流，使用Subgraphs实现多Agent协作

        参考示例代码，将子图作为节点添加到主图中，在节点中调用子图的 invoke/ainvoke

        Returns:
            StateGraph: 编译后的工作流图
        """
        workflow = StateGraph(AdminAgentState)

        # 添加节点
        workflow.add_node("intent_analysis", self._intent_analysis_node)
        workflow.add_node("data_source_agent", self.data_source_agent_graph)
        workflow.add_node("data_model_agent", self.data_model_agent_graph)
        workflow.add_node("data_model_analysis_agent", self.data_model_analysis_agent_graph)
        workflow.add_node("system_health_agent", self.system_health_agent_graph)

        # 设置入口点
        workflow.set_entry_point("intent_analysis")

        # 意图分析后，根据选择的子智能体路由
        workflow.add_conditional_edges(
            "intent_analysis",
            self._route_after_intent,
            {
                "data_source": "data_source_agent",
                "data_model": "data_model_agent",
                "data_model_analysis": "data_model_analysis_agent",
                "system_health": "system_health_agent",
                "end": END,
            },
        )

        # 所有子智能体执行完成后，直接结束
        workflow.add_edge("data_source_agent", END)
        workflow.add_edge("data_model_agent", END)
        workflow.add_edge("data_model_analysis_agent", END)
        workflow.add_edge("system_health_agent", END)

        # 编译工作流
        graph = workflow.compile()
        print(graph.get_graph().draw_mermaid())
        return graph

    async def _intent_analysis_node(self, state: AdminAgentState) -> AdminAgentState:
        """
        意图分析节点：根据用户问题判断应该由哪个子智能体处理

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        try:
            user_input = state.get("user_input")
            his_messages = state.get("messages", [])

            # 构建消息列表（系统提示词 + 用户输入 + 历史消息）
            messages = [
                SystemMessage(content=ADMIN_AGENT_INTENT_PROMPT),
                user_input,
                *his_messages,
            ]

            logger.info(f"[ADMIN-INTENT] [LLM-INPUT] 用户问题: {user_input.content[:100]}...")

            # 使用LLM分析意图
            response = await self.llm.ainvoke(messages)

            # 从响应中提取选中的子智能体名称
            selected_agent = self._extract_agent_name(response.content)

            logger.info(f"[ADMIN-INTENT] [LLM-OUTPUT] 选中的子智能体: {selected_agent}")

            return {
                **state,
                "selected_agent": selected_agent,
            }
        except Exception as e:
            error_msg = f"意图分析失败: {e!s}"
            logger.exception("[ADMIN-INTENT] [ERROR] 意图分析失败")
            return {
                **state,
                "messages": [
                    *state.get("messages", []),
                    AIMessage(content=error_msg),
                ],
                "selected_agent": None,
            }

    def _extract_agent_name(self, content: str) -> Optional[str]:
        """
        从LLM响应中提取子智能体名称

        Args:
            content: LLM响应内容

        Returns:
            子智能体名称，如果无法识别则返回None
        """
        content_lower = content.lower()
        if "datasourceagent" in content_lower:
            return "data_source"
        elif "datamodelagent" in content_lower:
            return "data_model"
        elif "datamodelanalysisagent" in content_lower:
            return "data_model_analysis"
        elif "systemhealthagent" in content_lower:
            return "system_health"
        else:
            return None

    def _route_after_intent(self, state: AdminAgentState) -> str:
        """
        意图分析后的路由逻辑

        Args:
            state: 当前状态

        Returns:
            下一个节点的名称
        """
        selected_agent = state.get("selected_agent")
        route_map = {
            "data_source": "data_source",
            "data_model": "data_model",
            "data_model_analysis": "data_model_analysis",
            "system_health": "system_health",
        }
        return route_map.get(selected_agent, "end")

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
            "selected_agent": None,
        }
