from typing import Any, Optional

import clickhouse_connect

from app.connector.base import BaseConnector
from app.connector.models import ConnectionTestResult
from app.core.json_utils import normalize_query_results
from app.core.logging import get_logger

# ClickHouse DESCRIBE TABLE 查询返回的列索引
COMMENT_INDEX = 4

logger = get_logger(__name__)


class ClickHouseConnector(BaseConnector):
    """
    ClickHouse数据库连接器
    使用 clickhouse-connect（官方推荐的 Python 客户端）
    """

    def __init__(self, **kwargs):
        """
        初始化ClickHouse连接器

        Args:
            kwargs: 连接参数，包括host, port, username, password, database等
        """
        super().__init__(**kwargs)
        # 默认端口（HTTP接口）
        if self.port is None:
            self.port = 8123

    def _connect(self, database: Optional[str] = None):
        """
        建立数据库连接

        Args:
            database: 要连接的数据库名称，默认为当前连接的数据库
        """
        if not self.connection:
            self.connection = clickhouse_connect.get_client(
                host=self.host,
                port=int(self.port),
                username=self.username,
                password=self.password,
                database=database or self.database,
                **self.extra_params,
            )

    def test_connection(self) -> ConnectionTestResult:
        """
        测试ClickHouse连接是否成功
        """
        try:
            self._connect()
            # 执行简单查询测试连接
            self.connection.query("SELECT 1")
            logger.info(f"成功连接到ClickHouse数据库：{self.host}:{self.port}/{self.database}")
            return ConnectionTestResult(
                success=True,
                message=f"成功连接到ClickHouse数据库：{self.host}:{self.port}/{self.database}",
            )
        except Exception as e:
            error_msg = f"连接ClickHouse数据库失败：{e!s}"
            logger.exception(f"连接ClickHouse数据库失败：{self.host}:{self.port}/{self.database}")
            return ConnectionTestResult(success=False, message=error_msg)
        finally:
            if self.connection:
                self.connection.close()
                self.connection = None

    def get_server_info(self) -> dict[str, Any]:
        """
        获取ClickHouse服务器基本信息
        """
        self._connect()
        try:
            # 获取版本信息
            result = self.connection.query("SELECT version()")
            version = result.result_set[0][0]

            # 获取服务器时间
            result = self.connection.query("SELECT now()")
            server_time = result.result_set[0][0]

            # 获取服务器时区
            result = self.connection.query("SELECT timezone()")
            timezone = result.result_set[0][0]

            return {
                "version": version,
                "server_time": server_time,
                "timezone": timezone,
                "type": "clickhouse",
            }
        finally:
            pass

    def get_databases(self) -> list[str]:
        """
        获取ClickHouse服务器上所有数据库名称
        """
        self._connect()
        try:
            result = self.connection.query("SHOW DATABASES")
            databases = [row[0] for row in result.result_set]
            return databases
        finally:
            pass

    def get_tables(self, database: Optional[str] = None, schema: Optional[str] = None) -> list[str]:
        """
        获取ClickHouse指定数据库下的所有表名（不包括视图）

        Args:
            database: 数据库名称，默认为当前连接的数据库
            schema: schema名称，ClickHouse中无此概念，忽略此参数

        Returns:
            List[str]: 表名列表（不包括视图）
        """
        self._connect(database)
        try:
            # 获取指定数据库的表（不包括视图）
            db_name = database or self.database
            result = self.connection.query(
                f"SELECT name FROM system.tables WHERE database = '{db_name}' AND engine NOT LIKE '%View%' AND engine NOT LIKE '%MaterializedView%' ORDER BY name"
            )
            tables = [row[0] for row in result.result_set]
            return tables
        finally:
            pass

    def get_views(self, database: Optional[str] = None, schema: Optional[str] = None) -> list[str]:
        """
        获取ClickHouse指定数据库下的所有视图名

        ClickHouse支持普通视图(View)和物化视图(MaterializedView)

        Args:
            database: 数据库名称，默认为当前连接的数据库
            schema: schema名称，ClickHouse中无此概念，忽略此参数

        Returns:
            List[str]: 视图名列表（包括普通视图和物化视图）
        """
        self._connect(database)
        try:
            # 获取指定数据库的视图（包括View和MaterializedView）
            db_name = database or self.database
            result = self.connection.query(
                f"SELECT name FROM system.tables WHERE database = '{db_name}' AND (engine LIKE '%View%' OR engine LIKE '%MaterializedView%') ORDER BY name"
            )
            views = [row[0] for row in result.result_set]
            return views
        finally:
            pass

    def get_table_structure(
        self, table_name: str, database: Optional[str] = None, schema: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        获取ClickHouse指定数据库和表名的结构信息

        Args:
            table_name: 表名
            database: 数据库名称，默认为当前连接的数据库
            schema: schema名称，ClickHouse中无此概念，忽略此参数

        Returns:
            List[Dict[str, Any]]: 表结构信息，包括字段名、类型、是否为主键等
        """
        self._connect(database)
        try:
            # 获取表结构信息
            result = self.connection.query(f"DESCRIBE TABLE {table_name}")

            # 获取主键信息
            create_table_result = self.connection.query(f"SHOW CREATE TABLE {table_name}")
            create_table_sql = create_table_result.result_set[0][0]

            # 解析主键信息
            primary_keys = []
            if "ENGINE" in create_table_sql:
                engine_part = create_table_sql.split("ENGINE")[0]
                if "PRIMARY KEY" in engine_part:
                    pk_part = engine_part.split("PRIMARY KEY")[1].strip()
                    # 简单解析主键列名
                    if pk_part.startswith("("):
                        pk_part = pk_part[1:-1].strip()
                    primary_keys = [pk.strip() for pk in pk_part.split(",")]

            columns_info = []
            for row in result.result_set:
                field_name = row[0]
                columns_info.append(
                    {
                        "field_name": field_name,
                        "data_type": row[1],
                        "is_nullable": row[2] == "YES",
                        "default_value": row[3],
                        "is_primary_key": field_name in primary_keys,
                        "comment": row[COMMENT_INDEX] if len(row) > COMMENT_INDEX else "",
                    }
                )

            return columns_info
        finally:
            pass

    def execute_query(
        self, query: str, params: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        """
        执行ClickHouse查询

        返回结果会自动处理特殊字段类型（时间类型、BLOB类型、DECIMAL等）
        """
        self._connect()
        try:
            # 执行查询
            result = self.connection.query(query, parameters=params)

            # 构建结果集
            column_names = result.column_names
            result_list = []
            for row in result.result_set:
                row_dict = {}
                for i, value in enumerate(row):
                    row_dict[column_names[i]] = value
                result_list.append(row_dict)

            # 规范化查询结果，处理特殊类型
            return normalize_query_results(result_list)
        finally:
            pass

    def close(self):
        """
        关闭ClickHouse连接
        """
        if self.connection:
            self.connection.close()
            self.connection = None
