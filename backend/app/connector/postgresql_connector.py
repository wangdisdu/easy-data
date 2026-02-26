from typing import Any, Optional

import psycopg2

from app.connector.base import BaseConnector
from app.connector.models import ConnectionTestResult
from app.core.json_utils import normalize_query_results
from app.core.logging import get_logger

logger = get_logger(__name__)


class PostgreSQLConnector(BaseConnector):
    """
    PostgreSQL数据库连接器
    """

    def __init__(self, **kwargs):
        """
        初始化PostgreSQL连接器

        Args:
            kwargs: 连接参数，包括host, port, username, password, database等
        """
        super().__init__(**kwargs)
        # 默认端口
        if self.port is None:
            self.port = 5432

    def _connect(self, database: Optional[str] = None):
        """
        建立数据库连接

        Args:
            database: 要连接的数据库名称，默认为当前连接的数据库
        """
        if not self.connection or self.connection.closed != 0:
            self.connection = psycopg2.connect(
                host=self.host,
                port=int(self.port),
                user=self.username,
                password=self.password,
                dbname=database or self.database,
                **self.extra_params,
            )

    def test_connection(self) -> ConnectionTestResult:
        """
        测试PostgreSQL连接是否成功
        """
        try:
            self._connect()
            logger.info(f"成功连接到PostgreSQL数据库：{self.host}:{self.port}/{self.database}")
            return ConnectionTestResult(
                success=True,
                message=f"成功连接到PostgreSQL数据库：{self.host}:{self.port}/{self.database}",
            )
        except Exception as e:
            error_msg = f"连接PostgreSQL数据库失败：{e!s}"
            logger.exception(f"连接PostgreSQL数据库失败：{self.host}:{self.port}/{self.database}")
            return ConnectionTestResult(success=False, message=error_msg)
        finally:
            if self.connection:
                self.connection.close()
                self.connection = None

    def get_server_info(self) -> dict[str, Any]:
        """
        获取PostgreSQL服务器基本信息
        """
        self._connect()
        cursor = self.connection.cursor()
        try:
            # 获取版本信息
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]

            # 获取服务器信息
            cursor.execute("SELECT inet_server_addr()")
            server_addr = cursor.fetchone()[0]

            cursor.execute("SELECT inet_server_port()")
            server_port = cursor.fetchone()[0]

            cursor.execute("SELECT current_setting('server_version_num')")
            version_num = cursor.fetchone()[0]

            return {
                "version": version,
                "server_address": server_addr,
                "server_port": server_port,
                "version_num": version_num,
                "type": "postgresql",
            }
        finally:
            cursor.close()

    def get_databases(self) -> list[str]:
        """
        获取PostgreSQL服务器上所有数据库名称
        """
        # 连接到postgres默认数据库以获取所有数据库列表
        self._connect(database="postgres")
        cursor = self.connection.cursor()
        try:
            cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false")
            databases = [row[0] for row in cursor.fetchall()]
            return databases
        finally:
            cursor.close()

    def get_schemas(self, database: Optional[str] = None) -> list[str]:
        """
        获取PostgreSQL指定数据库下的所有schema名称
        """
        self._connect(database)
        cursor = self.connection.cursor()
        try:
            cursor.execute("SELECT schema_name FROM information_schema.schemata")
            schemas = [row[0] for row in cursor.fetchall()]
            return schemas
        finally:
            cursor.close()

    def get_tables(self, database: Optional[str] = None, schema: Optional[str] = None) -> list[str]:
        """
        获取PostgreSQL指定数据库和schema下的所有表名

        Args:
            database: 数据库名称，默认为当前连接的数据库
            schema: schema名称，默认为'public'

        Returns:
            List[str]: 表名列表
        """
        self._connect(database)
        cursor = self.connection.cursor()
        try:
            target_schema = schema or "public"
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """,
                (target_schema,),
            )
            tables = [row[0] for row in cursor.fetchall()]
            return tables
        finally:
            cursor.close()

    def get_views(self, database: Optional[str] = None, schema: Optional[str] = None) -> list[str]:
        """
        获取PostgreSQL指定数据库和schema下的所有视图名

        Args:
            database: 数据库名称，默认为当前连接的数据库
            schema: schema名称，默认为'public'

        Returns:
            List[str]: 视图名列表
        """
        self._connect(database)
        cursor = self.connection.cursor()
        try:
            target_schema = schema or "public"
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.views
                WHERE table_schema = %s
                ORDER BY table_name
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
        获取PostgreSQL指定数据库、schema和表名的结构信息

        Args:
            table_name: 表名
            database: 数据库名称，默认为当前连接的数据库
            schema: schema名称，默认为'public'

        Returns:
            List[Dict[str, Any]]: 表结构信息，包括字段名、类型、是否为主键等
        """
        self._connect(database)
        cursor = self.connection.cursor()
        try:
            target_schema = schema or "public"

            # 获取表结构信息
            cursor.execute(
                """
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    ordinal_position
                FROM
                    information_schema.columns
                WHERE
                    table_name = %s AND table_schema = %s
                ORDER BY
                    ordinal_position
            """,
                (table_name, target_schema),
            )
            columns = cursor.fetchall()

            # 获取主键信息
            cursor.execute(
                """
                SELECT
                    kcu.column_name
                FROM
                    information_schema.table_constraints tc
                JOIN
                    information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                WHERE
                    tc.table_name = %s AND
                    tc.table_schema = %s AND
                    tc.constraint_type = 'PRIMARY KEY'
            """,
                (table_name, target_schema),
            )
            primary_keys = [row[0] for row in cursor.fetchall()]

            # 获取列注释信息
            cursor.execute(
                """
                SELECT
                    col.column_name,
                    col_description((col.table_schema || '.' || col.table_name)::regclass, col.ordinal_position)
                FROM
                    information_schema.columns col
                WHERE
                    col.table_name = %s AND col.table_schema = %s
            """,
                (table_name, target_schema),
            )
            comments = {row[0]: row[1] for row in cursor.fetchall()}

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
        执行PostgreSQL查询

        返回结果会自动处理特殊字段类型（时间类型、BLOB类型、DECIMAL等）
        """
        self._connect()
        cursor = self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cursor.execute(query, params or {})
            results = [dict(row) for row in cursor.fetchall()]
            # 规范化查询结果，处理特殊类型
            return normalize_query_results(results)
        finally:
            cursor.close()

    def close(self):
        """
        关闭PostgreSQL连接
        """
        if self.connection:
            self.connection.close()
            self.connection = None
