"""
数据源服务层
"""

import json
import time
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.connector import ConnectorFactory
from app.connector.models import ConnectionTestResult
from app.core.biz_error import BizError, BizErrorCode
from app.core.logging import get_logger
from app.dao.models import TbDataModel, TbDataSource
from app.services.workspace_relation_service import WorkSpaceRelationService

logger = get_logger(__name__)


class DataSourceCreate(BaseModel):
    """数据源创建模型"""

    code: str
    name: str
    platform: str
    setting: str
    semantic: Optional[str] = None
    description: Optional[str] = None
    extend: Optional[str] = None
    workspace_ids: Optional[list[int]] = None


class DataSourceUpdate(BaseModel):
    """数据源更新模型"""

    name: Optional[str] = None
    platform: Optional[str] = None
    setting: Optional[str] = None
    semantic: Optional[str] = None
    description: Optional[str] = None
    extend: Optional[str] = None
    workspace_ids: Optional[list[int]] = None


class DataSourceResponse(BaseModel):
    """数据源响应模型"""

    id: int
    code: str
    name: str
    platform: str
    setting: str
    semantic: Optional[str] = None
    description: Optional[str] = None
    extend: Optional[str] = None
    create_time: int
    update_time: int
    workspace_ids: Optional[list[int]] = None

    class Config:
        from_attributes = True


class DataSourceService:
    """数据源服务"""

    @staticmethod
    def create_data_source(
        db: Session, data_source_data: DataSourceCreate, create_user_id: int
    ) -> TbDataSource:
        """
        创建数据源

        Args:
            db: 数据库会话
            data_source_data: 数据源创建数据
            create_user_id: 创建用户ID

        Returns:
            创建的数据源对象

        Raises:
            ValueError: 如果数据源编码已存在
        """
        # 检查编码是否已存在
        existing = db.query(TbDataSource).filter(TbDataSource.code == data_source_data.code).first()
        if existing:
            raise BizError(BizErrorCode.DATASOURCE_CODE_EXISTS, "数据源编码已存在")

        current_time = int(time.time() * 1000)
        new_data_source = TbDataSource(
            code=data_source_data.code,
            name=data_source_data.name,
            platform=data_source_data.platform,
            setting=data_source_data.setting,
            semantic=data_source_data.semantic,
            description=data_source_data.description,
            extend=data_source_data.extend,
            create_time=current_time,
            update_time=current_time,
            create_user=create_user_id,
        )

        db.add(new_data_source)
        db.commit()
        db.refresh(new_data_source)

        # 关联工作空间
        if data_source_data.workspace_ids:
            WorkSpaceRelationService.set_resource_workspaces(
                db=db,
                resource_type="data_source",
                resource_id=new_data_source.id,
                workspace_ids=data_source_data.workspace_ids,
            )

        return new_data_source

    @staticmethod
    def get_data_sources(
        db: Session, skip: int = 0, limit: int = 100
    ) -> tuple[list[TbDataSource], int]:
        """
        获取数据源列表

        Args:
            db: 数据库会话
            skip: 跳过记录数
            limit: 限制记录数

        Returns:
            （数据源列表，总记录数）
        """
        data_sources = db.query(TbDataSource).offset(skip).limit(limit).all()
        total = db.query(TbDataSource).count()
        return data_sources, total

    @staticmethod
    def get_data_source_by_id(
        db: Session, data_source_id: int, include_workspaces: bool = False
    ) -> Optional[TbDataSource]:
        """
        根据ID获取数据源

        Args:
            db: 数据库会话
            data_source_id: 数据源ID
            include_workspaces: 是否包含关联的工作空间ID列表

        Returns:
            数据源对象，如果不存在返回None
        """
        data_source = db.query(TbDataSource).filter(TbDataSource.id == data_source_id).first()
        if data_source and include_workspaces:
            # 获取关联的工作空间ID列表
            workspace_ids = WorkSpaceRelationService.get_resource_workspaces(
                db=db, resource_type="data_source", resource_id=data_source_id
            )
            # 将workspace_ids添加到对象属性中（注意：这不是数据库字段）
            data_source.workspace_ids = workspace_ids
        return data_source

    @staticmethod
    def update_data_source(
        db: Session, data_source_id: int, data_source_update: DataSourceUpdate, update_user_id: int
    ) -> TbDataSource:
        """
        更新数据源

        Args:
            db: 数据库会话
            data_source_id: 数据源ID
            data_source_update: 数据源更新数据
            update_user_id: 更新用户ID

        Returns:
            更新后的数据源对象

        Raises:
            ValueError: 如果数据源不存在
        """
        data_source = db.query(TbDataSource).filter(TbDataSource.id == data_source_id).first()
        if not data_source:
            raise BizError(BizErrorCode.DATASOURCE_NOT_EXIST, "数据源不存在")

        current_time = int(time.time() * 1000)

        if data_source_update.name is not None:
            data_source.name = data_source_update.name
        if data_source_update.platform is not None:
            data_source.platform = data_source_update.platform
        if data_source_update.setting is not None:
            data_source.setting = data_source_update.setting
        if data_source_update.semantic is not None:
            data_source.semantic = data_source_update.semantic
        if data_source_update.description is not None:
            data_source.description = data_source_update.description
        if data_source_update.extend is not None:
            data_source.extend = data_source_update.extend

        data_source.update_time = current_time
        data_source.update_user = update_user_id

        db.commit()

        # 更新工作空间关联
        if data_source_update.workspace_ids is not None:
            WorkSpaceRelationService.set_resource_workspaces(
                db=db,
                resource_type="data_source",
                resource_id=data_source_id,
                workspace_ids=data_source_update.workspace_ids,
            )

        db.refresh(data_source)
        return data_source

    @staticmethod
    def delete_data_source(db: Session, data_source_id: int) -> TbDataSource:
        """
        删除数据源

        约束：当数据源下存在关联的数据模型时，拒绝删除并提示用户先处理关联模型

        Args:
            db: 数据库会话
            data_source_id: 数据源ID

        Returns:
            被删除的数据源对象

        Raises:
            ValueError: 如果数据源不存在
        """
        data_source = db.query(TbDataSource).filter(TbDataSource.id == data_source_id).first()
        if not data_source:
            raise BizError(BizErrorCode.DATASOURCE_NOT_EXIST, "数据源不存在")

        # 检查是否存在关联的数据模型
        related_model_count = (
            db.query(TbDataModel).filter(TbDataModel.ds_id == data_source_id).count()
        )
        if related_model_count > 0:
            raise BizError(
                BizErrorCode.DATASOURCE_DELETE_ERROR,
                f"数据源下存在 {related_model_count} 个关联的数据模型，无法删除，请先删除关联模型",
            )

        # 删除关联的工作空间关系
        WorkSpaceRelationService.delete_resource_relations(
            db=db, resource_type="data_source", resource_id=data_source_id
        )

        db.delete(data_source)
        db.commit()
        return data_source

    @staticmethod
    def test_data_source_connection(platform: str, setting: str) -> ConnectionTestResult:
        """
        测试数据源连接

        Args:
            platform: 数据库平台类型
            setting: 数据库配置(JSON字符串或字典)

        Returns:
            连接测试结果
        """
        # 解析setting JSON配置
        if isinstance(setting, str):
            try:
                setting_dict = json.loads(setting)
            except json.JSONDecodeError as e:
                return ConnectionTestResult(success=False, message=f"配置解析错误:{e!s}")
        else:
            setting_dict = setting

        # 创建连接器实例
        try:
            connector = ConnectorFactory.create_connector(platform, **setting_dict)
        except Exception as e:
            logger.exception("创建连接器失败")
            return ConnectionTestResult(success=False, message=f"创建连接器失败:{e!s}")

        # 测试连接
        try:
            result = connector.test_connection()
            return result
        except Exception as e:
            logger.exception("测试连接失败")
            return ConnectionTestResult(success=False, message=f"测试连接失败:{e!s}")

    @staticmethod
    def get_data_source_connector(db: Session, data_source_id: int):
        """
        获取数据源的连接器实例

        Args:
            db: 数据库会话
            data_source_id: 数据源ID

        Returns:
            连接器实例

        Raises:
            BizError: 如果数据源不存在或配置错误
        """
        data_source = DataSourceService.get_data_source_by_id(db=db, data_source_id=data_source_id)
        if not data_source:
            raise BizError(BizErrorCode.DATASOURCE_NOT_EXIST, "数据源不存在")

        # 解析setting配置
        try:
            setting = json.loads(data_source.setting)
        except json.JSONDecodeError as e:
            raise BizError(BizErrorCode.DATASOURCE_CONFIG_ERROR, f"数据源配置格式错误:{e!s}") from e

        # 创建连接器实例
        try:
            connector = ConnectorFactory.create_connector(data_source.platform, **setting)
            return connector
        except Exception as e:
            logger.exception("创建连接器失败")
            raise BizError(BizErrorCode.DATASOURCE_CONNECTION_ERROR, f"创建连接器失败:{e!s}") from e

    @staticmethod
    def get_tables_and_views(
        db: Session,
        data_source_id: int,
        database: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> dict:
        """
        获取数据源的表和视图列表

        Args:
            db: 数据库会话
            data_source_id: 数据源ID
            database: 数据库名称（可选）
            schema: Schema名称（可选）

        Returns:
            包含tables和views的字典
        """
        connector = DataSourceService.get_data_source_connector(
            db=db, data_source_id=data_source_id
        )
        try:
            tables = connector.get_tables(database=database, schema=schema)
            views = connector.get_views(database=database, schema=schema)
            return {"tables": tables, "views": views}
        finally:
            connector.close()

    @staticmethod
    def get_table_structure(
        db: Session,
        data_source_id: int,
        table_name: str,
        database: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> list[dict]:
        """
        获取表结构信息

        Args:
            db: 数据库会话
            data_source_id: 数据源ID
            table_name: 表名
            database: 数据库名称（可选）
            schema: Schema名称（可选）

        Returns:
            表结构信息列表
        """
        connector = DataSourceService.get_data_source_connector(
            db=db, data_source_id=data_source_id
        )
        try:
            structure = connector.get_table_structure(
                table_name=table_name, database=database, schema=schema
            )
            return structure
        finally:
            connector.close()

    @staticmethod
    def execute_sql_query(
        db: Session, data_source_id: int, sql: str, params: Optional[dict] = None
    ) -> list[dict]:
        """
        执行SQL查询

        Args:
            db: 数据库会话
            data_source_id: 数据源ID
            sql: SQL查询语句
            params: 查询参数（可选）

        Returns:
            查询结果列表

        Raises:
            BizError: 如果SQL不是SELECT语句或执行失败
        """
        # 验证SQL是否为SELECT语句（简单检查）
        # sql_upper = sql.strip().upper()
        # if not sql_upper.startswith('SELECT'):
        #     raise BizError(BizErrorCode.DATASOURCE_SQL_ERROR, "只支持SELECT查询语句")

        connector = DataSourceService.get_data_source_connector(
            db=db, data_source_id=data_source_id
        )
        try:
            result = connector.execute_query(query=sql, params=params)
            return result
        except Exception as e:
            logger.exception("执行SQL查询失败")
            raise BizError(BizErrorCode.DATASOURCE_SQL_ERROR, f"执行SQL查询失败:{e!s}") from e
        finally:
            connector.close()
