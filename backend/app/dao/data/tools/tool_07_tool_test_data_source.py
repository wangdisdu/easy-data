"""工具初始化数据: tool_test_data_source"""

DESCRIPTION = """测试数据源连接是否可用

该工具用于验证数据库连接配置是否正确，在创建数据源之前应该先使用此工具测试连接。
工具会尝试连接到指定的数据库，如果连接成功则返回成功信息，如果失败则返回详细的错误原因。

使用场景：
- 在创建数据源配置之前，先测试连接是否可用
- 验证用户提供的数据库连接信息是否正确
- 诊断数据库连接问题

Args:
    platform: 数据库平台类型，必须是以下之一：mysql, postgresql, sqlserver, oracle, clickhouse, doris, sqlite
    host: 数据库服务器的主机地址，例如：localhost, 192.168.1.100, db.example.com。注意：SQLite不需要此参数，可以传空字符串
    port: 数据库服务器的端口号，例如：MySQL默认3306,PostgreSQL默认5432,SQL Server默认1433。注意：SQLite不需要此参数，可以传0
    username: 用于连接数据库的用户名。注意：SQLite不需要此参数，可以传空字符串
    password: 对应用户名的密码。注意：SQLite不需要此参数，可以传空字符串
    database: 要连接的数据库名称。对于SQLite，此参数为文件路径（相对于backend/local_sqlite目录，如：chinook.sqlite），或绝对路径

Returns:
    str: 连接测试结果
        - 成功时：返回 "数据源连接测试成功：[详细信息]"
        - 失败时：返回 "数据源连接测试失败：[错误原因]"，错误原因会包含具体的失败信息，如认证失败、网络不通、数据库不存在等

Example:
    测试MySQL连接：
    tool_test_data_source(
        platform="mysql",
        host="localhost",
        port=3306,
        username="root",
        password="mypassword",
        database="testdb"
    )
"""

CONTENT = """def tool_test_data_source(
    platform: str, host: str, port: int, username: str, password: str, database: str
) -> str:
    from app.connector.factory import ConnectorFactory
    try:
        # 创建连接器实例
        connector = ConnectorFactory.create_connector(
            platform, host=host, port=port, username=username, password=password, database=database
        )

        # 测试连接
        test_result = connector.test_connection()

        if test_result.success:
            success_msg = f"数据源连接测试成功：{test_result.message}"
            return success_msg
        else:
            error_msg = f"数据源连接测试失败：{test_result.message}"
            return error_msg

    except ValueError:
        error_msg = f"不支持的数据库类型：{platform}。支持的类型：{', '.join(ConnectorFactory.get_supported_dbs())}"
        return error_msg
    except Exception as e:
        error_msg = f"测试数据源连接时发生错误：{e!s}"
        return error_msg
"""

ROW = {
    "tool": "tool_test_data_source",
    "description": DESCRIPTION,
    "parameters": "",
    "content": CONTENT,
    "extend": "",
    "id": 7,
}
