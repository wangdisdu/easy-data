"""
Agent工具模块
提供Agent相关的工具函数
"""

import json
import os
import re
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("graph.agent_utils")


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


def extract_json_message(content: str) -> Optional[str]:
    """
    从文本内容中提取JSON字符串

    用于从LLM响应消息中提取完整的JSON内容，支持多种格式：
    1. 直接JSON格式
    2. Markdown代码块格式（```json ... ```）
    3. 文本中的JSON对象

    提取策略（按优先级）：
    1. 尝试直接解析整个内容为JSON
    2. 从markdown代码块中提取JSON（```json ... ``` 或 ``` ... ```）
    3. 从文本中提取第一个完整的JSON对象

    Args:
        content: 待提取的文本内容

    Returns:
        提取的JSON字符串，如果提取失败返回None
    """
    if not content or not content.strip():
        return None

    content = content.strip()

    # 策略1: 尝试直接解析整个内容为JSON
    try:
        json.loads(content)
        logger.debug(f"[JSON-EXTRACTOR] 策略1成功：直接解析JSON，长度: {len(content)} 字符")
        return content
    except json.JSONDecodeError:
        pass

    # 策略2：尝试从markdown代码块中提取JSON
    # 匹配 ```json ... ``` 或 ``` ... ```（支持多行）
    json_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
    matches = re.findall(json_pattern, content, re.DOTALL)
    if matches:
        # 取最长的匹配（通常是完整的JSON）
        semantic_json = max(matches, key=len)
        # 验证是否为有效JSON
        try:
            json.loads(semantic_json)
            logger.debug(
                f"[JSON-EXTRACTOR] 策略2成功：从markdown代码块提取JSON，长度: {len(semantic_json)} 字符"
            )
            return semantic_json
        except json.JSONDecodeError:
            pass

    # 策略3：尝试提取第一个完整的JSON对象
    # 使用更精确的正则表达式匹配JSON对象（支持嵌套）
    json_obj_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
    json_matches = re.findall(json_obj_pattern, content, re.DOTALL)
    if json_matches:
        # 验证每个匹配是否为有效JSON，取最长的有效JSON
        valid_jsons = []
        for match in json_matches:
            try:
                json.loads(match)
                valid_jsons.append(match)
            except json.JSONDecodeError:
                continue
        if valid_jsons:
            semantic_json = max(valid_jsons, key=len)
            logger.debug(
                f"[JSON-EXTRACTOR] 策略3成功：从文本中提取JSON，长度: {len(semantic_json)} 字符"
            )
            return semantic_json

    # 所有策略都失败
    logger.warning("[JSON-EXTRACTOR] 所有提取策略都失败，无法提取有效JSON")
    return None
