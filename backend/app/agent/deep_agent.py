"""
agents 目录智能体定义与运行。

按规范使用 AGENT.md（系统提示词）、可选 MEMORY.md、TOOLS.json、skills/、SUB_AGENTS.json。
支持所有 agents（含 main、admin、text_to_sql）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from deepagents import CompiledSubAgent, create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.agent.agent_utils import astream_workflow
from app.core.config import EASY_HOME, settings
from app.core.logging import get_logger
from app.tool import (
    tool_check_data_source_connection,
    tool_check_models_exist_in_database,
    tool_execute_sql_data_model,
    tool_execute_sql_data_source,
    tool_execute_system_sql,
    tool_import_data_models_by_data_source,
    tool_test_data_source_setting,
)

logger = get_logger(__name__)


AGENTS_DIR: Path = EASY_HOME / "agents"


def list_deepagents() -> list[str]:
    """遍历 agents 目录，返回含 AGENT.md 的子目录智能体列表。"""
    result: list[str] = []
    if AGENTS_DIR.is_dir():
        for sub in sorted(AGENTS_DIR.iterdir()):
            if sub.is_dir() and (sub / "AGENT.md").exists():
                result.append(sub.name)
    return result


TOOL_REGISTRY: dict[str, object] = {
    "tool_check_data_source_connection": tool_check_data_source_connection,
    "tool_check_models_exist_in_database": tool_check_models_exist_in_database,
    "tool_execute_sql_data_model": tool_execute_sql_data_model,
    "tool_execute_sql_data_source": tool_execute_sql_data_source,
    "tool_execute_system_sql": tool_execute_system_sql,
    "tool_import_data_models_by_data_source": tool_import_data_models_by_data_source,
    "tool_test_data_source_setting": tool_test_data_source_setting,
}


def create_llm(*, streaming: bool = True) -> ChatOpenAI:
    """统一创建 ChatOpenAI，供子智能体与主智能体复用。"""
    return ChatOpenAI(
        base_url=settings.OPENAI_BASE_URL,
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        streaming=streaming,
    )


class DeepAgent:
    """
    agents 目录下单个智能体的定义与运行类
    """

    def __init__(self, agent_id: str, user_id: Optional[int] = None) -> None:
        """
        Args:
            agent_id: 智能体 id，对应 agents 下目录名（如 main、admin、text_to_sql）。
            user_id: 用户 ID（预留）。
        """
        self.agent_id = (agent_id or "").strip().lower()
        self.user_id = user_id
        self.agent_home = Path(AGENTS_DIR) / self.agent_id

        # 加载配置与资源
        self.agent_doc = self._load_agent_doc()
        self.tools = self._load_tools()
        self.subagents: list[DeepAgent] = []
        self._load_sub_agents()
        # 编译 workflow
        self.deep_agent: Any = None
        self.build()

    def _load_agent_doc(self) -> str:
        """加载 AGENT.md 作为系统提示词。"""
        path = self.agent_home / "AGENT.md"
        if not path.exists():
            msg = f"目录智能体 {self.agent_id} 缺少 AGENT.md"
            raise ValueError(msg)
        return path.read_text(encoding="utf-8")

    def _load_tools(self) -> list:
        """从 TOOLS.json 加载工具列表，无文件或解析失败则返回空列表。"""
        path = self.agent_home / "TOOLS.json"
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
            tools = []
            for name in data:
                if isinstance(name, str) and name in TOOL_REGISTRY:
                    tools.append(TOOL_REGISTRY[name])
                else:
                    logger.warning("未知工具名: %s", name)
            return tools
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("解析 TOOLS.json 失败 %s: %s", path, e)
            return []

    def _load_sub_agents(self) -> None:
        """
        加载子智能体：读取 SUB_AGENTS.json，为每个 id 创建 DeepAgent，
        生成 CompiledSubAgent 列表供 create_deep_agent 使用，
        并保存 sub_agent_instances 供直接路由（如 /admin）。
        """
        path = self.agent_home / "SUB_AGENTS.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, list) or not data:
                return
            ids = [str(x).strip().lower() for x in data if x]
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("解析 SUB_AGENTS.json 失败 %s: %s", path, e)
            return

        for sub_id in ids:
            try:
                sub = DeepAgent(agent_id=sub_id, user_id=self.user_id)
                self.subagents.append(sub)
            except (ValueError, Exception) as e:
                logger.warning("加载子智能体 %s 失败: %s", sub_id, e)

    def build(self) -> Any:
        """
        编译 workflow：agent_doc 作为 system_prompt，memory 仅加载 MEMORY.md（若有），
        组装 skills、tools、subagents，调用 create_deep_agent。
        """
        kwargs: dict[str, Any] = {
            "model": create_llm(streaming=True),
            "system_prompt": self.agent_doc,
            "backend": FilesystemBackend(root_dir=str(self.agent_home)),
        }
        mem_path = self.agent_home / "MEMORY.md"
        if mem_path.exists():
            kwargs["memory"] = [str(mem_path)]
        skills_path = self.agent_home / "skills"
        if skills_path.is_dir():
            kwargs["skills"] = [str(skills_path)]
        if self.tools:
            kwargs["tools"] = self.tools
        if self.subagents:
            kwargs["subagents"] = [
                CompiledSubAgent(
                    name=sub.agent_id,
                    description=sub.agent_doc,
                    runnable=sub.deep_agent,
                )
                for sub in self.subagents
            ]

        self.deep_agent = create_deep_agent(**kwargs)
        return self.deep_agent

    def _build_initial_state(self, session_id: str, message: str) -> dict[str, Any]:
        """构建流式调用的初始状态。"""
        return {
            "messages": [HumanMessage(content=message)],
            "session_id": session_id,
            "user_id": self.user_id,
        }

    async def astream(
        self, session_id: str, message: str
    ) -> "AsyncIterator[dict[str, Any]]":  # noqa: UP037
        """
        流式执行，产出与 AgentExecutor.astream 相同格式的 chunk 字典。
        含子智能体时启用 has_subgraphs 以推送子图流式输出。
        """
        initial_state = self._build_initial_state(session_id, message)
        async for chunk in astream_workflow(
            self.deep_agent, initial_state, has_subgraphs=bool(self.subagents)
        ):
            yield chunk
