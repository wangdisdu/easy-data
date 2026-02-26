from typing import Any, Optional

import pyodbc

from app.connector.base import BaseConnector
from app.connector.models import ConnectionTestResult
from app.core.json_utils import normalize_query_results
from app.core.logging import get_logger

logger = get_logger(__name__)


class SQLServerConnector(BaseConnector):
    """
    SQL Server数据库连接器
    """

    def __init__(self, **kwargs):
        """
        初始化SQL Server连接器

        Args:
            kwargs: 连接参数，包括host, port, username, password, database等
        """
        super().__init__(**kwargs)
        # 默认端口
        if self.port is None:
            self.port = 1433

    def _connect(self, database: Optional[str] = None):
        """
        建立数据库连接

        Args:
            database: 要连接的数据库名称，默认为当前连接的数据库
        """
        if not self.connection or self.connection.state == 0:
            # 构建连接字符串
            conn_str = "DRIVER={ODBC Driver 17 for SQL Server};"
            conn_str += f"SERVER={self.host},{self.port};"
            conn_str += f"DATABASE={database or self.database};"
            conn_str += f"UID={self.username};"
            conn_str += f"PWD={self.password};"

            # 添加额外参数
            for key, value in self.extra_params.items():
                conn_str += f"{key}={value};"

            self.connection = pyodbc.connect(conn_str)

    def test_connection(self) -> ConnectionTestResult:
        """
        测试SQL Server连接是否成功
        """
        try:
            self._connect()
            logger.info(f"成功连接到SQL Server数据库：{self.host}:{self.port}/{self.database}")
            return ConnectionTestResult(
                success=True,
                message=f"成功连接到SQL Server数据库：{self.host}:{self.port}/{self.database}",
            )
        except Exception as e:
            error_msg = f"连接SQL Server数据库失败：{e!s}"
            logger.exception(f"连接SQL Server数据库失败：{self.host}:{self.port}/{self.database}")
            return ConnectionTestResult(success=False, message=error_msg)
        finally:
            if self.connection:
                self.connection.close()
                self.connection = None

    def get_server_info(self) -> dict[str, Any]:
        """
        获取SQL Server服务器基本信息
        """
        self._connect()
        cursor = self.connection.cursor()
        try:
            # 获取版本信息
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]

            # 获取服务器名称
            cursor.execute("SELECT @@SERVERNAME")
            server_name = cursor.fetchone()[0]

            # 获取服务器实例名称
            cursor.execute("SELECT @@SERVICENAME")
            service_name = cursor.fetchone()[0]

            return {
                "version": version,
                "server_name": server_name,
                "service_name": service_name,
                "type": "sqlserver",
            }
        finally:
            cursor.close()

    def get_databases(self) -> list[str]:
        """
        获取SQL Server服务器上所有数据库名称
        """
        self._connect()
        cursor = self.connection.cursor()
        try:
            cursor.execute("SELECT name FROM sys.databases WHERE database_id > 4")
            databases = [row[0] for row in cursor.fetchall()]
            return databases
        finally:
            cursor.close()

    def get_schemas(self, database: Optional[str] = None) -> list[str]:
        """
        获取SQL Server指定数据库下的所有schema名称
        """
        self._connect(database)
        cursor = self.connection.cursor()
        try:
            cursor.execute("SELECT name FROM sys.schemas")
            schemas = [row[0] for row in cursor.fetchall()]
            return schemas
        finally:
            cursor.close()

    def get_tables(self, database: Optional[str] = None, schema: Optional[str] = None) -> list[str]:
        """
        获取SQL Server指定数据库和schema下的所有表名

        Args:
            database: 数据库名称，默认为当前连接的数据库
            schema: schema名称，默认为'dbo'

        Returns:
            List[str]: 表名列表
        """
        self._connect(database)
        cursor = self.connection.cursor()
        try:
            target_schema = schema or "dbo"
            cursor.execute(
                """
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
                AND TABLE_SCHEMA = ?
                ORDER BY TABLE_NAME
            """,
                (target_schema,),
            )
            tables = [row[0] for row in cursor.fetchall()]
            return tables
        finally:
            cursor.close()

    def get_views(self, database: Optional[str] = None, schema: Optional[str] = None) -> list[str]:
        """
        获取SQL Server指定数据库和schema下的所有视图名

        Args:
            database: 数据库名称，默认为当前连接的数据库
            schema: schema名称，默认为'dbo'

        Returns:
            List[str]: 视图名列表
        """
        self._connect(database)
        cursor = self.connection.cursor()
        try:
            target_schema = schema or "dbo"
            cursor.execute(
                """
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.VIEWS
                WHERE TABLE_SCHEMA = ?
                ORDER BY TABLE_NAME
            """,
                (target_schema,),
            )
            views = [row[0] for row in cursor.fetchall()]
            return views
        finally:
            cursor.close()

    def get_table_structure(
        self, table_name: str, database: Optional[str] = None, schema: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        获取SQL Server指定数据库、schema和表名的结构信息

        Args:
            table_name: 表名
            database: 数据库名称，默认为当前连接的数据库
            schema: schema名称，默认为'dbo'

        Returns:
            List[Dict[str, Any]]: 表结构信息，包括字段名、类型、是否为主键等
        """
        self._connect(database)
        cursor = self.connection.cursor()
        try:
            target_schema = schema or "dbo"

            # 获取表结构信息
            cursor.execute(
                """
                SELECT
                    COLUMN_NAME,
                    DATA_TYPE,
                    IS_NULLABLE,
                    COLUMN_DEFAULT,
                    ORDINAL_POSITION
                FROM
                    INFORMATION_SCHEMA.COLUMNS
                WHERE
                    TABLE_NAME = ?
                    AND TABLE_SCHEMA = ?
                ORDER BY
                    ORDINAL_POSITION
            """,
                (table_name, target_schema),
            )
            columns = cursor.fetchall()

            # 获取主键信息
            cursor.execute(
                """
                SELECT
                    COLUMN_NAME
                FROM
                    INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE
                    OBJECTPROPERTY(OBJECT_ID(CONSTRAINT_SCHEMA + '.' + CONSTRAINT_NAME), 'IsPrimaryKey') = 1
                    AND TABLE_NAME = ?
                    AND TABLE_SCHEMA = ?
            """,
                (table_name, target_schema),
            )
            primary_keys = [row[0] for row in cursor.fetchall()]

            # 获取列注释信息
            cursor.execute(
                """
                SELECT
                    c.name AS COLUMN_NAME,
                    ep.value AS COLUMN_COMMENT
                FROM
                    sys.columns c
                LEFT JOIN
                    sys.extended_properties ep ON ep.major_id = c.object_id AND ep.minor_id = c.column_id
                INNER JOIN
                    sys.tables t ON t.object_id = c.object_id
                INNER JOIN
                    sys.schemas s ON t.schema_id = s.schema_id
                WHERE
                    t.name = ?
                    AND s.name = ?
                ORDER BY
                    c.column_id
            """,
                (table_name, target_schema),
            )
            comments = {row[0]: row[1] for row in cursor.fetchall() if row[1] is not None}

            result = []
            for column in columns:
                field_name = column[0]
                result.append(
                    {
                        "field_name": field_name,
                        "data_type": column[1],
                        "is_nullable": column[2] == "YES",
                        "default_value": column[3],
                        "is_primary_key": field_name in primary_keys,
                        "comment": comments.get(field_name, ""),
                    }
                )

            return result
        finally:
            cursor.close()

    def execute_query(
        self, query: str, params: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        """
        执行SQL Server查询

        返回结果会自动处理特殊字段类型（时间类型、BLOB类型、DECIMAL等）
        """
        self._connect()
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or {})

            # 获取列名
            columns = [column[0] for column in cursor.description]

            # 构建结果集
            result = []
            for row in cursor.fetchall():
                row_dict = {}
                for i, value in enumerate(row):
                    row_dict[columns[i]] = value
                result.append(row_dict)

            # 规范化查询结果，处理特殊类型
            return normalize_query_results(result)
        finally:
            cursor.close()

    def close(self):
        """
        关闭SQL Server连接
        """
        if self.connection:
            self.connection.close()
            self.connection = None
