"""
系统初始化接口（需登录）
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.models import Resp
from app.dao.database import get_db
from app.service.llm_service import LlmService, LlmUpdate

router = APIRouter()

DEFAULT_LLM_ID = 1


class LlmDefaultStatusResponse(BaseModel):
    configured: bool


class InitLlmBody(BaseModel):
    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None


def _is_llm_configured(llm) -> bool:
    """判断 tb_llm id=1 是否已配置：模型提供商、模型名称、API密钥、API基础URL 均非空。"""
    if not llm:
        return False
    provider = (llm.provider or "").strip()
    model = (llm.model or "").strip()
    api_key = (llm.api_key or "").strip()
    base_url = (llm.base_url or "").strip()
    return bool(provider and model and api_key and base_url)


@router.get("/system/llm-default-status", response_model=Resp[LlmDefaultStatusResponse])
async def get_llm_default_status(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取默认 LLM（id=1）是否已配置，用于决定是否展示系统初始化页。需登录。"""
    llm = LlmService.get_llm_by_id(db=db, llm_id=DEFAULT_LLM_ID)
    return Resp(data=LlmDefaultStatusResponse(configured=_is_llm_configured(llm)))


@router.post("/system/init-llm", response_model=Resp[dict])
async def init_llm(
    body: InitLlmBody,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """系统初始化：更新默认 LLM（id=1）的 provider、api_key、base_url。需登录。"""
    llm = LlmService.get_llm_by_id(db=db, llm_id=DEFAULT_LLM_ID)
    if not llm:
        return Resp(code="E001", msg="默认LLM不存在", data=None)
    LlmService.update_llm(
        db=db,
        llm_id=DEFAULT_LLM_ID,
        llm_update=LlmUpdate(
            provider=body.provider,
            model=body.model,
            api_key=body.api_key or "",
            base_url=body.base_url or "",
        ),
        update_user_id=current_user.id,
    )
    return Resp(data={"ok": True})
