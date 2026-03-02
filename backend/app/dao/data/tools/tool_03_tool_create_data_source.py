"""工具初始化数据: tool_create_data_source"""

DESCRIPTION = """创建并保存数据源配置到系统

该工具用于将数据库连接配置保存到系统中，以便后续使用。在创建之前，需要先使用 tool_test_data_source 测试连接是否可用。

重要提示：
- code 和 name 参数应该根据连接配置信息智能生成，使其具有描述性和唯一性
- code 是唯一标识符，必须唯一，建议使用小写字母、数字和下划线的组合
- name 是显示名称，应该清晰描述数据源的用途或位置

Args:
    code: 数据源编码（唯一标识符）。格式要求：只能包含小写字母、数字和下划线，不能包含空格和特殊字符。
        可以由大模型生成，生成建议：可以使用格式`{platform}{序号}`，序号为两位数字（01, 02, 03...）

    name: 数据源显示名称（人类可读的描述性名称）。格式要求：可以是中文、英文或混合，建议使用有意义的描述。
        生成建议：基于平台类型、主机地址、数据库名等信息生成友好的名称。
        示例："MySQL生产环境-测试数据库", "PostgreSQL本地开发库", "SQL Server销售数据库（192.168.1.100）"。
        命名规则：{平台类型} {环境/位置} - {数据库名}，如 "MySQL 生产环境 - 用户数据库"。

    platform: 数据库平台类型，必须是以下之一：mysql, postgresql, sqlserver, oracle, clickhouse, doris, sqlite

    host: 数据库服务器的主机地址，例如：localhost, 192.168.1.100, db.example.com。注意：SQLite不需要此参数，可以传空字符串

    port: 数据库服务器的端口号。
        MySQL默认3306,PostgreSQL默认5432,SQL Server默认1433,Oracle默认1521,ClickHouse默认9000,Doris默认9030。
        注意：SQLite不需要此参数，可以传0。

    username: 用于连接数据库的用户名。注意：SQLite不需要此参数，可以传空字符串

    password: 对应用户名的密码。注意：SQLite不需要此参数，可以传空字符串

    database: 要连接的数据库名称。对于SQLite，此参数为文件路径（相对于backend/local_sqlite目录，如：chinook.sqlite），或绝对路径

Returns:
    str: 创建结果
        - 成功时：返回创建成功的信息，包括数据源ID、编码、名称、平台、主机和数据库等详细信息
        - 失败时：返回错误原因，常见错误包括：
            * "创建数据源失败：数据源编码已存在" - code参数重复
            * "创建数据源时发生未知错误：[错误详情]" - 其他系统错误

Example:
    创建MySQL数据源：
    tool_create_data_source(
        code="mysql_prod_192_168_1_100_users",
        name="MySQL生产环境-用户数据库",
        platform="mysql",
        host="192.168.1.100",
        port=3306,
        username="dbuser",
        password="securepassword",
        database="users"
    )

    创建PostgreSQL数据源：
    tool_create_data_source(
        code="postgresql_local_dev",
        name="PostgreSQL本地开发库",
        platform="postgresql",
        host="localhost",
        port=5432,
        username="postgres",
        password="postgres",
        database="devdb"
    )

    创建SQLite数据源：
    tool_create_data_source(
        code="sqlite_chinook",
        name="SQLite - Chinook数据库",
        platform="sqlite",
        host="",
        port=0,
        username="",
        password="",
        database="chinook.sqlite"
    )

Note:
    - 建议在创建数据源之前先调用 tool_test_data_source 验证连接
    - code 必须唯一，如果已存在相同code的数据源，创建会失败
    - 连接配置信息（host, port, username, password, database）会被加密存储
"""

CONTENT = """def tool_create_data_source(
    code: str,
    name: str,
    platform: str,
    host: str,
    port: int,
    username: str,
    password: str,
    database: str,
) -> str:
    import json
    from app.dao.database import SessionLocal
    from app.service.data_source_service import DataSourceCreate
    from app.service.data_source_service import DataSourceService
    db = SessionLocal()
    try:
        # 构建数据库配置
        db_config = {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "database": database,
        }
        setting = json.dumps(db_config)

        data_source_data = DataSourceCreate(
            code=code, name=name, platform=platform, setting=setting
        )
        data_source = DataSourceService.create_data_source(
            db=db, data_source_data=data_source_data, create_user_id=1
        )

        success_msg = f"数据源创建成功！ ID: {data_source.id}；编码：{data_source.code}；名称：{data_source.name}；平台：{data_source.platform}；主机：{host}:{port}；数据库：{database}"

        return success_msg
    except Exception as e:
        error_msg = f"创建数据源失败：{e!s}"
        return error_msg
    finally:
        db.close()
"""

ROW = {
    "tool": "tool_create_data_source",
    "description": DESCRIPTION,
    "parameters": "",
    "content": CONTENT,
    "extend": "",
    "id": 3,
}
