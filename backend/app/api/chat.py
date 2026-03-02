"""
对话API
"""

import contextlib
from typing import Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel

from app.agent import TextToSqlAgent
from app.agent.agent_executor import AgentExecutor
from app.agent.base_agent import BaseAgent
from app.core.biz_error import BizError
from app.core.logging import get_logger
from app.dao.database import SessionLocal
from app.service.auth_service import AuthService

logger = get_logger("chat")

router = APIRouter()

# WebSocket 连接管理：存储 WebSocket 和用户 ID 的映射关系
# 格式：{websocket_id: {"websocket": websocket, "user_id": user_id}}
websocket_connections = {}


async def _authenticate_websocket(websocket: WebSocket, token: Optional[str]) -> Optional[int]:
    """验证 WebSocket 连接的 token

    Args:
        websocket: WebSocket 连接对象
        token: 认证 token

    Returns:
        用户 ID，如果验证失败则返回 None（并关闭连接）

    Raises:
        如果验证失败，会关闭连接并返回 None
    """
    if not token:
        logger.warning("WebSocket 连接缺少 token")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="缺少认证凭据")
        return None

    db = SessionLocal()
    try:
        user = AuthService.get_user_by_token(db=db, token=token)
        user_id = user.id
        logger.info(f"WebSocket 连接认证成功：user_id={user_id}, account={user.account}")
        return user_id
    except BizError as e:
        logger.warning(f"WebSocket 连接认证失败：{e.message}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=e.message)
        return None
    finally:
        if db:
            db.close()


def _accept_and_register_connection(websocket: WebSocket, user_id: int) -> int:
    """接受 WebSocket 连接并注册到连接管理

    Args:
        websocket: WebSocket 连接对象
        user_id: 用户 ID

    Returns:
        websocket_id: WebSocket 连接的唯一标识符
    """
    websocket_id = id(websocket)
    websocket_connections[websocket_id] = {"websocket": websocket, "user_id": user_id}
    logger.info(f"WebSocket 连接已建立：user_id={user_id}, websocket_id={websocket_id}")
    return websocket_id


async def _send_connection_success(websocket: WebSocket, session_id: str) -> None:
    """发送连接成功消息

    Args:
        websocket: WebSocket 连接对象
        session_id: 会话 ID
    """
    await websocket.send_json(
        {
            "type": "connection",
            "status": "success",
            "message": "连接已建立",
            "session_id": session_id,
        }
    )


async def _send_stream_start(websocket: WebSocket, session_id: str) -> None:
    """发送流式输出开始标记

    Args:
        websocket: WebSocket 连接对象
        session_id: 会话 ID
    """
    await websocket.send_json(
        {"type": "stream_start", "session_id": session_id, "status": "streaming"}
    )


async def _send_stream_end(websocket: WebSocket, session_id: str) -> None:
    """发送流式输出结束标记

    Args:
        websocket: WebSocket 连接对象
        session_id: 会话 ID
    """
    await websocket.send_json({"type": "stream_end", "session_id": session_id, "status": "success"})


async def _send_stream_chunk(
    websocket: WebSocket, session_id: str, chunk_dict: dict[str, Any]
) -> None:
    """发送流式数据块

    Args:
        websocket: WebSocket 连接对象
        session_id: 会话 ID
        chunk_dict: 数据块字典
    """
    if chunk_dict and chunk_dict.get("chunk"):
        await websocket.send_json(
            {
                **chunk_dict,
                "type": "stream_chunk",
                "session_id": session_id,
                "status": "streaming",
            }
        )


async def _send_error(websocket: WebSocket, session_id: str, error_message: str) -> None:
    """发送错误消息

    Args:
        websocket: WebSocket 连接对象
        session_id: 会话 ID
        error_message: 错误消息
    """
    await websocket.send_json(
        {
            "type": "error",
            "status": "error",
            "message": error_message,
            "session_id": session_id,
        }
    )


async def _process_message_stream(
    agent: BaseAgent, websocket: WebSocket, session_id: str, message: str, user_id: int
) -> None:
    """处理单条消息的流式输出

    Args:
        agent: Agent 实例
        websocket: WebSocket 连接对象
        session_id: 会话 ID
        message: 用户消息
        user_id: 用户 ID
    """
    logger.debug(f"收到消息：user_id={user_id}, message={message[:50]}...")

    try:
        await _send_stream_start(websocket, session_id)

        # 使用流式输出处理消息
        async for chunk_dict in agent.astream(session_id=session_id, message=message):
            # 确保 chunk_dict 是字典类型
            if isinstance(chunk_dict, dict):
                await _send_stream_chunk(websocket, session_id, chunk_dict)
            else:
                logger.warning(f"收到非字典类型的 chunk: {type(chunk_dict)}, 值: {chunk_dict}")

        await _send_stream_end(websocket, session_id)

    except Exception as e:
        error_msg = f"处理消息时发生错误：{e!s}"
        logger.exception("处理消息时发生错误")
        await _send_error(websocket, session_id, error_msg)


def _cleanup_connection(websocket_id: Optional[int]) -> None:
    """清理连接资源

    Args:
        websocket_id: WebSocket 连接 ID，如果存在则从连接管理中移除
    """
    if websocket_id and websocket_id in websocket_connections:
        del websocket_connections[websocket_id]
        logger.debug(f"已清理 WebSocket 连接：websocket_id={websocket_id}")


async def _handle_websocket_error(websocket: WebSocket, error: Exception) -> None:
    """处理 WebSocket 错误

    Args:
        websocket: WebSocket 连接对象
        error: 异常对象
    """
    logger.exception("WebSocket 处理错误")
    with contextlib.suppress(BaseException):
        await websocket.send_json(
            {"type": "error", "status": "error", "message": f"处理消息时发生错误：{error!s}"}
        )


class ChatMessage(BaseModel):
    """聊天消息模型"""

    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """聊天响应模型"""

    response: str
    session_id: str
    status: str = "success"


@router.websocket("/ws/chat/main")
async def websocket_chat(websocket: WebSocket, token: Optional[str] = None):
    """
    WebSocket聊天接口

    连接流程：
    1. 客户端连接时需要在 URL 参数中传递 token
    2. 服务端验证 token，获取用户 ID
    3. 验证通过后接受连接，并将 WebSocket 与用户 ID 绑定
    4. 后续长连接过程中，只要连接不断开，就不需要再次认证
    """
    user_id: Optional[int] = None
    websocket_id: Optional[int] = None

    try:
        # 1. 验证 token 并获取用户 ID
        user_id = await _authenticate_websocket(websocket, token)
        if user_id is None:
            return

        # 2. 接受 WebSocket 连接并注册
        await websocket.accept()
        websocket_id = _accept_and_register_connection(websocket, user_id)

        # 3. 创建 Agent 实例并获取会话 ID
        agent = TextToSqlAgent(user_id=user_id)
        session_id = agent.create_session()

        # 4. 发送连接成功消息
        await _send_connection_success(websocket, session_id)

        # 5. 处理消息循环
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")

            if not message:
                continue

            await _process_message_stream(agent, websocket, session_id, message, user_id)

    except WebSocketDisconnect:
        logger.info(f"WebSocket 连接已断开：user_id={user_id}, websocket_id={websocket_id}")
    except Exception as e:
        await _handle_websocket_error(websocket, e)
    finally:
        _cleanup_connection(websocket_id)


@router.websocket("/ws/chat/{agent_id}")
async def websocket_chat_agent(websocket: WebSocket, agent_id: int, token: Optional[str] = None):
    """
    WebSocket 智能体聊天接口

    连接流程：
    1. 客户端连接时需要在 URL 参数中传递 token
    2. 服务端验证 token，获取用户 ID
    3. 验证通过后接受连接
    4. 创建 AgentExecutor 实例
    5. 处理消息循环，使用 AgentExecutor 执行智能体
    """
    user_id: Optional[int] = None
    websocket_id: Optional[int] = None
    db: SessionLocal | None = None

    try:
        # 1. 验证 token 并获取用户 ID
        user_id = await _authenticate_websocket(websocket, token)
        if user_id is None:
            return

        # 2. 接受 WebSocket 连接并注册
        await websocket.accept()
        websocket_id = _accept_and_register_connection(websocket, user_id)

        # 3. 创建数据库会话并初始化 AgentExecutor
        db = SessionLocal()
        try:
            executor = AgentExecutor(db, agent_id, user_id)
            executor.build()
        except BizError as e:
            logger.exception("初始化智能体执行器失败")
            await _send_error(websocket, "", e.message)
            return
        except Exception as e:
            logger.exception("初始化智能体执行器失败")
            await _send_error(websocket, "", f"初始化智能体失败: {e!s}")
            return

        # 4. 创建会话 ID
        session_id = executor.create_session()

        # 5. 发送连接成功消息
        await _send_connection_success(websocket, session_id)

        # 6. 处理消息循环
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")

            if not message:
                continue

            # 使用 BaseAgent 的 astream 方法处理消息流
            await _process_message_stream(executor, websocket, session_id, message, user_id)

    except WebSocketDisconnect:
        logger.info(
            f"WebSocket 连接已断开：user_id={user_id}, agent_id={agent_id}, websocket_id={websocket_id}"
        )
    except Exception as e:
        await _handle_websocket_error(websocket, e)
    finally:
        _cleanup_connection(websocket_id)
        if db:
            db.close()
