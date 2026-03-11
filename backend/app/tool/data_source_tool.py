"""
数据源相关工具
"""

import contextlib
import json

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.connector.factory import ConnectorFactory
from app.core.json_utils import json_dumps, normalize_query_results
from app.core.logging import get_logger
from app.dao.database import SessionLocal
from app.dao.models import TbDataSource
from app.tool.tool_utils import format_tool_params

logger = get_logger("data_source_tool")

# 日志消息截取长度常量
LOG_MESSAGE_TRUNCATE_LENGTH = 100


def get_data_source(db: Session, ds_id_or_code: str):
    if ds_id_or_code.isdigit():
        ds_id = int(ds_id_or_code)
        return db.query(TbDataSource).filter(TbDataSource.id == ds_id).first()
    else:
        code = ds_id_or_code
        return db.query(TbDataSource).filter(TbDataSource.code == code).first()


@tool
def tool_test_data_source_setting(
    platform: str, host: str, port: int, username: str, password: str, database: str
) -> str:
    """
    测试数据源连接配置是否可用

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
        tool_test_data_source_setting(
            platform="mysql",
            host="localhost",
            port=3306,
            username="root",
            password="mypassword",
            database="testdb"
        )
    """
    logger.info(
        f"[TOOL-CALL] tool_test_data_source_setting - {format_tool_params(platform=platform, host=host, port=port, username=username, password=password, database=database)}"
    )
    try:
        # 创建连接器实例
        connector = ConnectorFactory.create_connector(
            platform, host=host, port=port, username=username, password=password, database=database
        )

        # 测试连接
        test_result = connector.test_connection()

        if test_result.success:
            success_msg = f"数据源连接测试成功：{test_result.message}"
            logger.info(
                f"[TOOL-RESULT] tool_test_data_source_setting - 成功：{test_result.message}"
            )
            return success_msg
        else:
            error_msg = f"数据源连接测试失败：{test_result.message}"
            logger.warning(
                f"[TOOL-RESULT] tool_test_data_source_setting - 失败：{test_result.message}"
            )
            return error_msg

    except ValueError:
        error_msg = f"不支持的数据库类型：{platform}。支持的类型：{', '.join(ConnectorFactory.get_supported_dbs())}"
        logger.exception("[TOOL-RESULT] tool_test_data_source_setting - 失败")
        return error_msg
    except Exception as e:
        error_msg = f"测试数据源连接时发生错误：{e!s}"
        logger.exception("[TOOL-RESULT] tool_test_data_source_setting - 失败")
        return error_msg


@tool
def tool_execute_sql_on_data_source(ds_id_or_code: str, sql: str) -> str:
    """
    在指定数据源上执行 SQL，通常用于探索数据源的表数据。

    与 tool_execute_sql_on_system_db 不同：本工具操作的是用户配置的**业务数据源**，用于查询、探索表数据；
    系统表（如 tb_data_model、tb_data_source）的增删改查应使用 tool_execute_sql_on_system_db。

    该工具用于在已配置的数据源上执行 SQL 查询语句，并返回查询结果。支持通过数据源编码（code）或数据源 ID 来指定数据源。

    使用场景：
    - 探索、查询数据源中的表数据
    - 执行数据分析 SQL 语句
    - 验证数据源中的数据内容
    - 执行统计查询、聚合查询等

    重要提示：
    - 该工具只支持SELECT查询语句，不支持INSERT、UPDATE、DELETE等修改数据的操作
    - SQL语句应该经过验证，避免SQL注入攻击
    - 查询结果会自动处理特殊字段类型（时间类型、BLOB类型、DECIMAL等）

    Args:
        ds_id_or_code: 数据源标识符，可以是数据源编码（code）或数据源ID（字符串格式的数字）
            - 如果以数字开头，则视为数据源ID
            - 否则视为数据源编码（code）
            - 示例：
              * "mysql01" - 数据源编码
              * "1" - 数据源ID
              * "123" - 数据源ID

        sql: 要执行的SQL查询语句
            - 必须是SELECT查询语句
            - 支持参数化查询（根据数据库类型使用不同的占位符）
            - 示例：
              * "SELECT * FROM users LIMIT 10"
              * "SELECT COUNT(*) as total FROM orders WHERE status = 'completed'"
              * "SELECT id, name, created_at FROM products ORDER BY created_at DESC"

    Returns:
        str: SQL执行结果，JSON格式
            - 成功时：返回查询结果，格式为JSON数组，每个元素是一个字典（行数据）
            - 失败时：返回错误信息
            - 格式示例：
              ```json
              [
                {
                  "id": 1,
                  "name": "张三",
                  "age": 25,
                  "created_at": "2023-01-01T12:00:00",
                  "price": 99.99,
                  "avatar": "<BLOB:base64:iVBORw0KGgoAAAANS...>"
                },
                {
                  "id": 2,
                  "name": "李四",
                  "age": 30,
                  "created_at": "2023-01-02T12:00:00",
                  "price": 199.99,
                  "avatar": null
                }
              ]
              ```
            - 特殊字段类型处理：
              * 时间类型（datetime, date）：转换为ISO格式字符串（如："2023-01-01T12:00:00"）
              * BLOB类型（bytes）：转换为base64编码字符串，格式为"<BLOB:base64:...>"
              * DECIMAL类型：转换为float类型
              * NULL值：保持为null

    Example:
        通过数据源编码执行查询：
        tool_execute_sql_on_data_source(
            ds_id_or_code="mysql01",
            sql="SELECT * FROM users LIMIT 10"
        )

        通过数据源ID执行查询：
        tool_execute_sql_on_data_source(
            ds_id_or_code="1",
            sql="SELECT COUNT(*) as total FROM orders WHERE status = 'completed'"
        )

        执行带条件的查询：
        tool_execute_sql_on_data_source(
            ds_id_or_code="postgresql01",
            sql="SELECT id, name, created_at FROM products WHERE price > 100 ORDER BY created_at DESC"
        )

    Note:
        - 只支持SELECT查询，不支持数据修改操作
        - 查询结果会自动处理特殊字段类型，确保可以正确序列化为JSON
        - 如果数据源不存在或连接失败，会返回相应的错误信息
        - 如果SQL语句执行失败，会返回详细的错误信息
    """
    logger.info(
        f"[TOOL-CALL] tool_execute_sql_on_data_source - {format_tool_params(ds_id_or_code=ds_id_or_code, sql=sql[:LOG_MESSAGE_TRUNCATE_LENGTH] + '...' if len(sql) > LOG_MESSAGE_TRUNCATE_LENGTH else sql)}"
    )
    db = SessionLocal()
    try:
        data_source = get_data_source(db, ds_id_or_code)

        if not data_source:
            error_msg = f"数据源不存在：{ds_id_or_code}"
            logger.error(f"[TOOL-RESULT] tool_execute_sql_on_data_source - 失败：{error_msg}")
            return error_msg

        # 解析setting配置
        try:
            setting = json.loads(data_source.setting)
        except json.JSONDecodeError:
            error_msg = f"数据源配置格式错误：ID={data_source.id}"
            logger.exception("[TOOL-RESULT] tool_execute_sql_on_data_source - 失败")
            return error_msg

        platform = data_source.platform
        host = setting.get("host")
        port = setting.get("port")
        username = setting.get("username")
        password = setting.get("password")
        database = setting.get("database")
        connector = None
        # 执行SQL查询
        try:
            # 创建连接器实例
            connector = ConnectorFactory.create_connector(
                platform,
                host=host,
                port=port,
                username=username,
                password=password,
                database=database,
            )
            # 执行查询（连接器的execute_query已经处理了特殊类型）
            results = connector.execute_query(sql)

            # 规范化查询结果（处理特殊类型）
            normalized_results = normalize_query_results(results)

            # 转换为JSON字符串
            result_json = json_dumps(normalized_results, ensure_ascii=False, indent=2)

            logger.info(
                f"[TOOL-RESULT] tool_execute_sql_on_data_source - 成功：返回 {len(results)} 条记录"
            )
            return result_json

        except Exception as e:
            error_msg = f"执行SQL查询时发生错误：{e!s}"
            logger.error(
                f"[TOOL-RESULT] tool_execute_sql_on_data_source - 失败：{error_msg}", exc_info=True
            )
            return error_msg
        finally:
            # 关闭连接器连接
            if connector:
                with contextlib.suppress(Exception):
                    connector.close()

    except Exception as e:
        error_msg = f"处理SQL执行请求时发生错误：{e!s}"
        logger.error(
            f"[TOOL-RESULT] tool_execute_sql_on_data_source - 失败：{error_msg}", exc_info=True
        )
        return error_msg
    finally:
        db.close()
