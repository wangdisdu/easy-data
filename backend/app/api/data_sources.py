"""
数据源管理API
"""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.connector.models import ConnectionTestResult
from app.core.biz_error import BizError, BizErrorCode
from app.core.models import PagedResp, Resp
from app.dao.database import get_db
from app.service.data_source_service import (
    DataSourceCreate,
    DataSourceResponse,
    DataSourceService,
    DataSourceUpdate,
)

router = APIRouter()


@router.post("/data-sources", response_model=Resp[DataSourceResponse])
async def create_data_source(
    data_source_data: DataSourceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """创建数据源"""
    new_data_source = DataSourceService.create_data_source(
        db=db, data_source_data=data_source_data, create_user_id=current_user.id
    )
    return Resp(data=new_data_source)


@router.get("/data-sources", response_model=PagedResp[DataSourceResponse])
async def get_data_sources(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取数据源列表"""
    data_sources, total = DataSourceService.get_data_sources(db=db, skip=skip, limit=limit)
    return PagedResp(data=data_sources, total=total)


@router.get("/data-sources/{data_source_id}", response_model=Resp[DataSourceResponse])
async def get_data_source(
    data_source_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """获取数据源详情"""
    data_source = DataSourceService.get_data_source_by_id(
        db=db, data_source_id=data_source_id, include_workspaces=True
    )
    if not data_source:
        raise BizError(BizErrorCode.DATASOURCE_NOT_EXIST, "数据源不存在")
    return Resp(data=data_source)


@router.put("/data-sources/{data_source_id}", response_model=Resp[DataSourceResponse])
async def update_data_source(
    data_source_id: int,
    data_source_update: DataSourceUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """更新数据源"""
    data_source = DataSourceService.update_data_source(
        db=db,
        data_source_id=data_source_id,
        data_source_update=data_source_update,
        update_user_id=current_user.id,
    )
    return Resp(data=data_source)


@router.delete("/data-sources/{data_source_id}", response_model=Resp[DataSourceResponse])
async def delete_data_source(
    data_source_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """删除数据源"""
    data_source = DataSourceService.delete_data_source(db=db, data_source_id=data_source_id)
    return Resp(data=data_source)


@router.post("/data-sources/{data_source_id}/test", response_model=Resp[ConnectionTestResult])
async def test_data_source_connection(
    data_source_id: int,
    data_source_data: DataSourceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """测试数据源连接"""
    # 从请求体获取平台类型和配置
    platform = data_source_data.platform
    setting = data_source_data.setting

    # 调用服务层测试连接
    result = DataSourceService.test_data_source_connection(platform=platform, setting=setting)

    # 无论成功还是失败，都返回HTTP 200
    return Resp(data=result)


@router.get("/data-sources/{data_source_id}/tables", response_model=Resp[dict])
async def get_data_source_tables(
    data_source_id: int,
    database: Optional[str] = None,
    schema: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取数据源的表和视图列表"""
    result = DataSourceService.get_tables_and_views(
        db=db, data_source_id=data_source_id, database=database, schema=schema
    )
    return Resp(data=result)


@router.get(
    "/data-sources/{data_source_id}/tables/{table_name}/structure", response_model=Resp[list]
)
async def get_table_structure(
    data_source_id: int,
    table_name: str,
    database: Optional[str] = None,
    schema: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取表结构信息"""
    structure = DataSourceService.get_table_structure(
        db=db,
        data_source_id=data_source_id,
        table_name=table_name,
        database=database,
        schema=schema,
    )
    return Resp(data=structure)


@router.post("/data-sources/{data_source_id}/execute-sql", response_model=Resp[list])
async def execute_sql_query(
    data_source_id: int,
    sql_data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """执行SQL查询"""
    sql = sql_data.get("sql")
    params = sql_data.get("params")

    if not sql:
        raise BizError(BizErrorCode.DATASOURCE_SQL_ERROR, "SQL语句不能为空")

    result = DataSourceService.execute_sql_query(
        db=db, data_source_id=data_source_id, sql=sql, params=params
    )
    return Resp(data=result)
