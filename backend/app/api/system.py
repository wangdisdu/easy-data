"""
系统初始化接口与系统库查询（需登录）
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.models import Resp
from app.dao.database import get_db
from app.service.llm_service import LlmService, LlmUpdate
from app.tool.system_sql_tool import _validate_sql

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


# ---------- 系统库查询（数据查询页「系统库」） ----------


class SystemSqlBody(BaseModel):
    sql: str


@router.get("/system/tables", response_model=Resp[dict])
async def get_system_tables(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取系统库表列表，用于数据查询页系统库树。"""
    result = db.execute(
        text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    )
    rows = result.fetchall()
    tables = [row[0] for row in rows]
    return Resp(data={"tables": tables, "views": []})


@router.get("/system/tables/{table_name}/structure", response_model=Resp[list])
async def get_system_table_structure(
    table_name: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取系统库某表的结构（SQLite PRAGMA table_info）。"""
    if not table_name or not table_name.replace("_", "").isalnum():
        return Resp(code="E002", msg="无效表名", data=[])
    result = db.execute(text(f"PRAGMA table_info({table_name})"))
    rows = result.fetchall()
    data = [
        {
            "field_name": row[1],
            "data_type": row[2],
            "is_nullable": row[3] == 0,
            "is_primary_key": bool(row[5]),
        }
        for row in rows
    ]
    return Resp(data=data)


@router.post("/system/execute-sql", response_model=Resp[list])
async def execute_system_sql(
    body: SystemSqlBody,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """在系统库上执行一条 SQL，用于数据查询页「系统库」。仅允许 SELECT/INSERT/UPDATE/DELETE。"""
    sql = (body.sql or "").strip()
    if not sql:
        return Resp(code="E002", msg="SQL 不能为空", data=[])

    ok, err = _validate_sql(sql)
    if not ok:
        return Resp(code="E002", msg=f"SQL 校验未通过: {err}", data=[])

    try:
        stmt = text(sql)
        result = db.execute(stmt)
        first_token = sql.split()[0].upper()

        if first_token == "SELECT":
            rows = result.fetchall()
            keys = list(rows[0]._mapping.keys()) if rows else []
            data = [dict(row._mapping) for row in rows]
            return Resp(data=data)
        # INSERT / UPDATE / DELETE
        db.commit()
        rc = result.rowcount
        return Resp(data=[{"message": f"执行成功，影响行数: {rc}"}])
    except Exception as e:
        db.rollback()
        return Resp(code="E002", msg=f"执行失败: {e!s}", data=[])
