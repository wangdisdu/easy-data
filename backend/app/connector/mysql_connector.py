from typing import Any, Optional

import pymysql

from app.connector.base import BaseConnector
from app.connector.models import ConnectionTestResult
from app.core.json_utils import normalize_query_results
from app.core.logging import get_logger

# MySQL DESCRIBE TABLE 查询返回的列索引
COMMENT_INDEX = 8

logger = get_logger(__name__)


class MySQLConnector(BaseConnector):
    """
    MySQL数据库连接器
    """

    def __init__(self, **kwargs):
        """
        初始化MySQL连接器

        Args:
            kwargs: 连接参数，包括host, port, username, password, database,extra_params等
        """
        super().__init__(**kwargs)
        # 默认端口
        if self.port is None:
            self.port = 3306

    def _connect(self, database: Optional[str] = None):
        """
        建立数据库连接

        Args:
            database: 要连接的数据库名称，默认为当前连接的数据库
        """
        if not self.connection or not self.connection.open:
            self.connection = pymysql.connect(
                host=self.host,
                port=int(self.port),
                user=self.username,
                password=self.password,
                database=database or self.database,
                **self.extra_params,
            )

    def test_connection(self) -> ConnectionTestResult:
        """
        测试MySQL连接是否成功
        """
        try:
            self._connect()
            logger.info(f"成功连接到MySQL数据库：{self.host}:{self.port}/{self.database}")
            return ConnectionTestResult(
                success=True,
                message=f"成功连接到MySQL数据库：{self.host}:{self.port}/{self.database}",
            )
        except Exception as e:
            error_msg = f"连接MySQL数据库失败：{e!s}"
            logger.exception(f"连接MySQL数据库失败：{self.host}:{self.port}/{self.database}")
            return ConnectionTestResult(success=False, message=error_msg)
        finally:
            if self.connection:
                self.connection.close()
                self.connection = None

    def get_server_info(self) -> dict[str, Any]:
        """
        获取MySQL服务器基本信息
        """
        self._connect()
        cursor = self.connection.cursor()
        try:
            # 获取版本信息
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]

            # 获取服务器信息
            cursor.execute("SHOW GLOBAL VARIABLES LIKE 'server_id'")
            server_id = cursor.fetchone()

            cursor.execute("SHOW GLOBAL VARIABLES LIKE 'hostname'")
            hostname = cursor.fetchone()

            return {
                "version": version,
                "server_id": server_id[1] if server_id else None,
                "hostname": hostname[1] if hostname else None,
                "type": "mysql",
            }
        finally:
            cursor.close()

    def get_databases(self) -> list[str]:
        """
        获取MySQL服务器上所有数据库名称
        """
        self._connect(database=None)  # 不指定数据库，连接到服务器
        cursor = self.connection.cursor()
        try:
            cursor.execute("SHOW DATABASES")
            databases = [row[0] for row in cursor.fetchall()]
            return databases
        finally:
            cursor.close()

    def get_tables(self, database: Optional[str] = None, schema: Optional[str] = None) -> list[str]:
        """
        获取MySQL指定数据库下的所有表名

        Args:
            database: 数据库名称，默认为当前连接的数据库
            schema: schema名称，MySQL中与database等价，忽略此参数

        Returns:
            List[str]: 表名列表
        """
        self._connect(database)
        cursor = self.connection.cursor()
        try:
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            return tables
        finally:
            cursor.close()

    def get_views(self, database: Optional[str] = None, schema: Optional[str] = None) -> list[str]:
        """
        获取MySQL指定数据库下的所有视图名

        Args:
            database: 数据库名称，默认为当前连接的数据库
            schema: schema名称，MySQL中与database等价，忽略此参数

        Returns:
            List[str]: 视图名列表
        """
        self._connect(database)
        cursor = self.connection.cursor()
        try:
            db_name = database or self.database
            cursor.execute(
                """
                SELECT TABLE_NAME
                FROM information_schema.VIEWS
                WHERE TABLE_SCHEMA = %s
                ORDER BY TABLE_NAME
            """,
                (db_name,),
            )
            views = [row[0] for row in cursor.fetchall()]
            return views
        finally:
            cursor.close()

    def get_table_structure(
        self, table_name: str, database: Optional[str] = None, schema: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        获取MySQL指定数据库和表名的结构信息

        Args:
            table_name: 表名
            database: 数据库名称，默认为当前连接的数据库
            schema: schema名称，MySQL中与database等价，忽略此参数

        Returns:
            List[Dict[str, Any]]: 表结构信息，包括字段名、类型、是否为主键等
        """
        self._connect(database)
        cursor = self.connection.cursor()
        try:
            # 获取表结构信息
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()

            # 获取主键信息
            cursor.execute(f"SHOW INDEX FROM {table_name} WHERE Key_name = 'PRIMARY'")
            primary_keys = [row[4] for row in cursor.fetchall()]

            result = []
            for column in columns:
                field_name = column[0]
                result.append(
                    {
                        "field_name": field_name,
                        "data_type": column[1],
                        "is_nullable": column[2] == "YES",
                        "default_value": column[4],
                        "is_primary_key": field_name in primary_keys,
                        "comment": column[COMMENT_INDEX] if len(column) > COMMENT_INDEX else "",
                    }
                )

            return result
        finally:
            cursor.close()

    def execute_query(
        self, query: str, params: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        """
        执行MySQL查询

        返回结果会自动处理特殊字段类型（时间类型、BLOB类型、DECIMAL等）
        """
        self._connect()
        cursor = self.connection.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute(query, params or {})
            results = cursor.fetchall()
            # 规范化查询结果，处理特殊类型
            return normalize_query_results(results)
        finally:
            cursor.close()

    def close(self):
        """
        关闭MySQL连接
        """
        if self.connection:
            self.connection.close()
            self.connection = None
