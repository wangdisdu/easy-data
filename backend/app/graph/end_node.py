"""
End 节点 Builder
"""

from langgraph.graph import StateGraph

from app.services.agents_service import AgentGraphNodeModel


def build_end_node(node: AgentGraphNodeModel, node_name: str, workflow: StateGraph) -> None:
    """
    构建 end 节点

    Args:
        node: 节点模型
        node_name: 节点名称
        workflow: LangGraph 工作流
    """

    async def end_node_func(state):
        return state

    workflow.add_node(node_name, end_node_func)
