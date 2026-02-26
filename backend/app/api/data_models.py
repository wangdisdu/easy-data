"""
数据模型管理API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.biz_error import BizError, BizErrorCode
from app.core.models import PagedResp, Resp
from app.dao.database import get_db
from app.services.data_models_service import (
    DataModelCreate,
    DataModelResponse,
    DataModelService,
    DataModelUpdate,
)

router = APIRouter()


@router.post("/data-models", response_model=Resp[DataModelResponse])
async def create_data_model(
    data_model_data: DataModelCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """创建数据模型"""
    new_data_model = DataModelService.create_data_model(
        db=db, data_model_data=data_model_data, create_user_id=current_user.id
    )
    return Resp(data=new_data_model)


@router.get("/data-models", response_model=PagedResp[DataModelResponse])
async def get_data_models(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取数据模型列表"""
    data_models, total = DataModelService.get_data_models(db=db, skip=skip, limit=limit)
    return PagedResp(data=data_models, total=total)


@router.get("/data-models/{data_model_id}", response_model=Resp[DataModelResponse])
async def get_data_model(
    data_model_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """获取数据模型详情"""
    data_model = DataModelService.get_data_model_by_id(
        db=db, data_model_id=data_model_id, include_workspaces=True
    )
    if not data_model:
        raise BizError(BizErrorCode.DATAMODEL_NOT_EXIST, "数据模型不存在")
    return Resp(data=data_model)


@router.put("/data-models/{data_model_id}", response_model=Resp[DataModelResponse])
async def update_data_model(
    data_model_id: int,
    data_model_update: DataModelUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """更新数据模型"""
    data_model = DataModelService.update_data_model(
        db=db,
        data_model_id=data_model_id,
        data_model_update=data_model_update,
        update_user_id=current_user.id,
    )
    return Resp(data=data_model)


@router.delete("/data-models/{data_model_id}", response_model=Resp[DataModelResponse])
async def delete_data_model(
    data_model_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """删除数据模型"""
    data_model = DataModelService.delete_data_model(db=db, data_model_id=data_model_id)
    return Resp(data=data_model)
