"""
LLM模型管理API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.biz_error import BizError, BizErrorCode
from app.core.models import PagedResp, Resp
from app.dao.database import get_db
from app.service.llm_service import LlmCreate, LlmResponse, LlmService, LlmUpdate

router = APIRouter()


@router.post("/llms", response_model=Resp[LlmResponse])
async def create_llm(
    llm_data: LlmCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """创建LLM模型"""
    new_llm = LlmService.create_llm(db=db, llm_data=llm_data, create_user_id=current_user.id)
    return Resp(data=new_llm)


@router.get("/llms", response_model=PagedResp[LlmResponse])
async def get_llms(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取LLM列表"""
    llms, total = LlmService.get_llms(db=db, skip=skip, limit=limit)
    return PagedResp(data=llms, total=total)


@router.get("/llms/{llm_id}", response_model=Resp[LlmResponse])
async def get_llm(
    llm_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """获取LLM详情"""
    llm = LlmService.get_llm_by_id(db=db, llm_id=llm_id)
    if not llm:
        raise BizError(BizErrorCode.LLM_NOT_EXIST, "LLM模型不存在")
    return Resp(data=llm)


@router.put("/llms/{llm_id}", response_model=Resp[LlmResponse])
async def update_llm(
    llm_id: int,
    llm_update: LlmUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """更新LLM模型"""
    llm = LlmService.update_llm(
        db=db,
        llm_id=llm_id,
        llm_update=llm_update,
        update_user_id=current_user.id,
    )
    return Resp(data=llm)


@router.delete("/llms/{llm_id}", response_model=Resp[LlmResponse])
async def delete_llm(
    llm_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """删除LLM模型"""
    llm = LlmService.delete_llm(db=db, llm_id=llm_id)
    return Resp(data=llm)
