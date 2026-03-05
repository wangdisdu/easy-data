"""
AdminDeepAgent - DeepAgents 版本的系统管理智能体

基于 deepagents 的 create_deep_agent，通过 SKILL 实现：
- 数据源管理
- 数据模型管理
- 数据模型分析
- 系统健康检查

本实现只提供异步流式接口 astream，便于与现有 WebSocket 流式输出逻辑对接。
"""

from pathlib import Path
from typing import Any, AsyncIterator, Optional

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.agent.base_agent import BaseAgent
from app.core.config import settings
from app.core.logging import get_logger
from app.tool import (
    tool_check_data_source_connection,
    tool_check_models_exist_in_database,
    tool_execute_sql_data_model,
    tool_execute_system_sql,
    tool_import_data_models_by_data_source,
    tool_test_data_source_setting,
)

logger = get_logger("admin_deep_agent")

# 系统库能力由 SKILL 生成 SQL + tool_execute_system_sql 完成；外库/复杂流程保留以下工具
ADMIN_DEEP_TOOLS = [
    tool_execute_system_sql,
    tool_test_data_source_setting,
    tool_check_data_source_connection,
    tool_import_data_models_by_data_source,
    tool_check_models_exist_in_database,
    tool_execute_sql_data_model,
]

ADMIN_DEEP_SYSTEM_PROMPT = """你是一个系统管理助手，负责根据用户问题选择并执行相应能力。

## 能力范围（通过 SKILL 提供）

1. **数据源管理**：新增、查询、测试、更新、删除数据源
2. **数据模型管理**：查阅/导入/删除数据模型（按数据源）
3. **数据分析**：对单个数据模型执行探索性 SQL 分析并生成报告，可选保存语义与总结
4. **系统自检**：按步骤检查数据源列表、连接、模型存在性、语义与新鲜度；无数据源时引导用户创建

请根据用户意图，优先匹配上述 SKILL 描述，按对应 SKILL 的说明与工具完成请求。若请求不属于任何能力范围，礼貌说明并提示可用能力。"""


def _get_skills_dir() -> Path:
    """返回 backend/skills 的绝对路径，供 deepagents 加载 SKILL。"""
    # backend/app/agent/admin_deep_agent.py -> backend
    backend_root = Path(__file__).resolve().parent.parent.parent
    return backend_root / "skills"


def create_admin_deep_agent(
    user_id: Optional[int] = None,
) -> Any:
    """
    创建 Admin DeepAgent 实例。

    使用 deepagents.create_deep_agent，绑定当前项目 LLM 配置、全部系统管理工具及 4 个 SKILL 目录。

    Args:
        user_id: 预留，与现有 Agent 接口一致；工具层若需用户上下文可在此扩展。

    Returns:
        编译后的 LangGraph（CompiledStateGraph），支持 invoke / ainvoke。
    """
    try:
        from deepagents import create_deep_agent
    except ImportError as e:
        logger.error("deepagents 未安装，无法创建 Admin DeepAgent: %s", e)
        raise

    skills_dir = _get_skills_dir()
    if not skills_dir.is_dir():
        logger.warning("SKILL 目录不存在: %s，DeepAgent 将不加载任何 SKILL", skills_dir)

    llm = ChatOpenAI(
        base_url=settings.OPENAI_BASE_URL,
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL or "gpt-4o",
        streaming=False,
    )

    backend_root = skills_dir.parent
    # 相对 backend root 的 skills 目录；deepagents 要求路径相对 backend 的 root_dir，使用正斜杠
    skills_path_relative_to_backend = "skills/"

    try:
        from deepagents.backends.filesystem import FilesystemBackend
    except ImportError:
        FilesystemBackend = None

    if FilesystemBackend is not None and skills_dir.is_dir():
        agent = create_deep_agent(
            model=llm,
            tools=ADMIN_DEEP_TOOLS,
            system_prompt=ADMIN_DEEP_SYSTEM_PROMPT,
            backend=FilesystemBackend(root_dir=str(backend_root)),
            skills=[skills_path_relative_to_backend],
        )
    else:
        agent = create_deep_agent(
            model=llm,
            tools=ADMIN_DEEP_TOOLS,
            system_prompt=ADMIN_DEEP_SYSTEM_PROMPT,
        )
    return agent


class AdminDeepAgent(BaseAgent):
    """
    DeepAgents 版系统管理智能体。

    只提供异步流式接口 astream，便于与 WebSocket 的 _process_message_stream 对接。
    """

    def __init__(self, user_id: Optional[int] = None):
        super().__init__(user_id=user_id)
        self.workflow = create_admin_deep_agent(user_id=user_id)

    def _build_initial_state(self, session_id: str, message: str) -> dict[str, Any]:
        """
        构建 DeepAgent 的初始状态：将用户输入放入 messages 作为 HumanMessage，
        以便 create_deep_agent 的图能正确消费用户消息。
        """
        return {
            "messages": [HumanMessage(content=message)],
            "session_id": session_id,
            "user_id": self.user_id,
        }

