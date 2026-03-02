"""
Tool 节点 Builder
"""

import json
from typing import Any, Optional

from langchain_core.tools import StructuredTool
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from sqlalchemy.orm import Session

from app.core.biz_error import BizError, BizErrorCode
from app.core.logging import get_logger
from app.dao.models import TbTool
from app.service.agent_service import AgentGraphNodeModel, ToolNodeConfig
from app.service.tool_service import ToolService

logger = get_logger(__name__)


def _get_callable_from_content(content: str, tool_name: str) -> Optional[Any]:
    """从脚本 content 中执行并取出名为 tool_name 的可调用对象。"""
    exec_globals: dict[str, Any] = {"__builtins__": __builtins__}
    exec(content, exec_globals)
    return exec_globals.get(tool_name)


def build_tool_from(tool_obj: TbTool) -> Optional[StructuredTool]:
    """仅从 TbTool 生成 StructuredTool，使用 StructuredTool.from_function。

    - name/description 取自 TbTool.tool、TbTool.description
    - 若 TbTool.content 有内容：执行脚本得到名为 TbTool.tool 的可调用对象，作为 func
    - 若 TbTool.content 为空：使用占位函数，返回“未配置实现”提示
    """
    name = tool_obj.tool
    description = (tool_obj.description or "").strip() or f"工具 {name}"

    if tool_obj.content and tool_obj.content.strip():
        try:
            func = _get_callable_from_content(tool_obj.content, name)
            if not callable(func):
                logger.warning("TbTool.content 中未找到可调用对象: %s", name)
                func = None
        except Exception:
            logger.exception("执行 TbTool.content 失败")
            func = None
    else:
        func = None

    if func is None:
        # 占位：无实现时仍返回一个 StructuredTool，调用时返回提示
        def _stub() -> str:
            return "该工具未配置代码实现（TbTool.content 为空）"

        func = _stub

    return StructuredTool.from_function(
        func=func,
        name=name,
        description=description,
        infer_schema=True,
    )


def build_tool_node(
    node: AgentGraphNodeModel,
    node_name: str,
    workflow: StateGraph,
    db: Session,
) -> None:
    """
    构建 tool 节点

    Args:
        node: 节点模型
        node_name: 节点名称
        workflow: LangGraph 工作流
        db: 数据库会话
    """
    # 解析节点配置
    try:
        config_dict = json.loads(node.config or "{}")
        config = ToolNodeConfig(**config_dict)
    except Exception as e:
        raise BizError(BizErrorCode.INVALID_PARAM, f"节点 {node.id} 配置格式错误: {e}") from e

    tool_ids = config.tool_ids or []
    if not tool_ids:
        raise BizError(BizErrorCode.INVALID_PARAM, f"节点 {node.id} 未配置工具")

    tools = []
    for tool_id in tool_ids:
        tool_obj = ToolService.get_tool_by_id(db=db, tool_id=tool_id)
        if tool_obj:
            structured_tool = build_tool_from(tool_obj)
            if structured_tool:
                tools.append(structured_tool)

    if not tools:
        raise BizError(BizErrorCode.INVALID_PARAM, f"节点 {node.id} 的工具不存在")

    tool_node = ToolNode(tools)

    workflow.add_node(node_name, tool_node)
