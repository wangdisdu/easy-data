"""
工作空间服务层
"""

import time
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.biz_error import BizError, BizErrorCode
from app.dao.models import TbWorkSpace


class WorkSpaceCreate(BaseModel):
    """工作空间创建模型"""

    code: str
    name: str
    description: Optional[str] = None
    extend: Optional[str] = None


class WorkSpaceUpdate(BaseModel):
    """工作空间更新模型"""

    name: Optional[str] = None
    description: Optional[str] = None
    extend: Optional[str] = None


class WorkSpaceResponse(BaseModel):
    """工作空间响应模型"""

    id: int
    code: str
    name: str
    description: Optional[str] = None
    extend: Optional[str] = None
    create_time: int
    update_time: int

    class Config:
        from_attributes = True


class WorkSpaceService:
    """工作空间服务"""

    @staticmethod
    def create_workspace(
        db: Session, workspace_data: WorkSpaceCreate, create_user_id: int
    ) -> TbWorkSpace:
        """
        创建工作空间

        Args:
            db: 数据库会话
            workspace_data: 工作空间创建数据
            create_user_id: 创建用户ID

        Returns:
            创建的工作空间对象

        Raises:
            ValueError: 如果工作空间编码已存在
        """
        # 检查编码是否已存在
        existing = db.query(TbWorkSpace).filter(TbWorkSpace.code == workspace_data.code).first()
        if existing:
            raise BizError(BizErrorCode.WORKSPACE_CODE_EXISTS, "工作空间编码已存在")

        current_time = int(time.time() * 1000)
        new_workspace = TbWorkSpace(
            code=workspace_data.code,
            name=workspace_data.name,
            description=workspace_data.description,
            extend=workspace_data.extend,
            create_time=current_time,
            update_time=current_time,
            create_user=create_user_id,
        )

        db.add(new_workspace)
        db.commit()
        db.refresh(new_workspace)
        return new_workspace

    @staticmethod
    def get_workspaces(
        db: Session, skip: int = 0, limit: int = 100
    ) -> tuple[list[TbWorkSpace], int]:
        """
        获取工作空间列表

        Args:
            db: 数据库会话
            skip: 跳过记录数
            limit: 限制记录数

        Returns:
            （工作空间列表，总记录数）
        """
        workspaces = db.query(TbWorkSpace).offset(skip).limit(limit).all()
        total = db.query(TbWorkSpace).count()
        return workspaces, total

    @staticmethod
    def get_workspace_by_id(db: Session, workspace_id: int) -> Optional[TbWorkSpace]:
        """
        根据ID获取工作空间

        Args:
            db: 数据库会话
            workspace_id: 工作空间ID

        Returns:
            工作空间对象，如果不存在返回None
        """
        return db.query(TbWorkSpace).filter(TbWorkSpace.id == workspace_id).first()

    @staticmethod
    def update_workspace(
        db: Session, workspace_id: int, workspace_update: WorkSpaceUpdate, update_user_id: int
    ) -> TbWorkSpace:
        """
        更新工作空间

        Args:
            db: 数据库会话
            workspace_id: 工作空间ID
            workspace_update: 工作空间更新数据
            update_user_id: 更新用户ID

        Returns:
            更新后的工作空间对象

        Raises:
            ValueError: 如果工作空间不存在
        """
        workspace = db.query(TbWorkSpace).filter(TbWorkSpace.id == workspace_id).first()
        if not workspace:
            raise BizError(BizErrorCode.WORKSPACE_NOT_EXIST, "工作空间不存在")

        current_time = int(time.time() * 1000)

        if workspace_update.name is not None:
            workspace.name = workspace_update.name
        if workspace_update.description is not None:
            workspace.description = workspace_update.description
        if workspace_update.extend is not None:
            workspace.extend = workspace_update.extend

        workspace.update_time = current_time
        workspace.update_user = update_user_id

        db.commit()
        db.refresh(workspace)
        return workspace

    @staticmethod
    def delete_workspace(db: Session, workspace_id: int) -> TbWorkSpace:
        """
        删除工作空间

        Args:
            db: 数据库会话
            workspace_id: 工作空间ID

        Returns:
            被删除的工作空间对象

        Raises:
            ValueError: 如果工作空间不存在
        """
        workspace = db.query(TbWorkSpace).filter(TbWorkSpace.id == workspace_id).first()
        if not workspace:
            raise BizError(BizErrorCode.WORKSPACE_NOT_EXIST, "工作空间不存在")

        db.delete(workspace)
        db.commit()
        return workspace
