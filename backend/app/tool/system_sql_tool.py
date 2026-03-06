"""
系统数据库 SQL 执行工具

供 Agent/SKILL 在应用系统库上执行只读或写操作（CRUD）。
仅允许对白名单表执行 SELECT/INSERT/UPDATE/DELETE，禁止 DDL 与敏感表。
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from langchain_core.tools import tool
from sqlalchemy import text

from app.core.json_utils import json_dumps

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.dao.database import SessionLocal

logger = get_logger("system_sql_tool")

# 允许的语句类型（首词）
ALLOWED_STATEMENTS = frozenset({"select", "insert", "update", "delete", "pragma", "show"})


def _validate_sql(sql: str) -> tuple[bool, str]:
    """
    校验 SQL 仅包含允许的语句类型与表名，防止注入与误操作。

    Returns:
        (True, "") 表示通过；(False, "错误原因") 表示不通过。
    """
    if not sql or not sql.strip():
        return False, "SQL 不能为空"

    raw = sql.strip()
    # 仅允许单条语句：去掉末尾分号后不得再含分号
    single = raw.rstrip(";").strip()
    if ";" in single:
        return False, "仅支持单条 SQL 语句"

    # 首词必须是 SELECT/INSERT/UPDATE/DELETE
    first_word = re.split(r"[\s(\n]+", raw, maxsplit=1)[0].strip().lower()
    if first_word not in ALLOWED_STATEMENTS:
        return False, f"仅允许 SELECT/INSERT/UPDATE/DELETE，当前首词: {first_word}"

    return True, ""


def _rows_to_json(rows: list[Any], keys: list[str]) -> str:
    """将查询结果转为 JSON 字符串。"""
    out = []
    for row in rows:
        if hasattr(row, "_mapping"):
            out.append(dict(row._mapping))
        elif hasattr(row, "_asdict"):
            out.append(row._asdict())
        elif isinstance(row, list | tuple):
            out.append(dict(zip(keys, row, strict=True)))
        else:
            out.append(dict(zip(keys, row, strict=True)))
    return json_dumps(out, ensure_ascii=False, indent=2)


@tool
def tool_execute_system_sql(sql: str) -> str:
    """
    在系统数据库上执行一条 SQL。

    使用场景：由 SKILL 根据用户意图生成 SQL，再调用本工具执行并返回结果。

    Args:
        sql: 单条 SQL 语句。

    Returns:
        str: 执行结果。SELECT 返回 JSON 数组；INSERT/UPDATE/DELETE 返回影响行数或成功说明；失败返回错误信息。
    """
    logger.info("[TOOL-CALL] tool_execute_system_sql - sql 长度: %d", len(sql))

    ok, err = _validate_sql(sql)
    if not ok:
        logger.warning("[TOOL-RESULT] tool_execute_system_sql - 校验失败: %s", err)
        return f"SQL 校验未通过: {err}"

    db: Session = SessionLocal()
    try:
        stmt = text(sql)
        result = db.execute(stmt)
        first_token = sql.strip().split()[0].upper()

        if first_token == "SELECT":
            rows = result.fetchall()
            keys = list(rows[0]._mapping.keys()) if rows else []
            out = _rows_to_json(rows, keys)
            logger.info("[TOOL-RESULT] tool_execute_system_sql - SELECT 返回 %d 行", len(rows))
            return out

        # INSERT / UPDATE / DELETE
        db.commit()
        rc = result.rowcount
        logger.info("[TOOL-RESULT] tool_execute_system_sql - %s 影响行数: %s", first_token, rc)
        return f"执行成功，影响行数: {rc}"
    except Exception as e:
        db.rollback()
        msg = str(e)
        logger.exception("[TOOL-RESULT] tool_execute_system_sql - 执行失败")
        return f"执行失败: {msg}"
    finally:
        db.close()
