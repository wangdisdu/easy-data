"""
API路由
"""

from fastapi import APIRouter

from app.api import agents, auth, chat, data_models, data_sources, llm, system, tools, users, workspaces

api_router = APIRouter()

api_router.include_router(chat.router, tags=["对话"])
api_router.include_router(auth.router, tags=["认证"])
api_router.include_router(users.router, tags=["用户"])
api_router.include_router(workspaces.router, tags=["工作空间"])
api_router.include_router(data_sources.router, tags=["数据源"])
api_router.include_router(data_models.router, tags=["数据模型"])
api_router.include_router(agents.router, tags=["智能体管理"])
api_router.include_router(tools.router, tags=["工具管理"])
api_router.include_router(llm.router, tags=["LLM模型管理"])
api_router.include_router(system.router, tags=["系统"])
