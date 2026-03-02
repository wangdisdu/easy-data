"""
Easy Data 主应用入口
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, Response

from app.api import api_router
from app.core.biz_error import BizError
from app.core.config import settings
from app.core.exception_handler import (
    biz_error_handler,
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.models import Resp
from app.dao.database import Base, engine
from app.dao.init_db import init_db_data

# 前端静态文件目录（backend/www）
WWW_DIR = Path(__file__).resolve().parent.parent / "www"

HTTP_STATUS_NOT_FOUND = 404

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 初始化数据库基础数据
init_db_data()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期：启动时启动作业扫描器"""
    from app.job.scanner import start_job_scanner

    start_job_scanner()
    yield
    # shutdown 时无需显式停止扫描任务，进程退出即结束


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Easy Data - 致力于做真正的的智能平台",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)


class SPAStaticFilesMiddleware(BaseHTTPMiddleware):
    """SPA 前端路由回退：对非 API 的 GET 请求 404 返回 index.html"""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if (
            response.status_code == HTTP_STATUS_NOT_FOUND
            and request.method == "GET"
            and not request.url.path.startswith("/api")
            and WWW_DIR.joinpath("index.html").exists()
        ):
            return FileResponse(WWW_DIR / "index.html")
        return response


# SPA 回退需最先添加，以便能拦截到静态文件 404
app.add_middleware(SPAStaticFilesMiddleware)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip压缩
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 注册全局异常处理器
# 注意：异常处理器的注册顺序很重要，更具体的异常应该先注册
app.add_exception_handler(BizError, biz_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# 注册路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", response_model=Resp[dict])
async def health_check():
    """健康检查"""
    return Resp(data={"status": "healthy"})


# 挂载前端静态文件（backend/www），/ 提供 SPA，非 API 的 404 由中间件回退到 index.html
if WWW_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WWW_DIR), html=True), name="www")
