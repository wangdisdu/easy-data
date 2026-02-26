"""
全局异常处理器
用于处理HTTP请求中的意外异常情况
"""

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.biz_error import BizError
from app.core.logging import get_logger
from app.core.models import Resp

logger = get_logger("exception_handler")


async def biz_error_handler(request: Request, exc: BizError) -> JSONResponse:
    """
    业务异常处理器
    处理BizError异常
    """
    logger.warning(
        f"业务异常：code={exc.code}, message={exc.message}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.code,
            "error_message": exc.message,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=Resp(code=str(exc.code), msg=exc.message, data=None).model_dump(),
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    全局异常处理器
    捕获所有未处理的异常，返回统一的错误响应
    """
    logger.exception(
        f"请求路径：{request.method} {request.url.path}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "client": request.client.host if request.client else None,
        },
    )

    # 如果是SQLAlchemy异常，记录更详细的信息
    if isinstance(exc, SQLAlchemyError):
        logger.exception("数据库异常")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=Resp(code="5000", msg="请求失败，请联系管理员", data=None).model_dump(),
        )

    # 对于其他未预期的异常，返回通用错误信息
    # 在生产环境中不暴露详细的异常信息
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=Resp(code="0500", msg="请求失败，请联系管理员", data=None).model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    HTTP异常处理器
    处理FastAPI的HTTPException
    """

    # 将HTTP状态码映射为业务错误码
    error_code = f"{exc.status_code:04d}"

    return JSONResponse(
        status_code=exc.status_code,
        content=Resp(code=error_code, msg=exc.detail, data=None).model_dump(),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    请求验证异常处理器
    处理FastAPI的RequestValidationError（请求参数验证失败）
    """
    logger.warning(
        f"请求参数验证失败：{exc.errors()}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors(),
        },
    )

    # 格式化验证错误信息
    error_messages = []
    for error in exc.errors():
        field = "->".join(str(loc) for loc in error["loc"] if loc != "body")
        error_messages.append(f"{field}: {error['msg']}")

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=Resp(
            code="0400", msg="请求参数验证失败：" + "; ".join(error_messages), data=None
        ).model_dump(),
    )
