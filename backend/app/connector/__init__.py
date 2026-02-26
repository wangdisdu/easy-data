"""
数据库连接器模块
提供统一的数据库连接接口，支持多种数据库类型
"""

from app.connector.base import BaseConnector
from app.connector.factory import ConnectorFactory, get_connector

__all__ = [
    "BaseConnector",
    "ConnectorFactory",
    "get_connector",
]
