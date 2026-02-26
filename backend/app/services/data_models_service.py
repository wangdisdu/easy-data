"""
数据模型服务层
"""

import time
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.biz_error import BizError, BizErrorCode
from app.dao.models import TbDataModel
from app.services.workspace_relation_service import WorkSpaceRelationService


class DataModelCreate(BaseModel):
    """数据模型创建模型"""

    code: str
    name: str
    platform: str
    type: Optional[str] = None  # 模型类型:table-表，view-视图
    ds_id: Optional[int] = None
    semantic: Optional[str] = None
    summary: Optional[str] = None
    knowledge: Optional[str] = None
    description: Optional[str] = None
    extend: Optional[str] = None
    workspace_ids: Optional[list[int]] = None


class DataModelUpdate(BaseModel):
    """数据模型更新模型"""

    name: Optional[str] = None
    platform: Optional[str] = None
    type: Optional[str] = None  # 模型类型:table-表，view-视图
    ds_id: Optional[int] = None
    semantic: Optional[str] = None
    summary: Optional[str] = None
    knowledge: Optional[str] = None
    description: Optional[str] = None
    extend: Optional[str] = None
    workspace_ids: Optional[list[int]] = None


class DataModelResponse(BaseModel):
    """数据模型响应模型"""

    id: int
    code: str
    name: str
    platform: str
    type: Optional[str] = None  # 模型类型:table-表，view-视图
    ds_id: Optional[int] = None
    semantic: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    extend: Optional[str] = None
    create_time: int
    update_time: int
    workspace_ids: Optional[list[int]] = None

    class Config:
        from_attributes = True


class DataModelService:
    """数据模型服务"""

    @staticmethod
    def create_data_model(
        db: Session, data_model_data: DataModelCreate, create_user_id: int
    ) -> TbDataModel:
        """
        创建数据模型

        Args:
            db: 数据库会话
            data_model_data: 数据模型创建数据
            create_user_id: 创建用户ID

        Returns:
            创建的数据模型对象

        Raises:
            ValueError: 如果数据模型编码已存在
        """
        # 检查编码是否已存在
        existing = db.query(TbDataModel).filter(TbDataModel.code == data_model_data.code).first()
        if existing:
            raise BizError(BizErrorCode.DATAMODEL_CODE_EXISTS, "数据模型编码已存在")

        current_time = int(time.time() * 1000)
        new_data_model = TbDataModel(
            code=data_model_data.code,
            name=data_model_data.name,
            platform=data_model_data.platform,
            type=data_model_data.type,
            ds_id=data_model_data.ds_id,
            semantic=data_model_data.semantic,
            summary=data_model_data.summary,
            knowledge=data_model_data.knowledge,
            description=data_model_data.description,
            extend=data_model_data.extend,
            create_time=current_time,
            update_time=current_time,
            create_user=create_user_id,
        )

        db.add(new_data_model)
        db.commit()
        db.refresh(new_data_model)

        # 关联工作空间
        if data_model_data.workspace_ids:
            WorkSpaceRelationService.set_resource_workspaces(
                db=db,
                resource_type="data_model",
                resource_id=new_data_model.id,
                workspace_ids=data_model_data.workspace_ids,
            )

        return new_data_model

    @staticmethod
    def get_data_models(
        db: Session, skip: int = 0, limit: int = 100
    ) -> tuple[list[TbDataModel], int]:
        """
        获取数据模型列表

        Args:
            db: 数据库会话
            skip: 跳过记录数
            limit: 限制记录数

        Returns:
            （数据模型列表，总记录数）
        """
        data_models = db.query(TbDataModel).offset(skip).limit(limit).all()
        total = db.query(TbDataModel).count()
        return data_models, total

    @staticmethod
    def get_data_model_by_id(
        db: Session, data_model_id: int, include_workspaces: bool = False
    ) -> Optional[TbDataModel]:
        """
        根据ID获取数据模型

        Args:
            db: 数据库会话
            data_model_id: 数据模型ID
            include_workspaces: 是否包含关联的工作空间ID列表

        Returns:
            数据模型对象，如果不存在返回None
        """
        data_model = db.query(TbDataModel).filter(TbDataModel.id == data_model_id).first()
        if data_model and include_workspaces:
            # 获取关联的工作空间ID列表
            workspace_ids = WorkSpaceRelationService.get_resource_workspaces(
                db=db, resource_type="data_model", resource_id=data_model_id
            )
            # 将workspace_ids添加到对象属性中（注意：这不是数据库字段）
            data_model.workspace_ids = workspace_ids
        return data_model

    @staticmethod
    def update_data_model(
        db: Session, data_model_id: int, data_model_update: DataModelUpdate, update_user_id: int
    ) -> TbDataModel:
        """
        更新数据模型

        Args:
            db: 数据库会话
            data_model_id: 数据模型ID
            data_model_update: 数据模型更新数据
            update_user_id: 更新用户ID

        Returns:
            更新后的数据模型对象

        Raises:
            ValueError: 如果数据模型不存在
        """
        data_model = db.query(TbDataModel).filter(TbDataModel.id == data_model_id).first()
        if not data_model:
            raise BizError(BizErrorCode.DATAMODEL_NOT_EXIST, "数据模型不存在")

        current_time = int(time.time() * 1000)

        if data_model_update.name is not None:
            data_model.name = data_model_update.name
        if data_model_update.platform is not None:
            data_model.platform = data_model_update.platform
        if data_model_update.type is not None:
            data_model.type = data_model_update.type
        if data_model_update.ds_id is not None:
            data_model.ds_id = data_model_update.ds_id
        if data_model_update.semantic is not None:
            data_model.semantic = data_model_update.semantic
        if data_model_update.summary is not None:
            data_model.summary = data_model_update.summary
        if data_model_update.knowledge is not None:
            data_model.knowledge = data_model_update.knowledge
        if data_model_update.description is not None:
            data_model.description = data_model_update.description
        if data_model_update.extend is not None:
            data_model.extend = data_model_update.extend

        data_model.update_time = current_time
        data_model.update_user = update_user_id

        db.commit()

        # 更新工作空间关联
        if data_model_update.workspace_ids is not None:
            WorkSpaceRelationService.set_resource_workspaces(
                db=db,
                resource_type="data_model",
                resource_id=data_model_id,
                workspace_ids=data_model_update.workspace_ids,
            )

        db.refresh(data_model)
        return data_model

    @staticmethod
    def delete_data_model(db: Session, data_model_id: int) -> TbDataModel:
        """
        删除数据模型

        Args:
            db: 数据库会话
            data_model_id: 数据模型ID

        Returns:
            被删除的数据模型对象

        Raises:
            ValueError: 如果数据模型不存在
        """
        data_model = db.query(TbDataModel).filter(TbDataModel.id == data_model_id).first()
        if not data_model:
            raise BizError(BizErrorCode.DATAMODEL_NOT_EXIST, "数据模型不存在")

        # 删除关联的工作空间关系
        WorkSpaceRelationService.delete_resource_relations(
            db=db, resource_type="data_model", resource_id=data_model_id
        )

        db.delete(data_model)
        db.commit()
        return data_model
