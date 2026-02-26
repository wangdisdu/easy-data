"""
数据库初始化：导入初始化数据并执行初始化逻辑。

- 初始化数据（LLM/工具/智能体 ROWS）在 app.dao.data 包中声明：tb_llm、tb_tool（聚合 tools/*）、tb_agent（聚合 agents/*）。
- 本模块仅负责：导入 ROWS、执行 init_user / init_workspace / init_llm / init_tools / init_agents。

从数据库生成 app/dao/data 初始化数据：
  cd backend && python scripts/gen_init_data.py [--db path/to/easy_data.db]
"""

import time

from app.core.logging import get_logger
from app.core.security import get_password_hash
from app.dao.data import (
    AGENT_EDGE_ROWS,
    AGENT_NODE_ROWS,
    AGENT_ROWS,
    LLM_ROWS,
    TOOL_ROWS,
)
from app.dao.database import SessionLocal
from app.dao.models import (
    TbAgent,
    TbAgentEdge,
    TbAgentNode,
    TbLlm,
    TbTool,
    TbUser,
    TbWorkSpace,
)

logger = get_logger("init_db")


def init_user():
    """初始化 admin 用户"""
    db = SessionLocal()
    try:
        # 检查是否已存在 admin 用户
        admin_user = db.query(TbUser).filter(TbUser.account == "admin").first()
        if not admin_user:
            current_time = int(time.time() * 1000)

            admin_user = TbUser(
                guid="admin",
                account="admin",
                name="管理员",
                passwd=get_password_hash("admin"),
                email="admin@easy-data.com",
                create_time=current_time,
                update_time=current_time,
            )
            db.add(admin_user)
            db.commit()
            logger.info("Admin 用户初始化成功：账号=admin, 密码=admin")
            return True
        else:
            # 如果用户已存在，更新密码以确保使用最新的哈希逻辑
            logger.info("Admin 用户已存在，更新密码以确保使用最新的哈希逻辑")
            admin_user.passwd = get_password_hash("admin")
            admin_user.update_time = int(time.time() * 1000)
            db.commit()
            logger.info("Admin 用户密码已更新")
            return True
    except Exception:
        logger.exception("初始化 Admin 用户失败")
        db.rollback()
        return False
    finally:
        db.close()


def init_workspace():
    """初始化默认工作空间"""
    db = SessionLocal()
    try:
        # 检查是否已存在默认工作空间
        default_workspace = db.query(TbWorkSpace).filter(TbWorkSpace.code == "default").first()
        if not default_workspace:
            current_time = int(time.time() * 1000)

            default_workspace = TbWorkSpace(
                code="default",
                name="默认工作空间",
                description="系统默认工作空间",
                create_time=current_time,
                update_time=current_time,
            )
            db.add(default_workspace)
            db.commit()
            logger.info("默认工作空间初始化成功：code=default, name=默认工作空间")
            return True
        else:
            logger.info("默认工作空间已存在")
            return True
    except Exception:
        logger.exception("初始化默认工作空间失败")
        db.rollback()
        return False
    finally:
        db.close()


def _row_meta() -> dict:
    t = int(time.time() * 1000)
    return {"create_time": t, "update_time": t, "create_user": 1, "update_user": 1}


def init_llm() -> bool:
    """初始化LLM"""
    db = SessionLocal()
    try:
        if db.query(TbLlm).count() > 0:
            logger.info("大模型数据已存在，跳过初始化")
            return False
        meta = _row_meta()
        for row in LLM_ROWS:
            db.add(TbLlm(**{**row, **meta}))
        db.commit()
        logger.info("大模型初始化成功，共 %d 条", len(LLM_ROWS))
        return True
    except Exception:
        logger.exception("大模型初始化失败")
        db.rollback()
        return False
    finally:
        db.close()


def init_tools() -> bool:
    """初始化工具"""
    db = SessionLocal()
    try:
        if db.query(TbTool).count() > 0:
            logger.info("工具数据已存在，跳过初始化")
            return False
        meta = _row_meta()
        for row in TOOL_ROWS:
            db.add(TbTool(**{**row, **meta}))
        db.commit()
        logger.info("工具初始化成功，共 %d 条", len(TOOL_ROWS))
        return True
    except Exception:
        logger.exception("工具初始化失败")
        db.rollback()
        return False
    finally:
        db.close()


def init_agents() -> bool:
    """初始化智能体"""
    db = SessionLocal()
    try:
        if db.query(TbAgent).count() > 0:
            logger.info("智能体数据已存在，跳过初始化")
            return False
        meta = _row_meta()
        for row in AGENT_ROWS:
            db.add(TbAgent(**{**row, **meta}))
        for row in AGENT_NODE_ROWS:
            db.add(TbAgentNode(**{**row, **meta}))
        for row in AGENT_EDGE_ROWS:
            db.add(TbAgentEdge(**{**row, **meta}))
        db.commit()
        logger.info(
            "智能体初始化成功：agent %d 条，node %d 条，edge %d 条",
            len(AGENT_ROWS),
            len(AGENT_NODE_ROWS),
            len(AGENT_EDGE_ROWS),
        )
        return True
    except Exception:
        logger.exception("智能体初始化失败")
        db.rollback()
        return False
    finally:
        db.close()


def init_db_data():
    """执行所有数据初始化函数"""
    init_user()
    init_workspace()
    init_llm()
    init_tools()
    init_agents()
