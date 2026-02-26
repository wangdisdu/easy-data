"""
Easy Data 主应用入口
"""

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

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

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 初始化数据库基础数据
init_db_data()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Easy Data - 致力于做真正的的智能平台",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

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


@app.get("/", response_model=Resp[dict])
async def root():
    """根路径"""
    return Resp(
        data={"name": settings.APP_NAME, "version": settings.APP_VERSION, "status": "running"}
    )


@app.get("/health", response_model=Resp[dict])
async def health_check():
    """健康检查"""
    return Resp(data={"status": "healthy"})
