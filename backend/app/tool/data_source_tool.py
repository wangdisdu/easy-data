"""
数据源相关工具
"""

import contextlib
import json
from typing import Optional

from jinja2 import Template
from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.connector.factory import ConnectorFactory
from app.core.json_utils import json_dumps, normalize_query_results
from app.core.logging import get_logger
from app.dao.database import SessionLocal
from app.dao.models import TbDataModel, TbDataSource
from app.service.data_source_service import DataSourceCreate, DataSourceService, DataSourceUpdate
from app.tool.data_source_template import DATA_SOURCES_TEMPLATE
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
def tool_test_data_source(
    platform: str, host: str, port: int, username: str, password: str, database: str
) -> str:
    """
    测试数据源连接是否可用

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
    logger.info(
        f"[TOOL-CALL] tool_test_data_source - {format_tool_params(platform=platform, host=host, port=port, username=username, password=password, database=database)}"
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
            logger.info(f"[TOOL-RESULT] tool_test_data_source - 成功：{test_result.message}")
            return success_msg
        else:
            error_msg = f"数据源连接测试失败：{test_result.message}"
            logger.warning(f"[TOOL-RESULT] tool_test_data_source - 失败：{test_result.message}")
            return error_msg

    except ValueError:
        error_msg = f"不支持的数据库类型：{platform}。支持的类型：{', '.join(ConnectorFactory.get_supported_dbs())}"
        logger.exception("[TOOL-RESULT] tool_test_data_source - 失败")
        return error_msg
    except Exception as e:
        error_msg = f"测试数据源连接时发生错误：{e!s}"
        logger.exception("[TOOL-RESULT] tool_test_data_source - 失败")
        return error_msg


@tool
def tool_create_data_source(
    code: str,
    name: str,
    platform: str,
    host: str,
    port: int,
    username: str,
    password: str,
    database: str,
) -> str:
    """
    创建并保存数据源配置到系统

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
    logger.info(
        f"[TOOL-CALL] tool_create_data_source - {format_tool_params(code=code, name=name, platform=platform, host=host, port=port, username=username, password=password, database=database)}"
    )
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

        success_msg = f"数据源创建成功！\n- ID: {data_source.id}\n- 编码：{data_source.code}\n- 名称：{data_source.name}\n- 平台：{data_source.platform}\n- 主机：{host}:{port}\n- 数据库：{database}"

        logger.info(
            f"[TOOL-RESULT] tool_create_data_source - 成功：{data_source.code} (ID: {data_source.id})"
        )
        return success_msg

    except Exception as e:
        error_msg = f"创建数据源失败：{e!s}"
        logger.exception("[TOOL-RESULT] tool_create_data_source - 失败")
        return error_msg
    finally:
        db.close()


@tool
def tool_list_data_source() -> str:
    """
    获取系统中所有已配置的数据源列表

    该工具用于查询和展示系统中所有已保存的数据源配置信息。返回结果使用markdown格式，便于阅读和展示。
    使用场景：
    - 查看系统中已配置的所有数据源
    - 了解数据源的连接配置信息
    - 查找特定数据源的编码、名称或者连接配置
    - 检查数据源是否已经存在了
    - 检查数据源的语义说明和描述信息

    返回信息包括：
    - 数据源ID：系统内部唯一标识
    - 编码（code）：用户定义的唯一标识符
    - 名称（name）：数据源的显示名称
    - 平台（platform）：数据库类型
    - 连接配置（setting）：完整的连接配置JSON，包含host、port、username、password、database
    - 语义说明（semantic）：数据源的业务语义描述（如果有）
    - 描述（description）：数据源的详细描述（如果有）
    - 创建时间（create_time）：数据源创建的时间戳

    Args:

    Returns:
        str: 数据源列表信息，使用markdown格式返回。如果有数据源，返回格式化的markdown列表，每个数据源包含完整信息。
            如果没有数据源，返回 "当前系统内没有配置任何数据源。"。
            格式示例：
            ```
            # 数据源列表
            系统内共找到 1 个数据源：
            ## MySQL生产环境-用户数据库 (mysql_prod_192_168_1_100_users)
            **ID**: 1
            **编码**: mysql_prod_192_168_1_100_users
            **名称**: MySQL生产环境-用户数据库
            **平台**: mysql
            **连接配置**:
            ```json
            {"host": "192.168.1.100", "port": 3306, "username": "dbuser", "password": "***", "database": "users"}
            ```
            **创建时间**: 1234567890
            ```

    """

    logger.info("[TOOL-CALL] tool_list_data_source")
    db = SessionLocal()
    try:
        # 直接查询所有数据源，不分页
        data_sources = db.query(TbDataSource).all()
        total = len(data_sources)

        # 使用模板渲染markdown
        template = Template(DATA_SOURCES_TEMPLATE)
        result = template.render(data_sources=data_sources, total=total)

        logger.info(
            f"[TOOL-RESULT] tool_list_data_source - 成功：获取 {len(data_sources)} 条数据源信息"
        )
        return result

    except Exception as e:
        error_msg = f"获取数据源列表时发生错误：{e!s}"
        logger.exception("[TOOL-RESULT] tool_list_data_source - 失败")
        return error_msg
    finally:
        db.close()


@tool
def tool_get_data_source(ds_id_or_code: str) -> str:
    """
    根据数据源ID或编码获取数据源信息（主要是code）

    该工具用于根据数据源ID或编码获取数据源的基本信息，特别是数据源的编码（code）。
    获取正确的数据源code非常重要，因为所有执行SQL的工具（tool_execute_sql_data_source）都需要使用数据源的code。

    使用场景：
    - 从数据模型中获取ds_id后，需要获取对应的数据源code
    - 验证数据源是否存在
    - 获取数据源的基本信息（code、platform等）

    Args:
        ds_id_or_code: 数据源标识符（必填）
            - 如果为数字字符串，视为数据源ID
            - 否则视为数据源编码（code）
            - 示例：
              * "1" - 数据源ID
              * "mysql_prod_192_168_1_100_users" - 数据源编码

    Returns:
        str: 数据源信息，JSON格式
            - 格式示例：
              ```json
              {
                "id": 1,
                "code": "mysql_prod_192_168_1_100_users",
                "name": "MySQL生产环境-用户数据库",
                "platform": "mysql",
                "ds_id": 1
              }
              ```
            - 如果数据源不存在，返回错误信息

    Example:
        根据ID获取数据源：
        tool_get_data_source(ds_id_or_code="1")

        根据编码获取数据源：
        tool_get_data_source(ds_id_or_code="mysql_prod_192_168_1_100_users")

    Note:
        - 该工具主要用于获取数据源的code，以便后续使用tool_execute_sql_data_source时传入正确的code
        - code是执行SQL时必须使用的标识符
    """
    logger.info(
        f"[TOOL-CALL] tool_get_data_source - {format_tool_params(ds_id_or_code=ds_id_or_code)}"
    )
    db = SessionLocal()
    try:
        data_source = get_data_source(db, ds_id_or_code)

        if not data_source:
            error_msg = f"数据源不存在：{ds_id_or_code}"
            logger.error(f"[TOOL-RESULT] tool_get_data_source - 失败：{error_msg}")
            return error_msg

        # 转换为字典，只返回必要的信息
        result = {
            "id": data_source.id,
            "code": data_source.code,
            "name": data_source.name,
            "platform": data_source.platform,
            "ds_id": data_source.id,  # 为了兼容，也提供ds_id字段
        }

        result_json = json_dumps(result, ensure_ascii=False, indent=2)
        logger.info(
            f"[TOOL-RESULT] tool_get_data_source - 成功：{ds_id_or_code} (code: {data_source.code})"
        )
        return result_json

    except Exception as e:
        error_msg = f"获取数据源信息时发生错误：{e!s}"
        logger.exception("[TOOL-RESULT] tool_get_data_source - 失败")
        return error_msg
    finally:
        db.close()


@tool
def tool_delete_data_source(ds_id_or_code: str) -> str:
    """
    删除数据源（若存在关联数据模型则拒绝）

    该工具用于删除指定的数据源。如果数据源下存在关联的数据模型（tb_data_model.ds_id = 数据源ID），将拒绝删除并提示先处理关联模型。

    使用场景：
    - 删除不再需要的数据源配置
    - 清理无关联模型的数据源

    重要提示：
    - 当数据源下存在关联的数据模型时，会拒绝删除并返回提示
    - 删除操作不可逆，请谨慎使用
    - 删除操作会同时删除关联的工作空间关系

    Args:
        ds_id_or_code: 数据源标识符（必填）。
            如果为数字字符串，视为数据源ID；否则视为数据源编码（code）。
            示例："1"（数据源ID）、"mysql01"（数据源编码）。

    Returns:
        str: 删除结果
            - 成功时：返回 "数据源删除成功：ID={ds_id}"
            - 失败时：返回错误原因
            - 常见错误：
              * "数据源不存在：{ds_id_or_code}" - 数据源不存在
              * "数据源下存在 X 个关联的数据模型，无法删除，请先删除关联模型" - 存在关联模型
              * "删除数据源失败：{错误信息}" - 删除失败

    Example:
        删除数据源（使用ID）:
        tool_delete_data_source(ds_id_or_code="1")

        删除数据源（使用编码）:
        tool_delete_data_source(ds_id_or_code="mysql01")

    Note:
        - ds_id_or_code 必须是已存在的数据源ID或编码
        - 如果存在关联数据模型会直接拒绝删除，请先清理关联模型
    """
    logger.info(
        f"[TOOL-CALL] tool_delete_data_source - {format_tool_params(ds_id_or_code=ds_id_or_code)}"
    )
    db = SessionLocal()
    try:
        data_source = get_data_source(db, ds_id_or_code)

        if not data_source:
            error_msg = f"数据源不存在：{ds_id_or_code}"
            logger.error(f"[TOOL-RESULT] tool_delete_data_source - 失败：{error_msg}")
            return error_msg

        ds_id = data_source.id

        # 检查是否存在关联数据模型，如果有则拒绝删除
        related_model_count = db.query(TbDataModel).filter(TbDataModel.ds_id == ds_id).count()
        if related_model_count > 0:
            error_msg = (
                f"数据源下存在 {related_model_count} 个关联的数据模型，无法删除，请先删除关联模型"
            )
            logger.error(f"[TOOL-RESULT] tool_delete_data_source - 失败：{error_msg}")
            return error_msg

        # 删除数据源（DataSourceService 内部会删除工作空间关系）
        DataSourceService.delete_data_source(db=db, data_source_id=ds_id)

        success_msg = f"数据源删除成功：{ds_id_or_code} (ID: {ds_id})"
        logger.info(f"[TOOL-RESULT] tool_delete_data_source - 成功：{ds_id_or_code} (ID: {ds_id})")
        return success_msg

    except Exception as e:
        error_msg = f"删除数据源失败：{e!s}"
        logger.exception("[TOOL-RESULT] tool_delete_data_source - 失败")
        return error_msg
    finally:
        db.close()


@tool
def tool_update_data_source(
    ds_id_or_code: str,
    name: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> str:
    """
    更新数据源的名称、账号密码等信息

    该工具用于更新已存在数据源的部分信息，支持更新名称、账号密码等。

    使用场景：
    - 修改数据源的显示名称
    - 更新数据源的账号密码
    - 修改数据源的连接配置

    重要提示：
    - 只能更新名称、账号密码，不能修改数据源编码（code）、平台类型（platform）等核心信息
    - 如果只更新账号密码，需要提供完整的连接配置（host、port、database等保持不变）
    - 更新账号密码时，需要重新构建 setting JSON

    Args:
        ds_id_or_code: 数据源标识符（必填）。
            如果为数字字符串，视为数据源ID；否则视为数据源编码（code）。
            示例："1"（数据源ID）、"mysql01"（数据源编码）。
        name: 数据源显示名称（可选）.如果提供，则更新数据源的名称。
        username: 新的用户名（可选）.如果提供，则更新数据源的账号。
        password: 新的密码（可选）.如果提供，则更新数据源的密码。

    Returns:
        str: 更新结果
            - 成功时：返回 "数据源更新成功：ID={ds_id}"
            - 失败时：返回错误原因
            - 常见错误：
              * "数据源不存在：{ds_id_or_code}" - 数据源不存在
              * "更新数据源失败：{错误信息}" - 更新失败
              * "必须提供至少一个要更新的字段（name、username、password）" - 未提供任何更新字段

    Example:
        只更新名称：
        tool_update_data_source(
            ds_id_or_code="1",
            name="MySQL生产环境-新名称"
        )

        只更新账号密码：
        tool_update_data_source(
            ds_id_or_code="mysql01",
            username="newuser",
            password="newpassword"
        )

        同时更新名称和账号密码：
        tool_update_data_source(
            ds_id_or_code="1",
            name="MySQL生产环境-新名称",
            username="newuser",
            password="newpassword"
        )

    Note:
        - ds_id_or_code 必须是已存在的数据源ID或编码
        - 必须提供至少一个要更新的字段（name、username、password）
        - 更新账号密码时，会保留原有的 host、port、database 等配置
    """
    logger.info(
        f"[TOOL-CALL] tool_update_data_source - {format_tool_params(ds_id_or_code=ds_id_or_code, name=name, username=username, password='***' if password else None)}"
    )
    db = SessionLocal()
    try:
        # 检查是否提供了至少一个更新字段
        if not any([name, username, password]):
            error_msg = "必须提供至少一个要更新的字段（name、username、password）"
            logger.error(f"[TOOL-RESULT] tool_update_data_source - 失败：{error_msg}")
            return error_msg

        data_source = get_data_source(db, ds_id_or_code)

        if not data_source:
            error_msg = f"数据源不存在：{ds_id_or_code}"
            logger.error(f"[TOOL-RESULT] tool_update_data_source - 失败：{error_msg}")
            return error_msg

        ds_id = data_source.id

        # 构建更新对象
        data_source_update = DataSourceUpdate()

        # 更新名称
        if name is not None:
            data_source_update.name = name

        # 更新账号密码（需要更新 setting）
        if username is not None or password is not None:
            # 解析现有的 setting
            try:
                setting = json.loads(data_source.setting)
            except json.JSONDecodeError:
                error_msg = f"数据源配置格式错误：ID={ds_id}"
                logger.exception("[TOOL-RESULT] tool_update_data_source - 失败")
                return error_msg

            # 更新账号密码
            if username is not None:
                setting["username"] = username
            if password is not None:
                setting["password"] = password

            # 重新序列化为JSON
            data_source_update.setting = json_dumps(setting, ensure_ascii=False)

            # 执行更新
            DataSourceService.update_data_source(
                db=db,
                data_source_id=ds_id,
                data_source_update=data_source_update,
                update_user_id=1,  # 使用系统用户ID
            )

        success_msg = f"数据源更新成功：{ds_id_or_code} (ID: {ds_id})"
        logger.info(f"[TOOL-RESULT] tool_update_data_source - 成功：{ds_id_or_code} (ID: {ds_id})")
        return success_msg

    except Exception as e:
        error_msg = f"更新数据源失败：{e!s}"
        logger.exception("[TOOL-RESULT] tool_update_data_source - 失败")
        return error_msg

    finally:
        db.close()


@tool
def tool_execute_sql_data_source(ds_id_or_code: str, sql: str) -> str:
    """
    在指定数据源上执行SQL查询

    该工具用于在已配置的数据源上执行SQL查询语句，并返回查询结果。支持通过数据源编码（code）或数据源ID来指定数据源。

    使用场景：
    - 查询数据源中的数据
    - 执行数据分析SQL语句
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
        tool_execute_sql_data_source(
            ds_identifier="mysql01",
            sql="SELECT * FROM users LIMIT 10"
        )

        通过数据源ID执行查询：
        tool_execute_sql_data_source(
            ds_identifier="1",
            sql="SELECT COUNT(*) as total FROM orders WHERE status = 'completed'"
        )

        执行带条件的查询：
        tool_execute_sql_data_source(
            ds_identifier="postgresql01",
            sql="SELECT id, name, created_at FROM products WHERE price > 100 ORDER BY created_at DESC"
        )

    Note:
        - 只支持SELECT查询，不支持数据修改操作
        - 查询结果会自动处理特殊字段类型，确保可以正确序列化为JSON
        - 如果数据源不存在或连接失败，会返回相应的错误信息
        - 如果SQL语句执行失败，会返回详细的错误信息
    """
    logger.info(
        f"[TOOL-CALL] tool_execute_sql_data_source - {format_tool_params(ds_id_or_code=ds_id_or_code, sql=sql[:LOG_MESSAGE_TRUNCATE_LENGTH] + '...' if len(sql) > LOG_MESSAGE_TRUNCATE_LENGTH else sql)}"
    )
    db = SessionLocal()
    try:
        data_source = get_data_source(db, ds_id_or_code)

        if not data_source:
            error_msg = f"数据源不存在：{ds_id_or_code}"
            logger.error(f"[TOOL-RESULT] tool_execute_sql_data_source - 失败：{error_msg}")
            return error_msg

        # 解析setting配置
        try:
            setting = json.loads(data_source.setting)
        except json.JSONDecodeError:
            error_msg = f"数据源配置格式错误：ID={data_source.id}"
            logger.exception("[TOOL-RESULT] tool_execute_sql_data_source - 失败")
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
                f"[TOOL-RESULT] tool_execute_sql_data_source - 成功：返回 {len(results)} 条记录"
            )
            return result_json

        except Exception as e:
            error_msg = f"执行SQL查询时发生错误：{e!s}"
            logger.error(
                f"[TOOL-RESULT] tool_execute_sql_data_source - 失败：{error_msg}", exc_info=True
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
            f"[TOOL-RESULT] tool_execute_sql_data_source - 失败：{error_msg}", exc_info=True
        )
        return error_msg
    finally:
        db.close()
