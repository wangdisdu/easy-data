"""
LLM模型管理服务层
"""

import time
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.biz_error import BizError, BizErrorCode
from app.core.logging import get_logger
from app.dao.models import TbLlm

logger = get_logger(__name__)


class LlmCreate(BaseModel):
    """LLM创建模型"""

    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str
    setting: Optional[str] = None
    description: Optional[str] = None
    extend: Optional[str] = None


class LlmUpdate(BaseModel):
    """LLM更新模型"""

    provider: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    setting: Optional[str] = None
    description: Optional[str] = None
    extend: Optional[str] = None


class LlmResponse(BaseModel):
    """LLM响应模型"""

    id: int
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str
    setting: Optional[str] = None
    description: Optional[str] = None
    extend: Optional[str] = None
    create_time: int
    update_time: int

    class Config:
        from_attributes = True


class LlmService:
    """LLM服务"""

    @staticmethod
    def create_llm(db: Session, llm_data: LlmCreate, create_user_id: int) -> TbLlm:
        """
        创建LLM模型

        Args:
            db: 数据库会话
            llm_data: LLM创建数据
            create_user_id: 创建用户ID

        Returns:
            创建的LLM对象
        """
        current_time = int(time.time() * 1000)
        new_llm = TbLlm(
            provider=llm_data.provider,
            api_key=llm_data.api_key,
            base_url=llm_data.base_url,
            model=llm_data.model,
            setting=llm_data.setting,
            description=llm_data.description,
            extend=llm_data.extend,
            create_time=current_time,
            update_time=current_time,
            create_user=create_user_id,
        )

        db.add(new_llm)
        db.commit()
        db.refresh(new_llm)

        return new_llm

    @staticmethod
    def get_llms(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[TbLlm], int]:
        """
        获取LLM列表

        Args:
            db: 数据库会话
            skip: 跳过记录数
            limit: 限制记录数

        Returns:
            （LLM列表，总记录数）
        """
        llms = db.query(TbLlm).offset(skip).limit(limit).all()
        total = db.query(TbLlm).count()
        return llms, total

    @staticmethod
    def get_llm_by_id(db: Session, llm_id: int) -> Optional[TbLlm]:
        """
        根据ID获取LLM

        Args:
            db: 数据库会话
            llm_id: LLM ID

        Returns:
            LLM对象，如果不存在返回None
        """
        llm = db.query(TbLlm).filter(TbLlm.id == llm_id).first()
        return llm

    @staticmethod
    def update_llm(
        db: Session, llm_id: int, llm_update: LlmUpdate, update_user_id: int | None = None
    ) -> TbLlm:
        """
        更新LLM

        Args:
            db: 数据库会话
            llm_id: LLM ID
            llm_update: LLM更新数据
            update_user_id: 更新用户ID

        Returns:
            更新后的LLM对象

        Raises:
            BizError: 如果LLM不存在
        """
        llm = db.query(TbLlm).filter(TbLlm.id == llm_id).first()
        if not llm:
            raise BizError(BizErrorCode.LLM_NOT_EXIST, "LLM模型不存在")

        current_time = int(time.time() * 1000)

        if llm_update.provider is not None:
            llm.provider = llm_update.provider
        if llm_update.api_key is not None:
            llm.api_key = llm_update.api_key
        if llm_update.base_url is not None:
            llm.base_url = llm_update.base_url
        if llm_update.model is not None:
            llm.model = llm_update.model
        if llm_update.setting is not None:
            llm.setting = llm_update.setting
        if llm_update.description is not None:
            llm.description = llm_update.description
        if llm_update.extend is not None:
            llm.extend = llm_update.extend

        llm.update_time = current_time
        llm.update_user = update_user_id

        db.commit()
        db.refresh(llm)
        return llm

    @staticmethod
    def delete_llm(db: Session, llm_id: int) -> TbLlm:
        """
        删除LLM

        注意：如果LLM被智能体使用，需要先解除关联

        Args:
            db: 数据库会话
            llm_id: LLM ID

        Returns:
            被删除的LLM对象

        Raises:
            BizError: 如果LLM不存在或LLM被智能体使用
        """
        llm = db.query(TbLlm).filter(TbLlm.id == llm_id).first()
        if not llm:
            raise BizError(BizErrorCode.LLM_NOT_EXIST, "LLM模型不存在")

        # 注意：由于TbAgent已移除llm_id字段，不再需要检查智能体关联

        db.delete(llm)
        db.commit()
        return llm
