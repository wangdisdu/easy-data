"""
智能体管理API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.biz_error import BizError, BizErrorCode
from app.core.logging import get_logger
from app.core.models import PagedResp, Resp
from app.dao.database import get_db
from app.services.agents_service import (
    AgentCreate,
    AgentGraphModel,
    AgentResponse,
    AgentService,
    AgentUpdate,
)

logger = get_logger(__name__)

router = APIRouter()


@router.post("/agents", response_model=Resp[AgentResponse])
async def create_agent(
    agent_data: AgentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """创建智能体"""
    new_agent = AgentService.create_agent(
        db=db, agent_data=agent_data, create_user_id=current_user.id
    )
    return Resp(data=new_agent)


@router.get("/agents", response_model=PagedResp[AgentResponse])
async def get_agents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取智能体列表"""
    agents, total = AgentService.get_agents(db=db, skip=skip, limit=limit)
    return PagedResp(data=agents, total=total)


@router.get("/agents/{agent_id}", response_model=Resp[AgentResponse])
async def get_agent(
    agent_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """获取智能体详情"""
    agent = AgentService.get_agent_by_id(db=db, agent_id=agent_id)
    if not agent:
        raise BizError(BizErrorCode.AGENT_NOT_EXIST, "智能体不存在")
    return Resp(data=agent)


@router.put("/agents/{agent_id}", response_model=Resp[AgentResponse])
async def update_agent(
    agent_id: int,
    agent_update: AgentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """更新智能体"""
    agent = AgentService.update_agent(
        db=db,
        agent_id=agent_id,
        agent_update=agent_update,
        update_user_id=current_user.id,
    )
    return Resp(data=agent)


@router.delete("/agents/{agent_id}", response_model=Resp[AgentResponse])
async def delete_agent(
    agent_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """删除智能体"""
    agent = AgentService.delete_agent(db=db, agent_id=agent_id)
    return Resp(data=agent)


# ========== 智能体图形管理 ==========


@router.get("/agents/{agent_id}/graph", response_model=Resp[AgentGraphModel])
async def get_agent_graph(
    agent_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """获取智能体的完整图形数据（节点和边）"""
    graph_data = AgentService.get_agent_graph(db=db, agent_id=agent_id)
    return Resp(data=graph_data)


@router.post("/agents/{agent_id}/graph", response_model=Resp[AgentGraphModel])
async def save_agent_graph(
    agent_id: int,
    graph_data: AgentGraphModel,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """统一保存智能体的节点和边"""
    result = AgentService.save_agent_graph(
        db=db,
        agent_id=agent_id,
        graph=graph_data,
        update_user_id=current_user.id,
    )
    return Resp(data=result)
