from typing import ClassVar

from app.connector.base import BaseConnector


class UnsupportedDatabaseTypeError(ValueError):
    """不支持的数据库类型异常"""

    def __init__(self, db_type: str):
        self.db_type = db_type
        super().__init__(f"Unsupported database type: {db_type}")


class ConnectorFactory:
    """
    数据库连接器工厂类，用于创建不同类型的数据库连接器实例
    """

    # 存储注册的连接器类
    _connectors: ClassVar[dict[str, type[BaseConnector]]] = {}

    # 存储连接器的导入路径，用于延迟加载
    _connector_imports: ClassVar[dict[str, str]] = {
        "mysql": "app.connector.mysql_connector.MySQLConnector",
        "postgresql": "app.connector.postgresql_connector.PostgreSQLConnector",
        "sqlserver": "app.connector.sqlserver_connector.SQLServerConnector",
        "oracle": "app.connector.oracle_connector.OracleConnector",
        "clickhouse": "app.connector.clickhouse_connector.ClickHouseConnector",
        "doris": "app.connector.doris_connector.DorisConnector",
        "sqlite": "app.connector.sqlite_connector.SQLiteConnector",
    }

    @classmethod
    def register_connector(cls, db_type: str, connector_cls: type[BaseConnector]):
        """
        注册数据库连接器类

        Args:
            db_type: 数据库类型，如'mysql', 'postgresql', 'sqlserver', 'oracle', 'clickhouse', 'doris'
            connector_cls: 连接器类，继承自BaseConnector
        """
        cls._connectors[db_type.lower()] = connector_cls

    @classmethod
    def _lazy_import_connector(cls, db_type: str):
        """
        延迟导入连接器类

        Args:
            db_type: 数据库类型
        """
        if db_type not in cls._connectors and db_type in cls._connector_imports:
            import_path = cls._connector_imports[db_type]
            module_path, class_name = import_path.rsplit(".", 1)

            # 动态导入模块
            module = __import__(module_path, fromlist=[class_name])
            connector_cls = getattr(module, class_name)

            # 注册连接器
            cls.register_connector(db_type, connector_cls)

    @classmethod
    def create_connector(cls, db_type: str, **kwargs) -> BaseConnector:
        """
        创建数据库连接器实例

        Args:
            db_type: 数据库类型
            kwargs: 连接器初始化参数

        Returns:
            BaseConnector: 数据库连接器实例

        Raises:
            UnsupportedDatabaseTypeError: 当指定的数据库类型未注册时抛出
        """
        db_type_lower = db_type.lower()

        # 延迟导入连接器
        cls._lazy_import_connector(db_type_lower)

        if db_type_lower not in cls._connectors:
            raise UnsupportedDatabaseTypeError(db_type)

        return cls._connectors[db_type_lower](**kwargs)

    @classmethod
    def get_supported_dbs(cls) -> list[str]:
        """
        获取支持的数据库类型列表

        Returns:
            List[str]: 支持的数据库类型列表
        """
        return list(cls._connector_imports.keys())


def get_connector(db_type: str, **kwargs) -> BaseConnector:
    """
    获取数据库连接器实例的便捷函数

    Args:
        db_type: 数据库类型
        kwargs: 连接器初始化参数

    Returns:
        BaseConnector: 数据库连接器实例
    """
    return ConnectorFactory.create_connector(db_type, **kwargs)
