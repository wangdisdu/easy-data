#!/usr/bin/env python3
"""
从 easy_data.db 生成 app/dao/data 包的初始化数据。

将数据库中的 tb_llm、tb_tool、tb_agent、tb_agent_node、tb_agent_edge 表数据
导出为 app/dao/data 下的 Python 模块（tb_llm.py、tb_tool.py、data/tools/*、tb_agent.py、data/agents/*），
供 init_db 初始化使用。

用法:
  cd backend && python scripts/gen_init_data.py [--db path/to/easy_data.db]
  未指定 --db 时自动在当前目录或 backend 下查找 easy_data.db。
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend))

# 要导出的表及顺序
TABLES = [
    "tb_llm",
    "tb_tool",
    "tb_agent",
    "tb_agent_node",
    "tb_agent_edge",
]

META_COLS = {"create_time", "update_time", "create_user", "update_user"}


def find_db_path(given: str | None) -> str:
    if given and os.path.isfile(given):
        return given
    for base in (".", "backend"):
        path = os.path.join(base, "easy_data.db")
        if os.path.isfile(path):
            return path
    return given or "easy_data.db"


def read_rows_from_db(db_path: str) -> tuple[list, list, list, list, list]:
    """从数据库读取五张表，去掉元数据列，返回 (llm_rows, tool_rows, agent_rows, node_rows, edge_rows)。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        def table_to_rows(table_name: str) -> list[dict]:
            cur = conn.execute(f"SELECT * FROM {table_name}")
            rows = cur.fetchall()
            keys = [d[0] for d in cur.description]
            return [dict(zip(keys, row)) for row in rows]

        def drop_meta(rows: list[dict]) -> list[dict]:
            return [{k: v for k, v in r.items() if k not in META_COLS} for r in rows]

        llm_rows = drop_meta(table_to_rows("tb_llm"))
        tool_rows = drop_meta(table_to_rows("tb_tool"))
        agent_rows = drop_meta(table_to_rows("tb_agent"))
        node_rows = drop_meta(table_to_rows("tb_agent_node"))
        edge_rows = drop_meta(table_to_rows("tb_agent_edge"))
        return llm_rows, tool_rows, agent_rows, node_rows, edge_rows
    finally:
        conn.close()


# ---------- 字符串与字面量 ----------

def _py_str_multiline(s: str) -> str:
    """生成三引号多行字符串：移除内容开头的换行符，结尾只保留一个换行符。"""
    if not s:
        return '""""""'
    if '"""' in s and "'''" in s:
        return repr(s)
    s = s.lstrip("\n")
    if not s:
        return '""""""'
    s = s.rstrip("\n") + "\n"
    if '"""' in s:
        return "'''" + s + "'''"
    return '"""' + s + '"""'


def _py_repr(obj, value_indent: str = "        ") -> str:
    if obj is None:
        return "None"
    if isinstance(obj, int):
        return str(obj)
    if isinstance(obj, str):
        if "\n" in obj:
            lines = obj.split("\n")
            parts = [repr(line + "\n") for line in lines[:-1]]
            if lines[-1]:
                parts.append(repr(lines[-1]))
            elif not parts:
                return '""'
            else:
                parts.append(repr(""))
            return "(\n" + value_indent + ("\n" + value_indent).join(parts) + "\n    )"
        return repr(obj)
    return repr(obj)


def _rows_repr(rows: list[dict]) -> str:
    if not rows:
        return "[]"
    parts = []
    for row in rows:
        item = "{" + ", ".join(f"{repr(k)}: {_py_repr(v)}" for k, v in row.items()) + "}"
        parts.append(item)
    return "[\n    " + ",\n    ".join(parts) + "\n]"


def _dict_to_py_literal(d: dict) -> str:
    parts = []
    for k, v in d.items():
        if isinstance(v, str):
            parts.append(f"{repr(k)}: {repr(v)}")
        elif isinstance(v, (int, float, bool)) or v is None:
            parts.append(f"{repr(k)}: {v}")
        else:
            parts.append(f"{repr(k)}: {repr(v)}")
    return "{" + ", ".join(parts) + "}"


def _single_node_config_to_py(obj: dict) -> str:
    parts = []
    for k, v in obj.items():
        if k == "script" and isinstance(v, str):
            parts.append(f"{repr(k)}: {_py_str_multiline(v)}")
        elif isinstance(v, str):
            parts.append(f"{repr(k)}: {repr(v)}")
        elif isinstance(v, (int, float, bool)) or v is None:
            parts.append(f"{repr(k)}: {v}")
        elif isinstance(v, list):
            parts.append(f"{repr(k)}: {repr(v)}")
        else:
            parts.append(f"{repr(k)}: {repr(v)}")
    return "{\n    " + ",\n    ".join(parts) + "\n}"


def _safe_module_name(tool_name: str, index: int) -> str:
    safe = "".join(c if c.isalnum() or c == "_" else "_" for c in tool_name)
    return f"tool_{index:02d}_{safe}"


# ---------- 写 tb_llm ----------

def write_tb_llm(data_dir: Path, llm_rows: list[dict]) -> None:
    text = f'''"""LLM 表初始化数据。"""

LLM_ROWS = {_rows_repr(llm_rows)}
'''
    (data_dir / "tb_llm.py").write_text(text, encoding="utf-8")


# ---------- 写 tools ----------

def write_tool_file(dir_path: Path, index: int, row: dict) -> str:
    name = row["tool"]
    mod_name = _safe_module_name(name, index)
    desc = _py_str_multiline(row["description"])
    content = _py_str_multiline(row["content"])
    text = f'''"""工具初始化数据: {name}"""

DESCRIPTION = {desc}

CONTENT = {content}

ROW = {{
    "tool": {repr(name)},
    "description": DESCRIPTION,
    "parameters": {repr(row["parameters"])},
    "content": CONTENT,
    "extend": {repr(row["extend"])},
    "id": {row["id"]},
}}
'''
    (dir_path / f"{mod_name}.py").write_text(text, encoding="utf-8")
    return mod_name


def write_tb_tool(data_dir: Path, mod_names: list[str]) -> None:
    imports = "\n".join(f"from app.dao.data.tools.{m} import ROW as _row_{m}" for m in mod_names)
    list_parts = ", ".join(f"_row_{m}" for m in mod_names)
    text = f'''"""TOOL_ROWS：由 data/tools/* 各模块组成，供 init_db 使用。"""

{imports}

TOOL_ROWS = [
    {list_parts}
]
'''
    (data_dir / "tb_tool.py").write_text(text, encoding="utf-8")


# ---------- 写 agents ----------

def write_agent_file(
    dir_path: Path,
    index: int,
    row: dict,
    nodes: list[dict],
    edges: list[dict],
) -> str:
    desc = _py_str_multiline(row["description"])
    config_raw = row.get("config") or ""
    if config_raw and config_raw.strip():
        try:
            config_obj = json.loads(config_raw)
            config_repr = _dict_to_py_literal(config_obj)
        except Exception:
            config_repr = repr(config_raw)
    else:
        config_repr = "None"

    config_var_by_index: dict[int, str] = {}
    node_config_lines: list[str] = []
    for i, n in enumerate(nodes):
        node_num = i + 1
        cfg = n.get("config")
        if not cfg or not str(cfg).strip():
            continue
        try:
            obj = json.loads(cfg)
        except Exception:
            continue
        var_name = f"NODE{node_num}_CONFIG"
        config_var_by_index[node_num] = var_name
        node_config_lines.append(f"{var_name} = {_single_node_config_to_py(obj)}")
    node_config_section = "\n\n".join(node_config_lines) if node_config_lines else "# 无带 config 的节点"

    node_rows_entries = []
    for i, n in enumerate(nodes):
        node_num = i + 1
        c_expr = f"json.dumps({config_var_by_index[node_num]})" if node_num in config_var_by_index else "None"
        node_rows_entries.append(
            f'{{"agent_id": {n["agent_id"]}, "name": {repr(n["name"])}, '
            f'"node_type": {repr(n["node_type"])}, "config": {c_expr}, '
            f'"description": {repr(n.get("description"))}, "extend": {repr(n.get("extend"))}, "id": {n["id"]}}}'
        )
    node_rows_str = "[\n    " + ",\n    ".join(node_rows_entries) + "\n]"
    edge_rows_str = "[\n    " + ",\n    ".join(repr(e) for e in edges) + "\n]"

    text = f'''"""智能体初始化数据: {row["name"]}（含本 agent 的节点与边）"""

import json

DESCRIPTION = {desc}

CONFIG = {config_repr}

ROW = {{
    "name": {repr(row["name"])},
    "description": DESCRIPTION,
    "config": json.dumps(CONFIG) if CONFIG else "",
    "status": {repr(row["status"])},
    "extend": {repr(row["extend"])},
    "id": {row["id"]},
}}

# 节点 config 以独立变量声明（仅对有 config 的节点），script 用三引号
{node_config_section}

NODE_ROWS = {node_rows_str}

EDGE_ROWS = {edge_rows_str}
'''
    (dir_path / f"agent_{index}.py").write_text(text, encoding="utf-8")
    return f"agent_{index}"


def write_tb_agent(data_dir: Path, agent_mods: list[str]) -> None:
    row_imports = "\n".join(
        f"from app.dao.data.agents.{m} import ROW as _arow_{m}" for m in agent_mods
    )
    node_imports = "\n".join(
        f"from app.dao.data.agents.{m} import NODE_ROWS as _nodes_{m}" for m in agent_mods
    )
    edge_imports = "\n".join(
        f"from app.dao.data.agents.{m} import EDGE_ROWS as _edges_{m}" for m in agent_mods
    )
    row_list = ", ".join(f"_arow_{m}" for m in agent_mods)
    node_concat = " + ".join(f"_nodes_{m}" for m in agent_mods)
    edge_concat = " + ".join(f"_edges_{m}" for m in agent_mods)
    text = f'''"""智能体初始化数据（由 data/agents/* 聚合）：AGENT_ROWS、AGENT_NODE_ROWS、AGENT_EDGE_ROWS。"""

{row_imports}

{node_imports}

{edge_imports}

AGENT_ROWS = [{row_list}]

AGENT_NODE_ROWS = {node_concat}

AGENT_EDGE_ROWS = {edge_concat}
'''
    (data_dir / "tb_agent.py").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="从 easy_data.db 生成 app/dao/data 包的初始化数据"
    )
    parser.add_argument(
        "--db",
        default=None,
        help="数据库文件路径，默认自动查找 easy_data.db",
    )
    args = parser.parse_args()

    db_path = find_db_path(args.db)
    if not os.path.isfile(db_path):
        print(f"错误: 未找到数据库文件 {db_path}", file=sys.stderr)
        sys.exit(1)

    data_dir = backend / "app" / "dao" / "data"
    tools_dir = data_dir / "tools"
    agents_dir = data_dir / "agents"
    tools_dir.mkdir(parents=True, exist_ok=True)
    agents_dir.mkdir(parents=True, exist_ok=True)

    llm_rows, tool_rows, agent_rows, node_rows, edge_rows = read_rows_from_db(db_path)

    write_tb_llm(data_dir, llm_rows)
    print("tb_llm.py")

    mod_names = []
    for i, row in enumerate(tool_rows, start=1):
        mod_names.append(write_tool_file(tools_dir, i, row))
    write_tb_tool(data_dir, mod_names)
    print(f"tools: {len(mod_names)} 个文件 + tb_tool.py")

    agent_mods = []
    for i, row in enumerate(agent_rows, start=1):
        nodes_i = [n for n in node_rows if n["agent_id"] == row["id"]]
        edges_i = [e for e in edge_rows if e["agent_id"] == row["id"]]
        agent_mods.append(write_agent_file(agents_dir, i, row, nodes_i, edges_i))
    write_tb_agent(data_dir, agent_mods)
    print(f"agents: {len(agent_mods)} 个文件 + tb_agent.py")

    print(f"已根据 {os.path.abspath(db_path)} 生成 app/dao/data 初始化数据。")


if __name__ == "__main__":
    main()
