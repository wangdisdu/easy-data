"""
基础Agent类
提供所有智能体通用的流式处理逻辑
"""

import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, Optional

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("base_agent")

# LangGraph astream 返回格式常量
STREAM_TUPLE_SIZE_STANDARD = 2  # 标准格式: (stream_mode, chunk)
STREAM_TUPLE_SIZE_SUBGRAPH = 3  # 子图格式: (node_name, stream_mode, chunk)


class BaseAgent(ABC):
    """基础Agent类，提供通用的流式处理逻辑"""

    def __init__(self, user_id: Optional[int] = None):
        """初始化基础Agent

        Args:
            user_id: 用户ID
        """
        self.user_id = user_id
        # 初始化LLM
        try:
            init_kwargs = {
                "base_url": settings.OPENAI_BASE_URL,
                "api_key": settings.OPENAI_API_KEY,
                "model": settings.OPENAI_MODEL,
                "streaming": True,
            }
            self.llm = ChatOpenAI(**init_kwargs)
        except Exception:
            logger.exception("初始化 LLM 失败")
            self.llm = ChatOpenAI()

        self.workflow = None  # 子类需要在 __init__ 中设置
        self.has_subgraphs = False  # 是否包含子图，子类可以重载

    def create_session(self) -> str:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        return session_id

    @abstractmethod
    def _build_initial_state(self, session_id: str, message: str) -> dict[str, Any]:
        """构建初始状态

        Args:
            session_id: 会话ID
            message: 用户消息

        Returns:
            初始状态字典
        """

    def _get_workflow_config(self) -> dict[str, Any]:
        """获取工作流配置

        子类可以覆盖此方法以提供额外的配置参数，如 recursion_limit 等

        Returns:
            工作流配置字典，默认为空字典
        """
        return {}

    def _process_message_item(self, item: Any) -> Optional[dict[str, Any]]:
        """处理单个消息项

        Args:
            item: 消息项

        Returns:
            处理后的字典，如果不需要处理则返回 None
        """
        if not (hasattr(item, "content") and item.content):
            return None

        if isinstance(item, ToolMessage):
            # 处理 ToolMessage(工具调用结果)
            return {
                "chunk": item.content,
                "tool_result_id": item.tool_call_id,
            }

        if not isinstance(item, HumanMessage):
            # 忽略 HumanMessage 消息
            return {"chunk": item.content}

        return None

    def _extract_tool_call_info(
        self, node_name: str, tool_call: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """提取工具调用信息

        Args:
            node_name: 节点名称
            tool_call: 工具调用字典

        Returns:
            工具调用信息字典，如果格式不正确则返回 None
        """
        if not (isinstance(tool_call, dict) and "id" in tool_call and "name" in tool_call):
            return None

        tool_call_id = tool_call.get("id")
        tool_name = tool_call["name"]
        tool_args = tool_call.get("args", {})
        tool_call_info = f"\n🔧 [{node_name}] 执行工具: {tool_name}, 参数: {tool_args}\n"
        return {
            "chunk": tool_call_info,
            "tool_call_id": tool_call_id,
        }

    def _process_messages_stream(self, chunk: Any) -> list[dict[str, Any]]:
        """处理 messages 流模式的数据

        Args:
            chunk: 消息块（通常是元组，包含多个消息）

        Returns:
            处理后的消息字典列表
        """
        if not isinstance(chunk, tuple):
            return []

        results = []
        for item in chunk:
            result = self._process_message_item(item)
            if result:
                results.append(result)
        return results

    def _process_updates_stream(self, chunk: Any) -> list[dict[str, Any]]:
        """处理 updates 流模式的数据

        Args:
            chunk: 更新块（通常是字典，key 是节点名，value 是节点返回的状态）

        Returns:
            处理后的工具调用信息字典列表
        """
        if not isinstance(chunk, dict):
            return []

        results = []
        for node_name, node_state in chunk.items():
            if not (
                isinstance(node_state, dict) and "messages" in node_state and node_state["messages"]
            ):
                continue

            last_message = node_state["messages"][-1]
            if not (hasattr(last_message, "tool_calls") and last_message.tool_calls):
                continue

            for tool_call in last_message.tool_calls:
                result = self._extract_tool_call_info(node_name, tool_call)
                if result:
                    results.append(result)
        return results

    def _process_stream_chunk(
        self, stream_mode: str, chunk: Any, node_name: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """处理流式数据块

        Args:
            stream_mode: 流模式 ("messages" 或 "updates")
            chunk: 数据块
            node_name: 节点名称（可选，用于子图场景）

        Returns:
            处理后的消息字典列表
        """
        if stream_mode == "messages":
            return self._process_messages_stream(chunk)
        elif stream_mode == "updates":
            return self._process_updates_stream(chunk)
        else:
            logger.warning(f"未知的流模式: {stream_mode}")
            return []

    async def astream(self, session_id: str, message: str) -> AsyncIterator[dict[str, Any]]:
        """
        流式处理用户消息

        使用 LangGraph 工作流的流式输出，支持工具调用的流式执行

        Args:
            session_id: 会话ID
            message: 用户消息

        Yields:
            dict: 流式输出的字典，格式为 {"chunk": "..."}
                或 {"chunk": "...", "tool_call_id": "..."}
                或 {"chunk": "...", "tool_result_id": "..."}
        """

        try:
            # 构建初始状态
            initial_state = self._build_initial_state(session_id, message)

            # 构建 astream 调用参数
            # LangGraph 的 astream 方法需要 input 参数，而不是 initial_state
            astream_kwargs = {
                "input": initial_state,
                "stream_mode": ["messages", "updates"],
            }

            # 获取工作流配置（如果有）
            config = self._get_workflow_config()
            if config:
                astream_kwargs["config"] = config

            # 如果有子图，则启用子图模式
            if self.has_subgraphs:
                astream_kwargs["subgraphs"] = True

            # 统一处理流式输出，支持标准格式 (stream_mode, chunk) 和子图格式 (node_name, stream_mode, chunk)
            async for item in self.workflow.astream(**astream_kwargs):
                if isinstance(item, tuple):
                    if len(item) == STREAM_TUPLE_SIZE_STANDARD:
                        # 标准格式: (stream_mode, chunk)
                        stream_mode, chunk = item
                        node_name = None
                    elif len(item) == STREAM_TUPLE_SIZE_SUBGRAPH:
                        # 子图格式: (node_name, stream_mode, chunk)
                        node_name, stream_mode, chunk = item
                    else:
                        logger.warning(f"收到非预期的元组长度: {len(item)}, 值: {item}")
                        continue

                    # 统一处理流式数据块
                    for result in self._process_stream_chunk(stream_mode, chunk, node_name):
                        yield result
                else:
                    # 非元组格式，记录警告但继续处理
                    logger.warning(f"收到非预期的返回格式: {type(item)}, 值: {item}")

        except Exception as e:
            error_msg = f"处理消息失败: {e!s}"
            logger.exception("流式处理消息错误")
            yield {"chunk": error_msg}
