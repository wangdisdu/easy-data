from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from app.connector.models import ConnectionTestResult


class BaseConnector(ABC):
    """
    数据库连接器基类，定义统一的数据库操作接口
    """

    def __init__(self, **kwargs):
        """
        初始化连接器

        Args:
            kwargs: 连接数据库所需的参数
                - host: 数据库主机地址
                - port: 数据库端口
                - username: 数据库用户名
                - password: 数据库密码
                - database: 数据库名称
                - other: 其他特定数据库的参数
        """
        self.host = kwargs.get("host")
        self.port = kwargs.get("port")
        self.username = kwargs.get("username")
        self.password = kwargs.get("password")
        self.database = kwargs.get("database")
        self.extra_params = kwargs.get("extra_params", {})
        self.connection = None

    @abstractmethod
    def test_connection(self) -> ConnectionTestResult:
        """
        测试数据库连接是否成功

        Returns:
            ConnectionTestResult: 连接结果，包含success和error字段
                success: True表示连接成功，False表示连接失败
                error: 连接失败时的错误信息
        """

    @abstractmethod
    def get_server_info(self) -> dict[str, Any]:
        """
        获取服务器基本信息

        Returns:
            Dict[str, Any]: 服务器信息，包括版本、类型、名称等
        """

    @abstractmethod
    def get_databases(self) -> list[str]:
        """
        获取服务器上所有数据库名称

        Returns:
            List[str]: 数据库名称列表
        """

    def get_schemas(self, database: Optional[str] = None) -> list[str]:
        """
        获取指定数据库下的所有schema名称

        Args:
            database: 数据库名称，默认为当前连接的数据库

        Returns:
            List[str]: schema名称列表
        """
        # 默认实现，不支持schema的数据库返回空列表
        return []

    @abstractmethod
    def get_tables(self, database: Optional[str] = None, schema: Optional[str] = None) -> list[str]:
        """
        获取指定数据库和schema下的所有表名

        Args:
            database: 数据库名称，默认为当前连接的数据库
            schema: schema名称，默认为数据库默认schema

        Returns:
            List[str]: 表名列表
        """

    @abstractmethod
    def get_views(self, database: Optional[str] = None, schema: Optional[str] = None) -> list[str]:
        """
        获取指定数据库和schema下的所有视图名

        Args:
            database: 数据库名称，默认为当前连接的数据库
            schema: schema名称，默认为数据库默认schema

        Returns:
            List[str]: 视图名列表
        """

    @abstractmethod
    def get_table_structure(
        self, table_name: str, database: Optional[str] = None, schema: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        获取指定数据库、schema和表名的结构信息

        Args:
            table_name: 表名
            database: 数据库名称，默认为当前连接的数据库
            schema: schema名称，默认为数据库默认schema

        Returns:
            List[Dict[str, Any]]: 表结构信息，包括字段名、类型、是否为主键等
        """

    @abstractmethod
    def execute_query(
        self, query: str, params: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        """
        执行SQL查询

        Args:
            query: SQL查询语句
            params: 查询参数

        Returns:
            List[Dict[str, Any]]: 查询结果
        """

    @abstractmethod
    def close(self):
        """
        关闭数据库连接
        """
