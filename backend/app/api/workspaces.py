"""
工作空间管理API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.biz_error import BizError, BizErrorCode
from app.core.models import PagedResp, Resp
from app.dao.database import get_db
from app.services.workspaces_service import (
    WorkSpaceCreate,
    WorkSpaceResponse,
    WorkSpaceService,
    WorkSpaceUpdate,
)

router = APIRouter()


@router.post("/workspaces", response_model=Resp[WorkSpaceResponse])
async def create_workspace(
    workspace_data: WorkSpaceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """创建工作空间"""
    new_workspace = WorkSpaceService.create_workspace(
        db=db, workspace_data=workspace_data, create_user_id=current_user.id
    )
    return Resp(data=new_workspace)


@router.get("/workspaces", response_model=PagedResp[WorkSpaceResponse])
async def get_workspaces(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取工作空间列表"""
    workspaces, total = WorkSpaceService.get_workspaces(db=db, skip=skip, limit=limit)
    return PagedResp(data=workspaces, total=total)


@router.get("/workspaces/{workspace_id}", response_model=Resp[WorkSpaceResponse])
async def get_workspace(
    workspace_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """获取工作空间详情"""
    workspace = WorkSpaceService.get_workspace_by_id(db=db, workspace_id=workspace_id)
    if not workspace:
        raise BizError(BizErrorCode.WORKSPACE_NOT_EXIST, "工作空间不存在")
    return Resp(data=workspace)


@router.put("/workspaces/{workspace_id}", response_model=Resp[WorkSpaceResponse])
async def update_workspace(
    workspace_id: int,
    workspace_update: WorkSpaceUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """更新工作空间"""
    workspace = WorkSpaceService.update_workspace(
        db=db,
        workspace_id=workspace_id,
        workspace_update=workspace_update,
        update_user_id=current_user.id,
    )
    return Resp(data=workspace)


@router.delete("/workspaces/{workspace_id}", response_model=Resp[WorkSpaceResponse])
async def delete_workspace(
    workspace_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """删除工作空间"""
    workspace = WorkSpaceService.delete_workspace(db=db, workspace_id=workspace_id)
    return Resp(data=workspace)
