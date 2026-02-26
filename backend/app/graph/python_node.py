"""
Python 节点 Builder

参考 LlmNode：PythonNodeConfig.script 定义 execute 方法，__call__ 中 exec script 后调用 execute(state)。
"""

import json
from typing import Any

from langgraph.graph import StateGraph

from app.core.biz_error import BizError, BizErrorCode
from app.core.logging import get_logger
from app.services.agents_service import AgentGraphNodeModel, PythonNodeConfig

logger = get_logger(__name__)

_ERR_SCRIPT_NO_EXECUTE = "script 中必须定义一个名为 'execute' 的函数"
_ERR_EXECUTE_NOT_DICT = "execute 函数必须返回一个字典"


class PythonNode:
    """Python 节点，作为 LangGraph 的可调用节点使用。

    通过 __call__(state) 实现节点逻辑。Script 格式要求（参考 LlmNode）：
    - script 必须定义函数名为 `execute`
    - 函数签名：def execute(state): 或 async def execute(state):
    - 函数必须返回一个字典，表示要更新到 state 中的字段
    """

    def __init__(self, script: str, node_id: int):
        self.script = script
        self.node_id = node_id

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        def _raise_no_execute() -> None:
            raise ValueError(_ERR_SCRIPT_NO_EXECUTE)

        def _raise_not_dict() -> None:
            raise TypeError(_ERR_EXECUTE_NOT_DICT)

        try:
            exec_globals: dict[str, Any] = {"__builtins__": __builtins__}
            exec(self.script, exec_globals)

            execute_func = exec_globals.get("execute")
            if not callable(execute_func):
                _raise_no_execute()

            result = execute_func(state)
            if hasattr(result, "__await__"):
                result = await result

            if not isinstance(result, dict):
                _raise_not_dict()

            return {**result}

        except Exception:
            logger.exception("执行 Python 节点 %s 脚本失败", self.node_id)
            return state


def build_python_node(
    node: AgentGraphNodeModel,
    node_name: str,
    workflow: StateGraph,
) -> None:
    """
    构建 python 节点

    Args:
        node: 节点模型
        node_name: 节点名称
        workflow: LangGraph 工作流
    """
    try:
        config_dict = json.loads(node.config or "{}")
        config = PythonNodeConfig(**config_dict)
    except Exception as e:
        raise BizError(BizErrorCode.INVALID_PARAM, f"节点 {node.id} 配置格式错误: {e}") from e

    if not config.script:
        raise BizError(BizErrorCode.INVALID_PARAM, f"节点 {node.id} 未配置脚本")

    python_node = PythonNode(script=config.script, node_id=node.id)
    workflow.add_node(node_name, python_node)
