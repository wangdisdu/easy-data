"""
工具管理服务层
"""

import time
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.biz_error import BizError, BizErrorCode
from app.core.logging import get_logger
from app.dao.models import TbTool

logger = get_logger(__name__)


class ToolCreate(BaseModel):
    """工具创建模型"""

    tool: str
    description: Optional[str] = None
    parameters: Optional[str] = None
    content: Optional[str] = None
    extend: Optional[str] = None


class ToolUpdate(BaseModel):
    """工具更新模型"""

    tool: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[str] = None
    content: Optional[str] = None
    extend: Optional[str] = None


class ToolResponse(BaseModel):
    """工具响应模型"""

    id: int
    tool: str
    description: Optional[str] = None
    parameters: Optional[str] = None
    content: Optional[str] = None
    extend: Optional[str] = None
    create_time: int
    update_time: int

    class Config:
        from_attributes = True


class ToolService:
    """工具服务"""

    @staticmethod
    def create_tool(db: Session, tool_data: ToolCreate, create_user_id: int) -> TbTool:
        """
        创建工具

        Args:
            db: 数据库会话
            tool_data: 工具创建数据
            create_user_id: 创建用户ID

        Returns:
            创建的工具对象

        Raises:
            BizError: 如果工具名称已存在
        """
        # 检查工具函数名是否已存在
        existing = db.query(TbTool).filter(TbTool.tool == tool_data.tool).first()
        if existing:
            raise BizError(BizErrorCode.TOOL_NAME_EXISTS, "工具函数名已存在")

        current_time = int(time.time() * 1000)
        new_tool = TbTool(
            tool=tool_data.tool,
            description=tool_data.description,
            parameters=tool_data.parameters,
            content=tool_data.content,
            extend=tool_data.extend,
            create_time=current_time,
            update_time=current_time,
            create_user=create_user_id,
        )

        db.add(new_tool)
        db.commit()
        db.refresh(new_tool)

        return new_tool

    @staticmethod
    def get_tools(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[TbTool], int]:
        """
        获取工具列表

        Args:
            db: 数据库会话
            skip: 跳过记录数
            limit: 限制记录数

        Returns:
            （工具列表，总记录数）
        """
        tools = db.query(TbTool).offset(skip).limit(limit).all()
        total = db.query(TbTool).count()
        return tools, total

    @staticmethod
    def get_tool_by_id(db: Session, tool_id: int) -> Optional[TbTool]:
        """
        根据ID获取工具

        Args:
            db: 数据库会话
            tool_id: 工具ID

        Returns:
            工具对象，如果不存在返回None
        """
        tool = db.query(TbTool).filter(TbTool.id == tool_id).first()
        return tool

    @staticmethod
    def update_tool(
        db: Session, tool_id: int, tool_update: ToolUpdate, update_user_id: int
    ) -> TbTool:
        """
        更新工具

        Args:
            db: 数据库会话
            tool_id: 工具ID
            tool_update: 工具更新数据
            update_user_id: 更新用户ID

        Returns:
            更新后的工具对象

        Raises:
            BizError: 如果工具不存在
        """
        tool = db.query(TbTool).filter(TbTool.id == tool_id).first()
        if not tool:
            raise BizError(BizErrorCode.TOOL_NOT_EXIST, "工具不存在")

        current_time = int(time.time() * 1000)

        if tool_update.tool is not None:
            # 检查新工具函数名是否已存在
            existing = (
                db.query(TbTool)
                .filter(TbTool.tool == tool_update.tool, TbTool.id != tool_id)
                .first()
            )
            if existing:
                raise BizError(BizErrorCode.TOOL_NAME_EXISTS, "工具函数名已存在")
            tool.tool = tool_update.tool
        if tool_update.description is not None:
            tool.description = tool_update.description
        if tool_update.parameters is not None:
            tool.parameters = tool_update.parameters
        if tool_update.content is not None:
            tool.content = tool_update.content
        if tool_update.extend is not None:
            tool.extend = tool_update.extend

        tool.update_time = current_time
        tool.update_user = update_user_id

        db.commit()
        db.refresh(tool)
        return tool

    @staticmethod
    def delete_tool(db: Session, tool_id: int) -> TbTool:
        """
        删除工具

        注意：如果工具被智能体使用，需要先解除关联

        Args:
            db: 数据库会话
            tool_id: 工具ID

        Returns:
            被删除的工具对象

        Raises:
            BizError: 如果工具不存在或工具被智能体使用
        """
        tool = db.query(TbTool).filter(TbTool.id == tool_id).first()
        if not tool:
            raise BizError(BizErrorCode.TOOL_NOT_EXIST, "工具不存在")

        # 注意：由于已移除 TbAgentTool，不再需要检查智能体关联

        db.delete(tool)
        db.commit()
        return tool
