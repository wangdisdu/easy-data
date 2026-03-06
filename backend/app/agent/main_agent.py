"""
MainAgent - 系统主智能体

直接使用 DeepAgent("main", user_id) 实现。
- 静态策略：用户输入 /{智能体名} 时直接交给目标子智能体。
- 智能决策：否则由 main 的 DeepAgent workflow 编排子智能体。
"""

import re
from collections.abc import AsyncIterator
from typing import Any, Optional

from app.agent.agent_utils import create_session, setup_langsmith_tracing
from app.agent.deep_agent import DeepAgent
from app.core.logging import get_logger

logger = get_logger(__name__)

setup_langsmith_tracing()


def _parse_direct_agent(message: str) -> Optional[tuple[str, str]]:
    """
    解析用户是否输入 /{智能体名字}。
    返回 (agent_name, rest_message)，若不是直接指定则返回 None。
    """
    s = (message or "").strip()
    if not s.startswith("/"):
        return None
    match = re.match(r"^/(\w+)(?:\s+(.*))?$", s, re.DOTALL)
    if not match:
        return None
    name = match.group(1).strip().lower()
    rest = (match.group(2) or "").strip()
    return (name, rest)


class MainAgent:
    """
    系统主智能体：封装 DeepAgent("main")，支持 /{名} 直接路由与智能决策。
    """

    def __init__(self, user_id: Optional[int] = None) -> None:
        self.user_id = user_id
        self._agent = DeepAgent(agent_id="main", user_id=user_id)

    def create_session(self) -> str:
        return create_session()

    async def astream(self, session_id: str, message: str) -> AsyncIterator[dict[str, Any]]:
        """
        流式处理：/agent_name 时直接调用子智能体，否则交给 main workflow。
        """
        agent: DeepAgent
        msg: str

        # 静态策略：/{智能体名} 直接路由
        direct = _parse_direct_agent(message)
        if direct is not None:
            agent_name, rest_message = direct
            sub = next(
                (d for d in self._agent.subagents if d.agent_id == agent_name),
                None,
            )
            if sub is None:
                available = ", ".join(d.agent_id for d in self._agent.subagents)
                yield {"chunk": f"未知的智能体名称：{agent_name}。可用：{available or '无'}"}
                return
            if not rest_message:
                yield {"chunk": "请继续输入您要咨询的问题。"}
                return
            agent, msg = sub, rest_message
        else:
            agent, msg = self._agent, message

        try:
            async for chunk in agent.astream(session_id=session_id, message=msg):
                yield chunk
        except Exception as e:
            logger.exception("智能体执行错误")
            yield {"chunk": f"处理时出错：{e!s}"}
