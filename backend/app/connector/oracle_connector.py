from typing import Any, Optional

try:
    import cx_Oracle
except ImportError:
    cx_Oracle = None  # type: ignore[assignment]

from app.connector.base import BaseConnector
from app.connector.models import ConnectionTestResult
from app.core.json_utils import normalize_query_results
from app.core.logging import get_logger

logger = get_logger(__name__)


class OracleConnector(BaseConnector):
    """
    Oracle数据库连接器
    """

    def __init__(self, **kwargs):
        """
        初始化Oracle连接器

        Args:
            kwargs: 连接参数，包括host, port, username, password, database等
        """
        super().__init__(**kwargs)
        # 默认端口
        if self.port is None:
            self.port = 1521

    def _connect(self, database: Optional[str] = None):
        """
        建立数据库连接

        Args:
            database: 要连接的数据库名称(service_name)，默认为当前连接的数据库
        """
        if cx_Oracle is None:
            raise RuntimeError(
                "Oracle 支持需要安装 cx-oracle 依赖，请执行: pip install -e '.[oracle]'"
            )
        if not self.connection or not self.connection.is_connected():
            # 构建DSN (Data Source Name)
            dsn = cx_Oracle.makedsn(
                host=self.host, port=int(self.port), service_name=database or self.database
            )

            self.connection = cx_Oracle.connect(
                user=self.username, password=self.password, dsn=dsn, **self.extra_params
            )

    def test_connection(self) -> ConnectionTestResult:
        """
        测试Oracle连接是否成功
        """
        try:
            self._connect()
            logger.info(f"成功连接到Oracle数据库：{self.host}:{self.port}/{self.database}")
            return ConnectionTestResult(
                success=True,
                message=f"成功连接到Oracle数据库：{self.host}:{self.port}/{self.database}",
            )
        except Exception as e:
            error_msg = f"连接Oracle数据库失败：{e!s}"
            logger.exception(f"连接Oracle数据库失败：{self.host}:{self.port}/{self.database}")
            return ConnectionTestResult(success=False, message=error_msg)
        finally:
            if self.connection:
                self.connection.close()
                self.connection = None

    def get_server_info(self) -> dict[str, Any]:
        """
        获取Oracle服务器基本信息
        """
        self._connect()
        cursor = self.connection.cursor()
        try:
            # 获取版本信息
            cursor.execute("SELECT banner FROM v$version WHERE banner LIKE 'Oracle%'")
            version = cursor.fetchone()[0]

            # 获取实例名称
            cursor.execute("SELECT instance_name FROM v$instance")
            instance_name = cursor.fetchone()[0]

            # 获取主机名
            cursor.execute("SELECT host_name FROM v$instance")
            host_name = cursor.fetchone()[0]

            return {
                "version": version,
                "instance_name": instance_name,
                "host_name": host_name,
                "type": "oracle",
            }
        finally:
            cursor.close()

    def get_databases(self) -> list[str]:
        """
        获取Oracle服务器上所有数据库名称(PDBs)
        """
        self._connect()
        cursor = self.connection.cursor()
        try:
            # 获取PDB列表(Oracle 12c+)
            try:
                cursor.execute("SELECT pdb_name FROM dba_pdbs")
                pdbs = [row[0] for row in cursor.fetchall()]
                return pdbs
            except cx_Oracle.DatabaseError:
                # 如果不是CDB，返回当前数据库
                cursor.execute("SELECT name FROM v$database")
                db_name = cursor.fetchone()[0]
                return [db_name]
        finally:
            cursor.close()

    def get_schemas(self, database: Optional[str] = None) -> list[str]:
        """
        获取Oracle指定数据库下的所有schema名称（用户列表）
        """
        self._connect(database)
        cursor = self.connection.cursor()
        try:
            # 获取用户列表
            cursor.execute("SELECT username FROM dba_users WHERE account_status = 'OPEN'")
            schemas = [row[0] for row in cursor.fetchall()]
            return schemas
        finally:
            cursor.close()

    def get_tables(self, database: Optional[str] = None, schema: Optional[str] = None) -> list[str]:
        """
        获取Oracle指定数据库和schema下的所有表名

        Args:
            database: 数据库名称(service_name)，默认为当前连接的数据库
            schema: schema名称（用户名），默认为当前用户

        Returns:
            List[str]: 表名列表
        """
        self._connect(database)
        cursor = self.connection.cursor()
        try:
            if schema:
                # 获取指定用户的表
                cursor.execute(
                    """
                    SELECT table_name
                    FROM all_tables
                    WHERE owner = UPPER(?)
                    ORDER BY table_name
                """,
                    (schema,),
                )
            else:
                # 获取当前用户的表
                cursor.execute(
                    """
                    SELECT table_name
                    FROM user_tables
                    ORDER BY table_name
                """
                )
            tables = [row[0] for row in cursor.fetchall()]
            return tables
        finally:
            cursor.close()

    def get_views(self, database: Optional[str] = None, schema: Optional[str] = None) -> list[str]:
        """
        获取Oracle指定数据库和schema下的所有视图名

        Args:
            database: 数据库名称(service_name)，默认为当前连接的数据库
            schema: schema名称（用户名），默认为当前用户

        Returns:
            List[str]: 视图名列表
        """
        self._connect(database)
        cursor = self.connection.cursor()
        try:
            if schema:
                # 获取指定用户的视图
                cursor.execute(
                    """
                    SELECT view_name
                    FROM all_views
                    WHERE owner = UPPER(?)
                    ORDER BY view_name
                """,
                    (schema,),
                )
            else:
                # 获取当前用户的视图
                cursor.execute(
                    """
                    SELECT view_name
                    FROM user_views
                    ORDER BY view_name
                """
                )
            views = [row[0] for row in cursor.fetchall()]
            return views
        finally:
            cursor.close()

    def get_table_structure(
        self, table_name: str, database: Optional[str] = None, schema: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        获取Oracle指定数据库、schema和表名的结构信息

        Args:
            table_name: 表名
            database: 数据库名称(service_name)，默认为当前连接的数据库
            schema: schema名称（用户名），默认为当前用户

        Returns:
            List[Dict[str, Any]]: 表结构信息，包括字段名、类型、是否为主键等
        """
        self._connect(database)
        cursor = self.connection.cursor()
        try:
            if schema:
                # 获取指定用户表的结构信息
                cursor.execute(
                    """
                    SELECT
                        column_name,
                        data_type,
                        nullable,
                        data_default,
                        column_id
                    FROM
                        all_tab_cols
                    WHERE
                        owner = UPPER(?) AND
                        table_name = UPPER(?)
                    ORDER BY
                        column_id
                """,
                    (schema, table_name),
                )
                columns = cursor.fetchall()

                # 获取指定用户表的主键信息
                cursor.execute(
                    """
                    SELECT
                        ucc.column_name
                    FROM
                        all_cons_columns ucc
                    JOIN
                        all_constraints uc ON ucc.constraint_name = uc.constraint_name
                    WHERE
                        uc.owner = UPPER(?) AND
                        uc.table_name = UPPER(?) AND
                        uc.constraint_type = 'P'
                """,
                    (schema, table_name),
                )
                primary_keys = [row[0] for row in cursor.fetchall()]

                # 获取指定用户表的列注释信息
                cursor.execute(
                    """
                    SELECT
                        column_name,
                        comments
                    FROM
                        all_col_comments
                    WHERE
                        owner = UPPER(?) AND
                        table_name = UPPER(?)
                """,
                    (schema, table_name),
                )
            else:
                # 获取当前用户表的结构信息
                cursor.execute(
                    """
                    SELECT
                        column_name,
                        data_type,
                        nullable,
                        data_default,
                        column_id
                    FROM
                        user_tab_cols
                    WHERE
                        table_name = UPPER(?)
                    ORDER BY
                        column_id
                """,
                    (table_name,),
                )
                columns = cursor.fetchall()

                # 获取当前用户表的主键信息
                cursor.execute(
                    """
                    SELECT
                        column_name
                    FROM
                        user_cons_columns ucc
                    JOIN
                        user_constraints uc ON ucc.constraint_name = uc.constraint_name
                    WHERE
                        uc.table_name = UPPER(?) AND
                        uc.constraint_type = 'P'
                """,
                    (table_name,),
                )
                primary_keys = [row[0] for row in cursor.fetchall()]

                # 获取当前用户表的列注释信息
                cursor.execute(
                    """
                    SELECT
                        column_name,
                        comments
                    FROM
                        user_col_comments
                    WHERE
                        table_name = UPPER(?)
                """,
                    (table_name,),
                )

            comments = {row[0]: row[1] for row in cursor.fetchall() if row[1] is not None}

            result = []
            for column in columns:
                field_name = column[0]
                result.append(
                    {
                        "field_name": field_name,
                        "data_type": column[1],
                        "is_nullable": column[2] == "Y",
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
        执行Oracle查询

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
        关闭Oracle连接
        """
        if self.connection:
            self.connection.close()
            self.connection = None
