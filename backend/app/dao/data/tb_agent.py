"""智能体初始化数据（由 data/agents/* 聚合）：AGENT_ROWS、AGENT_NODE_ROWS、AGENT_EDGE_ROWS。"""

from app.dao.data.agents.agent_1 import EDGE_ROWS as _edges_agent_1
from app.dao.data.agents.agent_1 import NODE_ROWS as _nodes_agent_1
from app.dao.data.agents.agent_1 import ROW as _arow_agent_1
from app.dao.data.agents.agent_2 import EDGE_ROWS as _edges_agent_2
from app.dao.data.agents.agent_2 import NODE_ROWS as _nodes_agent_2
from app.dao.data.agents.agent_2 import ROW as _arow_agent_2
from app.dao.data.agents.agent_3 import EDGE_ROWS as _edges_agent_3
from app.dao.data.agents.agent_3 import NODE_ROWS as _nodes_agent_3
from app.dao.data.agents.agent_3 import ROW as _arow_agent_3
from app.dao.data.agents.agent_4 import EDGE_ROWS as _edges_agent_4
from app.dao.data.agents.agent_4 import NODE_ROWS as _nodes_agent_4
from app.dao.data.agents.agent_4 import ROW as _arow_agent_4
from app.dao.data.agents.agent_5 import EDGE_ROWS as _edges_agent_5
from app.dao.data.agents.agent_5 import NODE_ROWS as _nodes_agent_5
from app.dao.data.agents.agent_5 import ROW as _arow_agent_5

AGENT_ROWS = [_arow_agent_1, _arow_agent_2, _arow_agent_3, _arow_agent_4, _arow_agent_5]

AGENT_NODE_ROWS = _nodes_agent_1 + _nodes_agent_2 + _nodes_agent_3 + _nodes_agent_4 + _nodes_agent_5

AGENT_EDGE_ROWS = _edges_agent_1 + _edges_agent_2 + _edges_agent_3 + _edges_agent_4 + _edges_agent_5
