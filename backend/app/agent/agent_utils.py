"""
Agent工具模块
提供Agent相关的工具函数与流式工作流处理逻辑（原 BaseAgent 核心能力）
"""

import os
import uuid
from collections.abc import AsyncIterator
from typing import Any, Optional

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# LangGraph astream 返回格式常量
STREAM_TUPLE_SIZE_STANDARD = 2  # 标准格式: (stream_mode, chunk)
STREAM_TUPLE_SIZE_SUBGRAPH = 3  # 子图格式: (node_name, stream_mode, chunk)


def create_session() -> str:
    """创建新会话 ID。"""
    return str(uuid.uuid4())


def process_message_item(item: Any) -> Optional[dict[str, Any]]:
    """处理单个消息项，返回 chunk 字典或 None。"""
    if not (hasattr(item, "content") and item.content):
        return None
    if isinstance(item, ToolMessage):
        return {
            "chunk": item.content,
            "tool_result_id": item.tool_call_id,
        }
    if not isinstance(item, HumanMessage):
        return {"chunk": item.content}
    return None


def extract_tool_call_info(node_name: str, tool_call: dict[str, Any]) -> Optional[dict[str, Any]]:
    """从工具调用中提取展示用信息。"""
    if not (isinstance(tool_call, dict) and "id" in tool_call and "name" in tool_call):
        return None
    tool_call_id = tool_call.get("id")
    tool_name = tool_call["name"]
    tool_args = tool_call.get("args", {})
    tool_call_info = f"\n🔧 [{node_name}] 执行工具: {tool_name}, 参数: {tool_args}\n"
    return {"chunk": tool_call_info, "tool_call_id": tool_call_id}


def get_messages_list_from_state_update(messages_value: Any) -> Optional[list]:
    """从 updates 流中的 messages 字段取出可下标的列表（处理 Overwrite 等包装）。"""
    if messages_value is None:
        return None
    if isinstance(messages_value, list):
        return messages_value
    if hasattr(messages_value, "value"):
        return get_messages_list_from_state_update(messages_value.value)
    return None


def process_messages_stream(chunk: Any) -> list[dict[str, Any]]:
    """处理 messages 流模式的数据。"""
    if not isinstance(chunk, tuple):
        return []
    results = []
    for item in chunk:
        result = process_message_item(item)
        if result:
            results.append(result)
    return results


def process_updates_stream(chunk: Any) -> list[dict[str, Any]]:
    """处理 updates 流模式的数据。"""
    if not isinstance(chunk, dict):
        return []
    results = []
    for node_name, node_state in chunk.items():
        if not (isinstance(node_state, dict) and "messages" in node_state):
            continue
        messages_list = get_messages_list_from_state_update(node_state["messages"])
        if not messages_list:
            continue
        last_message = messages_list[-1]
        if not (hasattr(last_message, "tool_calls") and last_message.tool_calls):
            continue
        for tool_call in last_message.tool_calls:
            result = extract_tool_call_info(node_name, tool_call)
            if result:
                results.append(result)
    return results


def process_stream_chunk(
    stream_mode: str, chunk: Any, node_name: Optional[str] = None
) -> list[dict[str, Any]]:
    """根据流模式处理单块数据。"""
    if stream_mode == "messages":
        return process_messages_stream(chunk)
    if stream_mode == "updates":
        return process_updates_stream(chunk)
    logger.warning(f"未知的流模式: {stream_mode}")
    return []


async def astream_graph(
    graph: CompiledStateGraph,
    initial_state: dict[str, Any],
    *,
    config: RunnableConfig | None = None,
    subgraphs: bool = False,
) -> AsyncIterator[dict[str, Any]]:
    """
    对 LangGraph 做流式调用，统一处理 (stream_mode, chunk) 与子图格式，
    产出 chunk 字典序列。
    """
    run_config = dict(config) if config else {}
    configurable = run_config.get("configurable")
    if not isinstance(configurable, dict):
        configurable = {}
    thread_id = (
        configurable.get("thread_id") or initial_state.get("session_id") or str(uuid.uuid4())
    )
    run_config["configurable"] = {**configurable, "thread_id": thread_id}

    astream_kwargs: dict[str, Any] = {
        "input": initial_state,
        "stream_mode": ["messages", "updates"],
        "config": run_config,
        "subgraphs": subgraphs,
    }

    try:
        async for item in graph.astream(**astream_kwargs):
            if not isinstance(item, tuple):
                logger.warning(f"收到非预期的返回格式: {type(item)}, 值: {item}")
                continue
            if len(item) == STREAM_TUPLE_SIZE_STANDARD:
                stream_mode, chunk = item
                node_name = None
            elif len(item) == STREAM_TUPLE_SIZE_SUBGRAPH:
                node_name, stream_mode, chunk = item
            else:
                logger.warning(f"收到非预期的元组长度: {len(item)}, 值: {item}")
                continue
            for result in process_stream_chunk(stream_mode, chunk, node_name):
                yield result
    except Exception as e:
        logger.exception("流式处理消息错误")
        yield {"chunk": f"处理消息失败: {e!s}"}


def setup_langsmith_tracing():
    """设置 LangSmith 追踪环境变量

    该函数用于配置 LangSmith 追踪功能，设置必要的环境变量。
    可以在需要启用 LangSmith 追踪的模块中调用此函数。

    Returns:
        None
    """
    if settings.LANGSMITH_TRACING:
        # 设置环境变量，LangChain/LangGraph 会自动读取
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
        if settings.LANGSMITH_API_KEY:
            os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
        if settings.LANGSMITH_PROJECT:
            os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT

        # 同时设置 LANGSMITH_ 前缀的环境变量（兼容性）
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
        if settings.LANGSMITH_API_KEY:
            os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
        if settings.LANGSMITH_PROJECT:
            os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT

        logger.info(f"LangSmith 追踪已启用, 项目: {settings.LANGSMITH_PROJECT}")
    else:
        # 确保追踪被禁用
        os.environ.pop("LANGCHAIN_TRACING_V2", None)
        os.environ.pop("LANGSMITH_TRACING", None)
