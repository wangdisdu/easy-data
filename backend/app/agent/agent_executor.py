"""
智能体执行服务
将保存的智能体节点和边转换为 LangGraph 并执行（流式）
"""

import json
from typing import Annotated, Any, Optional, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from sqlalchemy.orm import Session

from app.agent.agent_utils import setup_langsmith_tracing
from app.agent.base_agent import BaseAgent
from app.core.biz_error import BizError, BizErrorCode
from app.core.logging import get_logger
from app.dao.models import TbAgent
from app.graph import (
    build_condition_node,
    build_end_node,
    build_llm_node,
    build_python_node,
    build_start_node,
    build_tool_node,
)
from app.service.agent_service import (
    AgentGraphModel,
    AgentGraphNodeModel,
    AgentService,
    SubgraphNodeConfig,
)

logger = get_logger(__name__)

# 在模块加载时设置 LangSmith 追踪
setup_langsmith_tracing()


# 固定的状态定义
class AgentState(TypedDict):
    """智能体状态定义"""

    messages: Annotated[list[BaseMessage], add_messages]
    session_id: str
    user_id: Optional[int]
    data: dict[str, Any]


class AgentExecutor(BaseAgent):
    """智能体执行器"""

    def __init__(self, db: Session, agent_id: int, user_id: Optional[int] = None):
        """初始化执行服务

        Args:
            db: 数据库会话
            agent_id: 智能体ID
            user_id: 用户ID
        """
        # 调用父类初始化
        super().__init__(user_id=user_id)

        self.db = db
        self.agent_id = agent_id

        # 执行器状态
        self.agent: Optional[TbAgent] = None
        self.graph_data: Optional[AgentGraphModel] = None
        self.node_map: dict[int, AgentGraphNodeModel] = {}
        self.node_name_map: dict[int, str] = {}
        self.graph: Optional[Any] = None

    def _load_agent_data(self) -> None:
        """加载智能体数据"""
        # 获取智能体信息
        self.agent = self.db.query(TbAgent).filter(TbAgent.id == self.agent_id).first()
        if not self.agent:
            raise BizError(BizErrorCode.AGENT_NOT_EXIST, "智能体不存在")

        # 获取节点和边
        self.graph_data = AgentService.get_agent_graph(db=self.db, agent_id=self.agent_id)

        if not self.graph_data.nodes:
            raise BizError(BizErrorCode.INVALID_PARAM, "智能体没有节点")

        # 构建节点映射
        self.node_map = {node.id: node for node in self.graph_data.nodes}

    def _add_subgraph_node(
        self,
        node: AgentGraphNodeModel,
        node_name: str,
        workflow: StateGraph,
    ) -> None:
        """将子图智能体作为节点加入 workflow。"""
        try:
            config_dict = json.loads(node.config or "{}")
            config = SubgraphNodeConfig(**config_dict)
        except Exception as e:
            raise BizError(BizErrorCode.INVALID_PARAM, f"节点 {node.id} 配置格式错误: {e}") from e
        if not config.agent_id:
            raise BizError(BizErrorCode.INVALID_PARAM, f"节点 {node.id} 未配置子图智能体")
        executor = AgentExecutor(self.db, config.agent_id, self.user_id)
        subgraph = executor.build()
        workflow.add_node(node_name, subgraph)

    def _add_nodes_to_workflow(self, workflow: StateGraph) -> None:
        """添加所有节点到工作流（condition 不占节点，只通过 add_conditional_edges 挂到前驱节点）"""
        for node in self.graph_data.nodes:
            self.node_name_map[node.id] = f"{node.node_type}_node_{node.id}"

        for node in self.graph_data.nodes:
            node_name = self.node_name_map[node.id]

            if node.node_type == "start":
                build_start_node(node, node_name, workflow)
            elif node.node_type == "end":
                build_end_node(node, node_name, workflow)
            elif node.node_type == "llm":
                build_llm_node(node, node_name, workflow, self.db, self.node_name_map)
            elif node.node_type == "tool":
                build_tool_node(node, node_name, workflow, self.db)
            elif node.node_type == "python":
                build_python_node(node, node_name, workflow)
            elif node.node_type == "condition":
                build_condition_node(node, workflow, self.graph_data.edges, self.node_name_map)
            elif node.node_type == "subgraph":
                self._add_subgraph_node(node, node_name, workflow)

    def _set_start_node(self, workflow: StateGraph) -> None:
        """查找起始节点"""
        start_nodes = [n for n in self.graph_data.nodes if n.node_type == "start"]
        if not start_nodes:
            raise BizError(BizErrorCode.INVALID_PARAM, "智能体没有起始节点")
        if len(start_nodes) > 1:
            raise BizError(BizErrorCode.INVALID_PARAM, "智能体有多个起始节点")
        start_node = start_nodes[0]
        workflow.set_entry_point(self.node_name_map[start_node.id])

    def _add_regular_edges(self, workflow: StateGraph) -> None:
        """添加普通边（跳过从/到 condition 的边，condition 不占节点由 add_conditional_edges 处理）"""
        for edge in self.graph_data.edges:
            from_name = self.node_name_map.get(edge.from_node_id)
            to_name = self.node_name_map.get(edge.to_node_id)

            if not from_name or not to_name:
                continue

            from_node = self.node_map[edge.from_node_id]
            to_node = self.node_map.get(edge.to_node_id)
            if from_node.node_type == "condition":
                continue
            if to_node and to_node.node_type == "condition":
                continue
            workflow.add_edge(from_name, to_name)

    def _add_end_edges(self, workflow: StateGraph) -> None:
        """添加 end 节点到 END 的边"""
        end_nodes = [n for n in self.graph_data.nodes if n.node_type == "end"]
        for end_node in end_nodes:
            end_name = self.node_name_map[end_node.id]
            workflow.add_edge(end_name, END)

    def _build_workflow(self):
        """构建 LangGraph 工作流，返回编译后的图（Runnable），供执行或作为子图节点使用。"""
        workflow = StateGraph(AgentState)

        # 添加所有节点
        self._add_nodes_to_workflow(workflow)

        # 设置入口点
        self._set_start_node(workflow)
        # 添加边（condition 条件边已在 build_condition_node 内 add_conditional_edges）
        self._add_regular_edges(workflow)
        self._add_end_edges(workflow)

        # 编译工作流（子图节点需传入 compiled graph，故返回编译后的图）
        self.graph = workflow.compile()
        print(self.graph.get_graph().draw_mermaid())

        # 设置 workflow 供 BaseAgent 使用
        self.workflow = self.graph

        # 检查是否有子图节点
        self.has_subgraphs = any(node.node_type == "subgraph" for node in self.graph_data.nodes)
        return self.graph

    def _build_initial_state(self, session_id: str, message: str) -> dict[str, Any]:
        """构建初始状态

        Args:
            session_id: 会话ID
            message: 用户消息

        Returns:
            初始状态字典
        """
        return {
            "messages": [HumanMessage(content=message)],
            "session_id": session_id,
            "user_id": self.user_id,
            "data": {},
        }

    def build(self):
        """构建执行器（加载数据和工作流），返回编译后的图。

        这是一个便捷方法，合并了 _load_agent_data 和 _build_workflow。
        返回值可作为顶层 workflow 或作为子图传入 add_node。
        """
        self._load_agent_data()
        return self._build_workflow()
