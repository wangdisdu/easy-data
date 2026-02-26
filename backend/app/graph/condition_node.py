"""
Condition 节点 Builder

不向 workflow 增加 condition 节点，仅实现：
  workflow.add_conditional_edges(from_node, _route_mapping, path_map)

脚本需定义 execute(state) 并返回一个字符串（须在 route_mapping 中），例如：
  def execute(state):
      messages = state.get("messages", [])
      if not messages:
          return "no_tool"
      last_message = messages[-1]
      has_tool = hasattr(last_message, "tool_calls") and bool(last_message.tool_calls)
      return "tool" if has_tool else "no_tool"
"""

import json
from typing import Any

from langgraph.graph import END, StateGraph

from app.core.biz_error import BizError, BizErrorCode
from app.core.logging import get_logger
from app.services.agents_service import AgentGraphNodeModel, ConditionNodeConfig

logger = get_logger(__name__)

DEFAULT_ROUTE = "__default__"
_ERR_NO_EXECUTE = "script 中必须定义可调用的 execute(state) 函数"


class ConditionRouteMapping:
    """条件路由：执行 script 中定义的 execute(state)，根据返回值在 path_map 中选择下一节点。"""

    def __init__(self, script: str, path_map: dict[str, Any], node_id: int):
        self.script = script
        self.path_map = path_map
        self.node_id = node_id
        self._execute_func: Any = None
        self._exec_globals: dict[str, Any] = {}

    def _ensure_compiled(self) -> None:
        def _raise_no_execute() -> None:
            raise ValueError(_ERR_NO_EXECUTE)

        if self._execute_func is not None:
            return
        self._exec_globals = {"__builtins__": __builtins__}
        exec(self.script, self._exec_globals)
        self._execute_func = self._exec_globals.get("execute")
        if not callable(self._execute_func):
            _raise_no_execute()

    def __call__(self, state: dict[str, Any]) -> str:
        try:
            self._ensure_compiled()
            route_value = self._execute_func(state)
            if not isinstance(route_value, str):
                route_value = str(route_value)
            return route_value if route_value in self.path_map else DEFAULT_ROUTE
        except Exception:
            logger.exception("执行条件节点 %s 脚本失败", self.node_id)
            return DEFAULT_ROUTE


def build_condition_node(
    node: AgentGraphNodeModel,
    workflow: StateGraph,
    edges: list[Any],
    node_name_map: dict[int, str],
) -> None:
    """
    仅添加条件边，不增加节点。

    找到指向本 condition 的边，得到 from_node；用 script 计算 route_value（字符串），
    用 route_mapping 与 from_node_slot 构建 path_map，执行：
      workflow.add_conditional_edges(from_node, _route_mapping, path_map)
    """
    try:
        config_dict = json.loads(node.config or "{}")
        config = ConditionNodeConfig(**config_dict)
    except Exception as e:
        raise BizError(BizErrorCode.INVALID_PARAM, f"节点 {node.id} 配置格式错误: {e}") from e

    if not config.script:
        raise BizError(BizErrorCode.INVALID_PARAM, f"节点 {node.id} 未配置脚本")
    if not config.route_mapping:
        raise BizError(BizErrorCode.INVALID_PARAM, f"节点 {node.id} 未配置 route_mapping")

    # 指向本 condition 的边 -> 得到 from_node
    in_edges = [e for e in edges if e.to_node_id == node.id]
    if not in_edges:
        raise BizError(BizErrorCode.INVALID_PARAM, f"条件节点 {node.id} 无入边")
    from_node_id = in_edges[0].from_node_id
    from_node_name = node_name_map.get(from_node_id)
    if not from_node_name:
        raise BizError(BizErrorCode.INVALID_PARAM, f"条件节点 {node.id} 的入边源节点不在图中")

    # 本 condition 的出边 -> path_map（route_mapping[slot] -> 目标节点名）
    route_mapping = config.route_mapping
    path_map: dict[str, Any] = {}
    for e in edges:
        if e.from_node_id != node.id:
            continue
        target_name = node_name_map.get(e.to_node_id)
        if target_name and e.from_node_slot < len(route_mapping):
            path_map[route_mapping[e.from_node_slot]] = target_name
    path_map[DEFAULT_ROUTE] = END

    route_mapping = ConditionRouteMapping(
        script=config.script,
        path_map=path_map,
        node_id=node.id,
    )
    # 供 LangSmith 等 trace 显示：实例无 __name__ 会显示为 "Unnamed"
    route_mapping.__name__ = f"condition_{node.id}"
    workflow.add_conditional_edges(from_node_name, route_mapping, path_map)
