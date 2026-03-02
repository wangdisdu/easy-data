"""
LLM 节点 Builder
"""

import json
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from sqlalchemy.orm import Session

from app.core.biz_error import BizError, BizErrorCode
from app.core.logging import get_logger
from app.dao.models import TbLlm
from app.graph.tool_node import build_tool_from
from app.service.agent_service import AgentGraphNodeModel, LlmNodeConfig
from app.service.llm_service import LlmService
from app.service.tool_service import ToolService

logger = get_logger(__name__)

# 脚本校验错误文案（供 TRY 规则使用）
_ERR_SCRIPT_NO_EXECUTE = "script 中必须定义一个名为 'execute' 的异步函数"
_ERR_EXECUTE_NOT_DICT = "execute 函数必须返回一个字典"


class LlmNode:
    """LLM 节点，作为 LangGraph 的可调用节点使用。

    通过 __call__(state) 实现节点逻辑，LangGraph 会将本类实例当作节点函数注册。

    Script 格式要求：
    - script 必须是一个完整的异步函数定义，函数名为 `execute`
    - 函数签名：async def execute(state, llm, tools):
    - 函数必须返回一个字典，表示要更新到 state 中的字段
    - 函数内部可以使用 state、llm、tools 三个参数
    """

    def __init__(
        self,
        script: str,
        llm: BaseChatModel,
        tools: list,
        node_id: int,
    ):
        self.script = script
        self.llm = llm
        self.tools = tools
        self.node_id = node_id

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        def _raise_no_execute() -> None:
            raise ValueError(_ERR_SCRIPT_NO_EXECUTE)

        def _raise_not_dict() -> None:
            raise TypeError(_ERR_EXECUTE_NOT_DICT)

        try:
            exec_globals = {"__builtins__": __builtins__}
            exec(self.script, exec_globals)

            execute_func = exec_globals.get("execute")
            if not execute_func:
                _raise_no_execute()

            result = execute_func(state, self.llm, self.tools)
            if hasattr(result, "__await__"):
                result = await result

            if not isinstance(result, dict):
                _raise_not_dict()

            return {**result}

        except Exception as e:
            logger.exception("执行 LLM 节点 %s 脚本失败", self.node_id)
            error_msg = f"处理消息失败: {e!s}"
            messages = state.get("messages", [])
            return {
                **state,
                "messages": [*messages, AIMessage(content=error_msg)],
            }


def create_llm_from(llm_obj: TbLlm) -> BaseChatModel:
    """从 TbLlm 创建 ChatOpenAI 实例"""
    # TbLlm 的字段：provider, api_key, base_url, model, setting
    # setting 是 JSON 格式的其他配置信息（如 temperature, max_tokens 等）
    setting_config = {}
    if llm_obj.setting:
        try:
            setting_config = json.loads(llm_obj.setting)
        except Exception:
            logger.warning("解析 LLM setting 失败: %s", llm_obj.setting)

    # 构建 ChatOpenAI 参数
    init_kwargs = {
        "model": llm_obj.model,
        "streaming": True,  # 流式执行
    }

    # 设置 base_url 和 api_key（如果存在）
    if llm_obj.base_url:
        init_kwargs["base_url"] = llm_obj.base_url
    if llm_obj.api_key:
        init_kwargs["api_key"] = llm_obj.api_key

    # 合并其他配置（如 temperature, max_tokens 等）
    init_kwargs.update(setting_config)

    return ChatOpenAI(**init_kwargs)


def build_llm_node(
    node: AgentGraphNodeModel,
    node_name: str,
    workflow: StateGraph,
    db: Session,
    node_name_map: dict,
) -> None:
    """
    构建 LLM 节点

    1. 根据 llm_id 生成 LLM 大模型
    2. 根据 tool_ids 生成 TOOL 绑定到 LLM 大模型
    3. 根据 script 执行大模型节点，为 script 生成 3 个变量：state、llm、tools

    Args:
        node: 节点模型
        node_name: 节点名称
        workflow: LangGraph 工作流
        db: 数据库会话
        node_name_map: 节点名称映射字典（未使用，保留以兼容接口）
    """
    # 解析节点配置
    try:
        config_dict = json.loads(node.config or "{}")
        config = LlmNodeConfig(**config_dict)
    except Exception as e:
        raise BizError(BizErrorCode.INVALID_PARAM, f"节点 {node.id} 配置格式错误: {e}") from e

    if not config.llm_id:
        raise BizError(BizErrorCode.INVALID_PARAM, f"节点 {node.id} 未配置 LLM")

    script = config.script or ""
    if not script:
        raise BizError(BizErrorCode.INVALID_PARAM, f"节点 {node.id} 未配置脚本")

    # 1. 根据 llm_id 生成 LLM 大模型
    llm_obj = LlmService.get_llm_by_id(db=db, llm_id=config.llm_id)
    if not llm_obj:
        raise BizError(BizErrorCode.INVALID_PARAM, f"LLM {config.llm_id} 不存在")

    llm = create_llm_from(llm_obj)

    tools = []
    for tool_id in config.tool_ids or []:
        tool_obj = ToolService.get_tool_by_id(db=db, tool_id=tool_id)
        if tool_obj:
            structured_tool = build_tool_from(tool_obj)
            if structured_tool:
                tools.append(structured_tool)

    if tools:
        llm = llm.bind_tools(tools)

    llm_node = LlmNode(script=script, llm=llm, tools=tools, node_id=node.id)
    workflow.add_node(node_name, llm_node)
