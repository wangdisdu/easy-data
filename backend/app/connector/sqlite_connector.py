"""
SQLite数据库连接器
"""

import os
import sqlite3
from pathlib import Path
from typing import Any, Optional

from app.connector.base import BaseConnector
from app.connector.models import ConnectionTestResult
from app.core.json_utils import normalize_query_results
from app.core.logging import get_logger

logger = get_logger(__name__)


class SQLiteConnector(BaseConnector):
    """
    SQLite数据库连接器
    SQLite是文件数据库，只需要文件路径即可连接
    """

    def __init__(self, **kwargs):
        """
        初始化SQLite连接器

        Args:
            kwargs: 连接参数
                - database: SQLite文件路径（相对于backend/local_sqlite目录，或绝对路径）
                - 其他参数(host, port, username, password)将被忽略
        """
        super().__init__(**kwargs)
        # SQLite不需要host、port、username、password
        # database字段存储文件路径
        self.db_path = self._resolve_db_path(self.database)

    def _resolve_db_path(self, database: str) -> str:
        """
        解析数据库文件路径

        Args:
            database: 数据库文件路径（相对路径或绝对路径）

        Returns:
            str: 绝对路径
        """
        if not database:
            raise ValueError("SQLite数据库文件路径不能为空")

        # 如果是绝对路径，直接使用
        if os.path.isabs(database):
            return database

        # 如果是相对路径，相对于backend/local_sqlite目录
        # 获取backend目录的绝对路径
        backend_dir = Path(__file__).parent.parent.parent
        local_sqlite_dir = backend_dir / "local_sqlite"

        # 构建完整路径
        db_path = local_sqlite_dir / database

        return str(db_path.resolve())

    def _get_relative_path(self, absolute_path: str) -> str:
        """
        将绝对路径转换为相对路径（相对于backend/local_sqlite目录）

        Args:
            absolute_path: 绝对路径

        Returns:
            str: 相对路径，如果无法转换为相对路径则返回文件名
        """
        try:
            # 获取backend目录的绝对路径
            backend_dir = Path(__file__).parent.parent.parent
            local_sqlite_dir = backend_dir / "local_sqlite"

            # 尝试转换为相对路径
            try:
                relative_path = os.path.relpath(absolute_path, str(local_sqlite_dir))
                # 如果相对路径不包含 '..'，说明在local_sqlite目录下
                if ".." not in relative_path:
                    return relative_path
            except ValueError:
                # 如果无法转换为相对路径（不同驱动器等），返回文件名
                pass

            # 如果无法转换为相对路径，只返回文件名
            return os.path.basename(absolute_path)
        except Exception:
            # 如果出现任何错误，只返回文件名
            return os.path.basename(absolute_path)

    def _connect(self):
        """
        建立数据库连接
        """
        if not self.connection:
            # 确保文件存在
            if not os.path.exists(self.db_path):
                relative_path = self._get_relative_path(self.db_path)
                raise FileNotFoundError(f"SQLite数据库文件不存在：{relative_path}")

            # 连接SQLite数据库
            self.connection = sqlite3.connect(self.db_path)
            # 设置返回字典格式的游标
            self.connection.row_factory = sqlite3.Row

    def test_connection(self) -> ConnectionTestResult:
        """
        测试SQLite连接是否成功
        """
        try:
            self._connect()
            relative_path = self._get_relative_path(self.db_path)
            logger.info(f"成功连接到SQLite数据库：{relative_path}")
            return ConnectionTestResult(
                success=True, message=f"成功连接到SQLite数据库：{relative_path}"
            )
        except Exception as e:
            relative_path = self._get_relative_path(self.db_path)
            error_msg = f"连接SQLite数据库失败：{relative_path} - {e!s}"
            # 日志中只记录相对路径，不暴露绝对路径
            logger.exception(f"连接SQLite数据库失败：{relative_path}")
            return ConnectionTestResult(success=False, message=error_msg)
        finally:
            if self.connection:
                self.connection.close()
                self.connection = None

    def get_server_info(self) -> dict[str, Any]:
        """
        获取SQLite服务器基本信息
        SQLite是文件数据库，返回文件信息
        """
        self._connect()
        cursor = self.connection.cursor()
        try:
            # 获取SQLite版本
            cursor.execute("SELECT sqlite_version()")
            version = cursor.fetchone()[0]

            # 获取文件信息
            file_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            relative_path = self._get_relative_path(self.db_path)

            return {
                "version": version,
                "file_path": relative_path,
                "file_size_in_bytes": file_size,
                "type": "sqlite",
            }
        finally:
            cursor.close()

    def get_databases(self) -> list[str]:
        """
        获取SQLite数据库列表
        SQLite是单文件数据库，返回当前数据库名称（文件路径，相对路径）
        """
        relative_path = self._get_relative_path(self.db_path)
        return [relative_path]

    def get_tables(self, database: Optional[str] = None, schema: Optional[str] = None) -> list[str]:
        """
        获取SQLite数据库下的所有表名

        Args:
            database: 数据库名称，SQLite中忽略此参数
            schema: schema名称，SQLite不支持schema，忽略此参数

        Returns:
            List[str]: 表名列表
        """
        self._connect()
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """
            )
            tables = [row[0] for row in cursor.fetchall()]
            return tables
        finally:
            cursor.close()

    def get_views(self, database: Optional[str] = None, schema: Optional[str] = None) -> list[str]:
        """
        获取SQLite数据库下的所有视图名

        Args:
            database: 数据库名称，SQLite中忽略此参数
            schema: schema名称，SQLite不支持schema，忽略此参数

        Returns:
            List[str]: 视图名列表
        """
        self._connect()
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='view' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
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
        获取SQLite指定表的结构信息

        Args:
            table_name: 表名
            database: 数据库名称，SQLite中忽略此参数
            schema: schema名称，SQLite不支持schema，忽略此参数

        Returns:
            List[Dict[str, Any]]: 表结构信息，包括字段名、类型、是否为主键等
        """
        self._connect()
        cursor = self.connection.cursor()
        try:
            # 获取表结构信息
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            # 获取主键信息
            cursor.execute(f"PRAGMA table_info({table_name})")
            primary_keys = []
            for col in columns:
                if col[5] == 1:  # pk字段，1表示主键
                    primary_keys.append(col[1])  # name字段

            result = []
            for col in columns:
                field_name = col[1]  # name
                data_type = col[2]  # type
                is_nullable = col[3] == 0  # notnull,0表示可为空
                default_value = col[4]  # dflt_value
                is_pk = col[5] == 1  # pk

                result.append(
                    {
                        "field_name": field_name,
                        "data_type": data_type,
                        "is_nullable": is_nullable,
                        "default_value": default_value,
                        "is_primary_key": is_pk,
                        "comment": "",  # SQLite的PRAGMA table_info不包含注释
                    }
                )

            return result
        finally:
            cursor.close()

    def execute_query(
        self, query: str, params: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        """
        执行SQLite查询

        返回结果会自动处理特殊字段类型（时间类型、BLOB类型、DECIMAL等）

        Args:
            query: SQL查询语句
            params: 查询参数(SQLite使用?占位符)

        Returns:
            List[Dict[str, Any]]: 查询结果
        """
        self._connect()
        cursor = self.connection.cursor()
        try:
            if params:
                # SQLite使用?占位符，需要将字典参数转换为元组
                if isinstance(params, dict):
                    # 对于命名参数，SQLite支持:name格式
                    cursor.execute(query, params)
                else:
                    cursor.execute(query, params)
            else:
                cursor.execute(query)

            # 获取列名
            columns = (
                [description[0] for description in cursor.description] if cursor.description else []
            )

            # 转换为字典列表
            rows = cursor.fetchall()
            result = []
            for row in rows:
                result.append(dict(zip(columns, row, strict=True)))

            # 规范化查询结果，处理特殊类型
            return normalize_query_results(result)
        finally:
            cursor.close()

    def close(self):
        """
        关闭SQLite连接
        """
        if self.connection:
            self.connection.close()
            self.connection = None
