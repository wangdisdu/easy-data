"""
智能体管理服务层
"""

import time
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.biz_error import BizError, BizErrorCode
from app.core.logging import get_logger
from app.dao.models import TbAgent, TbAgentEdge, TbAgentNode

logger = get_logger(__name__)


class AgentCreate(BaseModel):
    """智能体创建模型"""

    name: str
    description: Optional[str] = None
    config: Optional[str] = None
    status: str = "active"
    extend: Optional[str] = None


class AgentUpdate(BaseModel):
    """智能体更新模型"""

    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[str] = None
    status: Optional[str] = None
    extend: Optional[str] = None


class AgentResponse(BaseModel):
    """智能体响应模型"""

    id: int
    name: str
    description: Optional[str] = None
    config: Optional[str] = None
    status: str
    extend: Optional[str] = None
    create_time: int
    update_time: int

    class Config:
        from_attributes = True


# 节点配置类型定义
class LlmNodeConfig(BaseModel):
    """LLM 节点配置"""

    llm_id: int
    script: Optional[str] = None
    tool_ids: Optional[list[int]] = None


class ConditionNodeConfig(BaseModel):
    """条件分支节点配置"""

    script: str
    route_mapping: list[str]


class ToolNodeConfig(BaseModel):
    """工具节点配置"""

    tool_ids: list[int]


class PythonNodeConfig(BaseModel):
    """处理节点配置"""

    script: str


class SubgraphNodeConfig(BaseModel):
    """子图节点配置"""

    agent_id: int


class AgentGraphNodeModel(BaseModel):
    """图节点模型"""

    id: int
    name: Optional[str] = None
    node_type: str
    config: Optional[str] = None  # JSON 字符串，根据 node_type 解析为对应的配置类型
    description: Optional[str] = None
    extend: Optional[str] = None


class AgentGraphEdgeModel(BaseModel):
    """图边模型"""

    from_node_id: int
    to_node_id: int
    from_node_slot: int = 0
    to_node_slot: int = 0


class AgentGraphModel(BaseModel):
    """图数据模型"""

    nodes: list[AgentGraphNodeModel]
    edges: list[AgentGraphEdgeModel]


class AgentService:
    """智能体服务"""

    @staticmethod
    def create_agent(db: Session, agent_data: AgentCreate, create_user_id: int) -> TbAgent:
        """
        创建智能体

        Args:
            db: 数据库会话
            agent_data: 智能体创建数据
            create_user_id: 创建用户ID

        Returns:
            创建的智能体对象
        """
        current_time = int(time.time() * 1000)
        new_agent = TbAgent(
            name=agent_data.name,
            description=agent_data.description,
            config=agent_data.config,
            status=agent_data.status,
            extend=agent_data.extend,
            create_time=current_time,
            update_time=current_time,
            create_user=create_user_id,
        )

        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)

        return new_agent

    @staticmethod
    def get_agents(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[TbAgent], int]:
        """
        获取智能体列表

        Args:
            db: 数据库会话
            skip: 跳过记录数
            limit: 限制记录数

        Returns:
            （智能体列表，总记录数）
        """
        agents = db.query(TbAgent).offset(skip).limit(limit).all()
        total = db.query(TbAgent).count()
        return agents, total

    @staticmethod
    def get_agent_by_id(db: Session, agent_id: int) -> Optional[TbAgent]:
        """
        根据ID获取智能体

        Args:
            db: 数据库会话
            agent_id: 智能体ID

        Returns:
            智能体对象，如果不存在返回None
        """
        agent = db.query(TbAgent).filter(TbAgent.id == agent_id).first()
        return agent

    @staticmethod
    def update_agent(
        db: Session, agent_id: int, agent_update: AgentUpdate, update_user_id: int
    ) -> TbAgent:
        """
        更新智能体

        Args:
            db: 数据库会话
            agent_id: 智能体ID
            agent_update: 智能体更新数据
            update_user_id: 更新用户ID

        Returns:
            更新后的智能体对象

        Raises:
            BizError: 如果智能体不存在
        """
        agent = db.query(TbAgent).filter(TbAgent.id == agent_id).first()
        if not agent:
            raise BizError(BizErrorCode.AGENT_NOT_EXIST, "智能体不存在")

        current_time = int(time.time() * 1000)

        if agent_update.name is not None:
            agent.name = agent_update.name
        if agent_update.description is not None:
            agent.description = agent_update.description
        if agent_update.config is not None:
            agent.config = agent_update.config
        if agent_update.status is not None:
            agent.status = agent_update.status
        if agent_update.extend is not None:
            agent.extend = agent_update.extend

        agent.update_time = current_time
        agent.update_user = update_user_id

        db.commit()
        db.refresh(agent)
        return agent

    @staticmethod
    def delete_agent(db: Session, agent_id: int) -> TbAgent:
        """
        删除智能体

        同时删除关联的节点、边和工具关联

        Args:
            db: 数据库会话
            agent_id: 智能体ID

        Returns:
            被删除的智能体对象

        Raises:
            BizError: 如果智能体不存在
        """
        agent = db.query(TbAgent).filter(TbAgent.id == agent_id).first()
        if not agent:
            raise BizError(BizErrorCode.AGENT_NOT_EXIST, "智能体不存在")

        # 删除关联的节点
        db.query(TbAgentNode).filter(TbAgentNode.agent_id == agent_id).delete()

        # 删除关联的边
        db.query(TbAgentEdge).filter(TbAgentEdge.agent_id == agent_id).delete()

        db.delete(agent)
        db.commit()
        return agent

    @staticmethod
    def get_agent_graph(db: Session, agent_id: int) -> AgentGraphModel:
        """
        获取智能体的完整图形数据（节点和边）

        Args:
            db: 数据库会话
            agent_id: 智能体ID

        Returns:
            包含节点和边的字典
        """
        nodes = (
            db.query(TbAgentNode)
            .filter(TbAgentNode.agent_id == agent_id)
            .order_by(TbAgentNode.id.asc())
            .all()
        )
        edges = (
            db.query(TbAgentEdge)
            .filter(TbAgentEdge.agent_id == agent_id)
            .order_by(TbAgentEdge.id.asc())
            .all()
        )
        node_ids = {n.id for n in nodes}

        return AgentGraphModel(
            nodes=[
                AgentGraphNodeModel(
                    id=n.id,
                    name=n.name,
                    node_type=n.node_type,
                    config=n.config,
                    description=n.description,
                    extend=n.extend,
                )
                for n in nodes
            ],
            edges=[
                AgentGraphEdgeModel(
                    from_node_id=e.from_node_id,
                    to_node_id=e.to_node_id,
                    from_node_slot=e.from_node_slot,
                    to_node_slot=e.to_node_slot,
                )
                for e in edges
                if e.from_node_id in node_ids and e.to_node_id in node_ids
            ],
        )

    @staticmethod
    def save_agent_graph(
        db: Session,
        agent_id: int,
        graph: AgentGraphModel,
        update_user_id: int,
    ) -> AgentGraphModel:
        """
        统一保存智能体的节点和边

        Args:
            db: 数据库会话
            agent_id: 智能体ID
            graph: 图形数据
            update_user_id: 更新用户ID

        Returns:
            保存结果字典，包含 nodes 和 edges

        Raises:
            BizError: 如果智能体不存在
        """
        # 检查智能体是否存在
        agent = db.query(TbAgent).filter(TbAgent.id == agent_id).first()
        if not agent:
            raise BizError(BizErrorCode.AGENT_NOT_EXIST, "智能体不存在")

        current_time = int(time.time() * 1000)

        # 统一清空该 graph 的所有边和节点（边先删）
        db.query(TbAgentEdge).filter(TbAgentEdge.agent_id == agent_id).delete()
        db.query(TbAgentNode).filter(TbAgentNode.agent_id == agent_id).delete()
        db.flush()

        # 插入节点，建立请求 id -> 新 DB id 的映射
        id_map: dict[int, int] = {}
        for n in graph.nodes:
            node = TbAgentNode(
                agent_id=agent_id,
                name=n.name or None,
                node_type=n.node_type,
                config=n.config or None,
                description=n.description or None,
                extend=n.extend or None,
                create_time=current_time,
                update_time=current_time,
                create_user=update_user_id,
                update_user=update_user_id,
            )
            db.add(node)
            db.flush()
            id_map[n.id] = node.id

        # 插入边
        saved_edges: list[AgentGraphEdgeModel] = []
        for e in graph.edges:
            from_db = id_map.get(e.from_node_id)
            to_db = id_map.get(e.to_node_id)
            if from_db is None or to_db is None:
                continue
            edge = TbAgentEdge(
                agent_id=agent_id,
                from_node_id=from_db,
                from_node_slot=int(e.from_node_slot or 0),
                to_node_id=to_db,
                to_node_slot=int(e.to_node_slot or 0),
                create_time=current_time,
                update_time=current_time,
                create_user=update_user_id,
                update_user=update_user_id,
            )
            db.add(edge)
            saved_edges.append(
                AgentGraphEdgeModel(
                    from_node_id=from_db,
                    to_node_id=to_db,
                    from_node_slot=e.from_node_slot,
                    to_node_slot=e.to_node_slot,
                )
            )

        db.commit()

        return AgentGraphModel(
            nodes=[
                AgentGraphNodeModel(
                    id=id_map[n.id],
                    name=n.name,
                    node_type=n.node_type,
                    config=n.config,
                    description=n.description,
                    extend=n.extend,
                )
                for n in graph.nodes
            ],
            edges=saved_edges,
        )
