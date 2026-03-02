"""
初始化数据包：LLM / 工具 / 智能体 ROWS，供 init_db 初始化使用。

- LLM_ROWS: app.dao.data.tb_llm
- TOOL_ROWS: app.dao.data.tb_tool（由 data/tools/* 各文件组成）
- AGENT_ROWS, AGENT_NODE_ROWS, AGENT_EDGE_ROWS: app.dao.data.tb_agent（由 data/agents/* 各文件组成）
"""

from app.dao.data.tb_agent import AGENT_EDGE_ROWS, AGENT_NODE_ROWS, AGENT_ROWS
from app.dao.data.tb_llm import LLM_ROWS
from app.dao.data.tb_tool import TOOL_ROWS

__all__ = [
    "AGENT_EDGE_ROWS",
    "AGENT_NODE_ROWS",
    "AGENT_ROWS",
    "LLM_ROWS",
    "TOOL_ROWS",
]
