"""
工具管理API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.biz_error import BizError, BizErrorCode
from app.core.models import PagedResp, Resp
from app.dao.database import get_db
from app.service.tool_service import ToolCreate, ToolResponse, ToolService, ToolUpdate

router = APIRouter()


@router.post("/tools", response_model=Resp[ToolResponse])
async def create_tool(
    tool_data: ToolCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """创建工具"""
    new_tool = ToolService.create_tool(db=db, tool_data=tool_data, create_user_id=current_user.id)
    return Resp(data=new_tool)


@router.get("/tools", response_model=PagedResp[ToolResponse])
async def get_tools(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取工具列表"""
    tools, total = ToolService.get_tools(db=db, skip=skip, limit=limit)
    return PagedResp(data=tools, total=total)


@router.get("/tools/{tool_id}", response_model=Resp[ToolResponse])
async def get_tool(
    tool_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """获取工具详情"""
    tool = ToolService.get_tool_by_id(db=db, tool_id=tool_id)
    if not tool:
        raise BizError(BizErrorCode.TOOL_NOT_EXIST, "工具不存在")
    return Resp(data=tool)


@router.put("/tools/{tool_id}", response_model=Resp[ToolResponse])
async def update_tool(
    tool_id: int,
    tool_update: ToolUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """更新工具"""
    tool = ToolService.update_tool(
        db=db,
        tool_id=tool_id,
        tool_update=tool_update,
        update_user_id=current_user.id,
    )
    return Resp(data=tool)


@router.delete("/tools/{tool_id}", response_model=Resp[ToolResponse])
async def delete_tool(
    tool_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """删除工具"""
    tool = ToolService.delete_tool(db=db, tool_id=tool_id)
    return Resp(data=tool)
