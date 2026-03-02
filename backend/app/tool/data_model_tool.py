"""
数据模型相关工具
"""

import contextlib
import json

from langchain.tools import tool
from sqlalchemy.orm import Session

from app.connector.factory import ConnectorFactory
from app.core.biz_error import BizError
from app.core.json_utils import json_dumps, normalize_query_results
from app.core.logging import get_logger
from app.dao.database import SessionLocal
from app.dao.models import TbDataModel
from app.service.data_model_service import DataModelCreate, DataModelService, DataModelUpdate
from app.tool.data_source_tool import get_data_source
from app.tool.tool_utils import format_tool_params

logger = get_logger("data_model_tool")

# 日志消息截取长度常量
LOG_MESSAGE_TRUNCATE_LENGTH = 100


def get_data_model(db: Session, dm_id_or_code: str):
    # 根据ID或编码查找指定数据模型
    if dm_id_or_code.isdigit():
        dm_id = int(dm_id_or_code)
        return db.query(TbDataModel).filter(TbDataModel.id == dm_id).first()
    else:
        code = dm_id_or_code
        return db.query(TbDataModel).filter(TbDataModel.code == code).first()


@tool
def tool_get_data_model(dm_id_or_code: str) -> str:
    """
    获取指定数据模型的详细信息

    该工具用于根据数据模型ID或编码获取指定数据模型的详细信息。

    使用场景：
    - 根据ID或编码查找特定数据模型
    - 获取数据模型的详细信息（包括ds_id、platform、type等）
    - 验证数据模型是否存在

    Args:
        dm_id_or_code: 数据模型标识符（必填）
            - 如果为数字字符串，视为数据模型ID
            - 否则视为数据模型编码(code)
            - 示例：
              * "1" - 数据模型ID
              * "public.users" - 数据模型编码

    Returns:
        str: 数据模型详细信息，JSON格式
            - 格式示例：
              ```json
              {
                "id": 1,
                "code": "public.users",
                "name": "users",
                "platform": "postgresql",
                "type": "table",
                "ds_id": 1,
                "semantic": "{\\"type\\": \\"table\\"}",
                "description": null,
                "extend": null,
                "create_time": 1234567890,
                "update_time": 1234567890
              }
              ```
            - 如果数据模型不存在，返回错误信息

    Example:
        根据ID获取数据模型：
        tool_get_data_model(dm_id_or_code="1")

        根据编码获取数据模型：
        tool_get_data_model(dm_id_or_code="public.users")
    """

    logger.info(
        f"[TOOL-CALL] tool_get_data_model - {format_tool_params(dm_id_or_code=dm_id_or_code)}"
    )
    db = SessionLocal()
    try:
        # 根据ID或编码查找指定数据模型
        data_model = get_data_model(db=db, dm_id_or_code=dm_id_or_code)

        if not data_model:
            error_msg = f"数据模型不存在：{dm_id_or_code}"
            logger.error(f"[TOOL-RESULT] tool_get_data_model - 失败：{error_msg}")
            return error_msg

        # 构建模型信息字典
        result = {
            "id": data_model.id,
            "code": data_model.code,
            "name": data_model.name,
            "platform": data_model.platform,
            "type": data_model.type,
            "ds_id": data_model.ds_id,
            "semantic": data_model.semantic,
            "description": data_model.description,
            "extend": data_model.extend,
            "create_time": data_model.create_time,
            "update_time": data_model.update_time,
        }

        result_json = json_dumps(result, ensure_ascii=False, indent=2)

        logger.info(f"[TOOL-RESULT] tool_get_data_model - 成功：{result_json}")

        return result_json

    except Exception as e:
        error_msg = f"获取数据模型信息时发生错误：{e!s}"
        logger.exception("[TOOL-RESULT] tool_get_data_model - 失败")
        return error_msg
    finally:
        db.close()


@tool
def tool_import_data_models_by_data_source(ds_id_or_code: str) -> str:
    """
    自动将指定数据源的所有表和视图转为数据模型

    该工具用于自动扫描指定数据源中的所有表和视图，并为每个表和视图创建对应的数据模型。
    可以一次性批量创建多个数据模型，提高创建效率。

    使用场景：
    - 从数据源自动生成数据模型
    - 批量导入数据库表和视图为数据模型
    - 快速建立数据模型目录

    重要提示：
    - 数据模型的 `code` 必须唯一，如果已存在相同code的数据模型，该条记录会跳过并记录错误
    - 批量创建时，如果某条记录失败，不会影响其他记录的创建
    - 返回结果会包含成功和失败的详细信息

    模型code生成说明：
      * 如果数据库支持schema且设置了schema：code格式为 `{database}.{schema}.{table/view}`
      * 如果不支持schema或未设置schema：code格式为 `{database}.{table/view}`

    模型name生成说明：
      * name直接使用表名或视图名

    Args:
        ds_id_or_code: 数据源标识符，可以是数据源编码(code)或数据源ID（字符串格式的数字）.
            如果以数字开头且全为数字，则视为数据源ID，否则视为数据源编码(code).
            示例:"mysql01"（数据源编码）、"1"（数据源ID）、"123"（数据源ID）.
            注意：数据源必须已配置 database 字段，否则会返回错误。

    Returns:
        str: 批量创建结果，JSON格式
            - 成功时：返回创建结果摘要，包括成功数量、失败数量、成功记录详情和失败记录详情
            - 格式示例：
              ```json
              {
                "success_count": 5,
                "failure_count": 1,
                "total_count": 6,
                "table_count": 4,
                "view_count": 2,
                "success_items": [
                  {
                    "code": "public.users",
                    "name": "users",
                    "type": "table",
                    "id": 1
                  },
                  {
                    "code": "public.orders",
                    "name": "orders",
                    "type": "table",
                    "id": 2
                  },
                  {
                    "code": "public.user_view",
                    "name": "user_view",
                    "type": "view",
                    "id": 3
                  }
                ],
                "failure_items": [
                  {
                    "code": "public.duplicate_table",
                    "name": "duplicate_table",
                    "type": "table",
                    "error": "数据模型编码已存在"
                  }
                ]
              }
              ```
            - 如果所有记录都成功:failure_count 为 0,failure_items 为空数组
            - 如果所有记录都失败:success_count 为 0,success_items 为空数组

    Example:
        自动创建数据模型（PostgreSQL，使用数据源配置中的database和默认schema 'public'）:
        tool_import_data_models_auto(
            ds_id_or_code="postgresql01"
        )

        自动创建数据模型（MySQL，使用数据源配置中的database）:
        tool_import_data_models_auto(
            ds_id_or_code="mysql01"
        )

        自动创建数据模型（SQLite，使用数据源配置中的database文件路径）:
        tool_import_data_models_auto(
            ds_id_or_code="sqlite01"
        )

    Note:
        - code 必须唯一，如果已存在相同code的数据模型，该条记录会跳过
        - 批量创建时，如果某条记录失败，不会影响其他记录的创建
        - 如果数据源配置中缺少 database 字段，会返回错误
    """

    logger.info(
        f"[TOOL-CALL] tool_import_data_models_auto - {format_tool_params(ds_id_or_code=ds_id_or_code)}"
    )
    db = SessionLocal()
    try:
        # 解析数据源标识符
        data_source = get_data_source(db, ds_id_or_code)

        if not data_source:
            error_msg = f"数据源不存在：{ds_id_or_code}"
            logger.error(f"[TOOL-RESULT] tool_import_data_models_auto - 失败：{error_msg}")
            return error_msg

        setting = json.loads(data_source.setting)

        platform = data_source.platform
        host = setting.get("host")
        port = setting.get("port")
        username = setting.get("username")
        password = setting.get("password")
        database = setting.get("database")
        schema = setting.get("schema")

        # 从数据源配置中获取database
        if not database:
            error_msg = "数据源配置中缺少 database 字段，无法自动导入数据模型"
            logger.error(f"[TOOL-RESULT] tool_import_data_models_auto - 失败：{error_msg}")
            return error_msg

        logger.debug(
            f"[TOOL-INTERNAL] tool_import_data_models_auto - 使用数据源配置中的database: {database}"
        )

        if schema:
            logger.debug(
                f"[TOOL-INTERNAL] tool_import_data_models_auto - 使用数据源配置中的schema: {schema}"
            )

        # 创建连接器实例
        connector = None
        # 获取表和视图列表
        try:
            connector = ConnectorFactory.create_connector(
                platform,
                host=host,
                port=port,
                username=username,
                password=password,
                database=database,
            )
            # 获取所有表
            tables = connector.get_tables(database=database, schema=schema)
            logger.debug(
                f"[TOOL-INTERNAL] tool_import_data_models_auto - 获取到 {len(tables)} 个表"
            )

            # 获取所有视图
            views = connector.get_views(database=database, schema=schema)
            logger.debug(
                f"[TOOL-INTERNAL] tool_import_data_models_auto - 获取到 {len(views)} 个视图"
            )

        except Exception as e:
            error_msg = f"获取表和视图列表时发生错误：{e!s}"
            logger.error(
                f"[TOOL-RESULT] tool_import_data_models_auto - 失败：{error_msg}", exc_info=True
            )
            return error_msg
        finally:
            # 关闭连接器连接
            if connector:
                with contextlib.suppress(Exception):
                    connector.close()

        # 生成code的前缀
        # 如果提供了schema，code格式为 {database}.{schema}.{table/view}，否则为 {database}.{table/view}
        code_prefix = f"{database}.{schema}" if schema else database

        success_items = []
        failure_items = []

        def create_data_model_for_item(item_name: str, item_type: str, type_label: str) -> None:
            """为单个表或视图创建数据模型的辅助函数

            Args:
                item_name: 表名或视图名
                item_type: 类型，'table' 或 'view'
                type_label: 类型标签，用于日志显示，'表' 或 '视图'
            """
            model_code = f"{code_prefix}.{item_name}"
            try:
                # 构建DataModelCreate对象
                data_model_create = DataModelCreate(
                    code=model_code,
                    name=item_name,
                    platform=platform,
                    type=item_type,
                    ds_id=data_source.id,
                    description=None,
                    extend=None,
                    workspace_ids=None,
                )
                # 创建数据模型
                created_model = DataModelService.create_data_model(
                    db=db,
                    data_model_data=data_model_create,
                    create_user_id=1,  # 使用系统用户ID
                )
                success_items.append(
                    {
                        "code": created_model.code,
                        "name": created_model.name,
                        "type": item_type,
                        "id": created_model.id,
                    }
                )
                logger.debug(
                    f"[TOOL-INTERNAL] tool_import_data_models_auto - 成功创建数据模型（{type_label}）: {model_code} (ID: {created_model.id})"
                )
            except BizError as e:
                failure_items.append(
                    {
                        "code": model_code,
                        "name": item_name,
                        "type": item_type,
                        "error": e.message,
                    }
                )
                logger.debug(
                    f"[TOOL-INTERNAL] tool_import_data_models_auto - 创建数据模型失败（{type_label}）: {model_code}, 错误：{e.message}"
                )

        # 为每个表创建数据模型
        for table_name in tables:
            create_data_model_for_item(table_name, "table", "表")

        # 为每个视图创建数据模型
        for view_name in views:
            create_data_model_for_item(view_name, "view", "视图")

        # 构建返回结果
        total_count = len(tables) + len(views)

        result = {
            "success_count": len(success_items),
            "failure_count": len(failure_items),
            "total_count": total_count,
            "table_count": len(tables),
            "view_count": len(views),
            "success_items": success_items,
            "failure_items": failure_items,
        }

        result_json = json_dumps(result, ensure_ascii=False, indent=2)

        logger.info(
            f"[TOOL-RESULT] tool_import_data_models_auto - 成功 {len(success_items)} 条，失败 {len(failure_items)} 条（表：{len(tables)}, 视图：{len(views)})"
        )
        return result_json

    except Exception as e:
        error_msg = f"自动创建数据模型时发生错误：{e!s}"
        logger.error(
            f"[TOOL-RESULT] tool_import_data_models_auto - 失败：{error_msg}", exc_info=True
        )
        return error_msg
    finally:
        db.close()


@tool
def tool_update_data_model_semantic_and_summary(
    dm_id_or_code: str, semantic: str, summary: str
) -> str:
    """
    同时更新数据模型的语义说明(semantic)和摘要说明(summary)字段

    该工具用于同时更新已存在数据模型的语义说明和摘要说明信息。
    语义说明通常包含数据模型的结构化信息(JSON格式)，摘要说明通常包含Markdown格式的字段说明和数据总结。

    使用场景：
    - 在生成数据模型语义说明后，同时更新语义说明和摘要说明
    - 批量更新数据模型的语义和摘要信息

    Args:
        dm_id_or_code: 数据模型标识符（必填）.
            如果为数字字符串，视为数据模型ID;否则视为数据模型编码(code).
            示例:"1"（数据模型ID）、"public.users"（数据模型编码）.
        semantic: 语义说明内容，通常是JSON格式的数据模型信息。
            建议使用JSON格式，便于后续解析和使用。
        summary: 摘要说明内容，建议使用 Markdown 格式。
            包含字段说明和数据总结。

    Returns:
        str: 更新结果
            - 成功时：返回 "数据模型语义说明和摘要说明更新成功：ID={dm_id}"
            - 失败时：返回错误原因
    """
    logger.info(
        f"[TOOL-CALL] tool_update_data_model_semantic_and_summary - {format_tool_params(dm_id_or_code=dm_id_or_code, semantic=semantic[:LOG_MESSAGE_TRUNCATE_LENGTH] + '...' if len(semantic) > LOG_MESSAGE_TRUNCATE_LENGTH else semantic, summary=summary[:LOG_MESSAGE_TRUNCATE_LENGTH] + '...' if len(summary) > LOG_MESSAGE_TRUNCATE_LENGTH else summary)}"
    )
    db = SessionLocal()
    try:
        # 根据ID或编码查找数据模型
        data_model = get_data_model(db=db, dm_id_or_code=dm_id_or_code)

        if not data_model:
            error_msg = f"数据模型不存在：{dm_id_or_code}"
            logger.error(
                f"[TOOL-RESULT] tool_update_data_model_semantic_and_summary - 失败：{error_msg}"
            )
            return error_msg

        # 同时更新 semantic 和 summary 字段
        data_model_update = DataModelUpdate(semantic=semantic, summary=summary)

        DataModelService.update_data_model(
            db=db,
            data_model_id=data_model.id,
            data_model_update=data_model_update,
            update_user_id=1,  # 使用系统用户ID
        )

        success_msg = f"数据模型语义说明和摘要说明更新成功：{dm_id_or_code} (ID: {data_model.id})"
        logger.info(
            f"[TOOL-RESULT] tool_update_data_model_semantic_and_summary - 成功：{dm_id_or_code} (ID: {data_model.id})"
        )
        return success_msg
    except Exception as e:
        error_msg = f"更新数据模型语义说明和摘要说明失败：{e!s}"
        logger.exception("[TOOL-RESULT] tool_update_data_model_semantic_and_summary - 失败")
        return error_msg
    finally:
        db.close()


@tool
def tool_delete_data_model(dm_id_or_code: str) -> str:
    """
    删除数据模型

    该工具用于删除指定的数据模型。支持通过数据模型ID或编码(code)来指定要删除的数据模型。

    使用场景：
    - 删除不再需要的数据模型
    - 清理错误导入的数据模型
    - 删除关联的数据模型

    重要提示：
    - 删除操作不可逆，请谨慎使用
    - 删除数据模型时，会同时删除关联的工作空间关系

    Args:
        dm_id_or_code: 数据模型标识符（必填）.
            如果为数字字符串，视为数据模型ID;否则视为数据模型编码(code).
            示例:"1"（数据模型ID）、"public.users"（数据模型编码）.

    Returns:
        str: 删除结果
            - 成功时：返回 "数据模型删除成功：ID={dm_id}"
            - 失败时：返回错误原因
            - 常见错误：
              * "数据模型不存在：{dm_id_or_code}" - 数据模型不存在
              * "删除数据模型失败：{错误信息}" - 删除失败

    Example:
        删除数据模型（使用ID）:
        tool_delete_data_model(dm_id_or_code="1")

        删除数据模型（使用编码）:
        tool_delete_data_model(dm_id_or_code="public.users")

    Note:
        - dm_id_or_code 必须是已存在的数据模型ID或编码
        - 删除操作不可逆，请确认后再执行
        - 删除操作会同时删除关联的工作空间关系
    """
    logger.info(
        f"[TOOL-CALL] tool_delete_data_model - {format_tool_params(dm_id_or_code=dm_id_or_code)}"
    )
    db = SessionLocal()
    try:
        # 根据ID或编码查找数据模型
        data_model = get_data_model(db=db, dm_id_or_code=dm_id_or_code)

        if not data_model:
            error_msg = f"数据模型不存在：{dm_id_or_code}"
            logger.error(f"[TOOL-RESULT] tool_delete_data_model - 失败：{error_msg}")
            return error_msg

        dm_id = data_model.id

        # 删除数据模型
        DataModelService.delete_data_model(db=db, data_model_id=dm_id)

        success_msg = f"数据模型删除成功：{dm_id_or_code} (ID: {dm_id})"
        logger.info(f"[TOOL-RESULT] tool_delete_data_model - 成功：{dm_id_or_code} (ID: {dm_id})")
        return success_msg
    except Exception as e:
        error_msg = f"处理数据模型删除时发生错误：{e!s}"
        logger.exception("[TOOL-RESULT] tool_delete_data_model - 失败")
        return error_msg
    finally:
        db.close()


@tool
def tool_delete_data_models_by_data_source(ds_id_or_code: str) -> str:
    """
    删除指定数据源下的所有数据模型

    该工具用于删除指定数据源下的所有数据模型。支持通过数据源ID或编码(code)来指定数据源。

    使用场景：
    - 清空数据源下的所有数据模型
    - 重新导入数据源的数据模型前，先清空旧模型
    - 清理数据源关联的所有数据模型

    重要提示：
    - 删除操作不可逆，请谨慎使用
    - 删除数据模型时，会同时删除关联的工作空间关系
    - 该操作会删除该数据源下的所有数据模型，请确认后再执行

    Args:
        ds_id_or_code: 数据源标识符（必填）.
            如果为数字字符串，视为数据源ID;否则视为数据源编码(code).
            示例:"1"（数据源ID）、"mysql01"（数据源编码）.

    Returns:
        str: 删除结果
            - 成功时：返回 "已删除数据源 {ds_id_or_code} 下的 {count} 个数据模型"
            - 如果没有数据模型：返回 "数据源 {ds_id_or_code} 下没有数据模型"
            - 失败时：返回错误原因
            - 常见错误：
              * "数据源不存在：{ds_id_or_code}" - 数据源不存在
              * "删除数据模型失败：{错误信息}" - 删除失败

    Example:
        删除数据源下的所有数据模型（使用ID）:
        tool_delete_data_models_by_data_source(ds_id_or_code="1")

        删除数据源下的所有数据模型（使用编码）:
        tool_delete_data_models_by_data_source(ds_id_or_code="mysql01")

    Note:
        - ds_id_or_code 必须是已存在的数据源ID或编码
        - 删除操作不可逆，请确认后再执行
        - 删除操作会同时删除所有关联的工作空间关系
        - 如果数据源下没有数据模型，会返回提示信息，不会报错
    """
    logger.info(
        f"[TOOL-CALL] tool_delete_data_models_by_data_source - {format_tool_params(ds_id_or_code=ds_id_or_code)}"
    )
    db = SessionLocal()
    try:
        # 根据ID或编码查找数据源
        data_source = get_data_source(db, ds_id_or_code)

        if not data_source:
            error_msg = f"数据源不存在：{ds_id_or_code}"
            logger.error(
                f"[TOOL-RESULT] tool_delete_data_models_by_data_source - 失败：{error_msg}"
            )
            return error_msg

        ds_id = data_source.id

        # 查询该数据源下的所有数据模型
        related_models = db.query(TbDataModel).filter(TbDataModel.ds_id == ds_id).all()
        model_count = len(related_models)

        if model_count == 0:
            success_msg = f"数据源 {ds_id_or_code} (ID: {ds_id}) 下没有数据模型"
            logger.info(f"[TOOL-RESULT] tool_delete_data_models_by_data_source - {success_msg}")
            return success_msg

        # 删除所有关联的数据模型(delete_data_model 会自动删除工作空间关系)
        deleted_count = 0
        failed_count = 0
        for model in related_models:
            try:
                # 删除数据模型（会自动删除关联的工作空间关系）
                DataModelService.delete_data_model(db=db, data_model_id=model.id)
                deleted_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(
                    f"[TOOL-RESULT] tool_delete_data_models_by_data_source - 删除数据模型失败：ID={model.id}, 错误：{e!s}",
                    exc_info=True,
                )

        if failed_count > 0:
            error_msg = f"删除数据源 {ds_id_or_code} (ID: {ds_id}) 下的数据模型时发生错误：成功删除 {deleted_count} 个，失败 {failed_count} 个"
            logger.error(
                f"[TOOL-RESULT] tool_delete_data_models_by_data_source - 部分失败：{error_msg}"
            )
            return error_msg

        success_msg = f"已删除数据源 {ds_id_or_code} (ID: {ds_id}) 下的 {deleted_count} 个数据模型"
        logger.info(f"[TOOL-RESULT] tool_delete_data_models_by_data_source - 成功：{success_msg}")
        return success_msg

    except Exception as e:
        error_msg = f"处理数据源数据模型删除时发生错误：{e!s}"
        logger.error(
            f"[TOOL-RESULT] tool_delete_data_models_by_data_source - 失败：{error_msg}",
            exc_info=True,
        )
        return error_msg
    finally:
        db.close()


@tool
def tool_list_data_models_by_data_source(ds_id_or_code: str) -> str:
    """
    查询指定数据源下的所有数据模型信息（简化信息）

    该工具用于查询指定数据源下的所有数据模型，返回模型的简化信息，包括：
    - id：数据模型ID
    - code：数据模型编码
    - name：数据模型名称
    - has_semantic：是否已有语义说明（semantic字段不为空）
    - has_summary：是否已有总结说明（summary字段不为空）

    使用场景：
    - 查看数据源下有哪些数据模型
    - 检查数据模型的语义说明和总结说明是否已生成
    - 批量查看数据模型的基本信息

    Args:
        ds_id_or_code: 数据源标识符（必填）
            - 如果为数字字符串，视为数据源ID
            - 否则视为数据源编码(code)
            - 示例：
              * "1" - 数据源ID
              * "mysql01" - 数据源编码

    Returns:
        str: 数据模型列表信息，JSON格式
            - 格式示例：
              ```json
              [
                {
                  "id": 1,
                  "code": "public.users",
                  "name": "users",
                  "has_semantic": true,
                  "has_summary": true
                },
                {
                  "id": 2,
                  "code": "public.orders",
                  "name": "orders",
                  "has_semantic": false,
                  "has_summary": false
                }
              ]
              ```
            - 如果数据源不存在，返回错误信息
            - 如果数据源下没有数据模型，返回空数组 []

    Example:
        查询数据源下的所有模型（使用ID）:
        tool_list_data_models_by_data_source(ds_id_or_code="1")

        查询数据源下的所有模型（使用编码）:
        tool_list_data_models_by_data_source(ds_id_or_code="mysql01")

    Note:
        - 只返回简化信息，不包含完整的模型详情
        - 如需获取完整模型信息，请使用 tool_get_data_model
    """
    logger.info(
        f"[TOOL-CALL] tool_list_data_models_by_data_source - {format_tool_params(ds_id_or_code=ds_id_or_code)}"
    )
    db = SessionLocal()
    try:
        # 根据ID或编码查找数据源
        data_source = get_data_source(db, ds_id_or_code)

        if not data_source:
            error_msg = f"数据源不存在：{ds_id_or_code}"
            logger.error(f"[TOOL-RESULT] tool_list_data_models_by_data_source - 失败：{error_msg}")
            return error_msg

        ds_id = data_source.id

        # 查询该数据源下的所有数据模型
        data_models = db.query(TbDataModel).filter(TbDataModel.ds_id == ds_id).all()

        # 构建结果列表
        result_list = []
        for model in data_models:
            model_info = {
                "id": model.id,
                "code": model.code,
                "name": model.name,
                "has_semantic": bool(model.semantic),
                "has_summary": bool(model.summary),
            }
            result_list.append(model_info)

        result_json = json_dumps(result_list, ensure_ascii=False, indent=2)

        logger.info(
            f"[TOOL-RESULT] tool_list_data_models_by_data_source - 成功：返回 {len(result_list)} 个模型信息"
        )
        return result_json

    except Exception as e:
        error_msg = f"查询数据源下的数据模型时发生错误：{e!s}"
        logger.exception("[TOOL-RESULT] tool_list_data_models_by_data_source - 失败")
        return error_msg
    finally:
        db.close()


@tool
def tool_get_data_models_semantic(model_ids: str) -> str:
    """
    批量获取指定数据模型的语义信息(semantic)

    该工具用于批量获取指定数据模型的完整语义信息(semantic)，用于SQL生成阶段。
    semantic包含详细的字段结构、数据类型、业务含义等信息，用于生成准确的SQL查询。

    使用场景：
    - 在文本转SQL场景中，获取选中模型的详细语义信息
    - 批量获取多个模型的完整信息用于SQL生成
    - 模型详细信息的批量检索

    Args:
        model_ids: 数据模型ID列表，逗号分隔的字符串
            示例："1,2,3" 或 "1,2"

    Returns:
        str: 指定数据模型的语义信息，JSON格式
            - 格式示例：
              ```json
              [
                {
                  "id": 1,
                  "code": "public.users",
                  "name": "users",
                  "platform": "postgresql",
                  "type": "table",
                  "ds_id": 1,
                  "ds_code": "postgresql01",
                  "semantic": "详细的语义说明，包含字段结构、数据类型等"
                },
                {
                  "id": 2,
                  "code": "public.orders",
                  "name": "orders",
                  "platform": "postgresql",
                  "type": "table",
                  "ds_id": 1,
                  "ds_code": "postgresql01",
                  "semantic": "详细的语义说明，包含字段结构、数据类型等"
                }
              ]
              ```
            - 如果某个模型不存在或semantic为空，则跳过该模型或返回空semantic
            - 只返回ds_id不为空且semantic不为空的模型

    Example:
        获取指定模型的语义信息：
        tool_get_data_models_semantic(model_ids="1,2,3")
    """
    logger.info(
        f"[TOOL-CALL] tool_get_data_models_semantic - {format_tool_params(model_ids=model_ids)}"
    )
    db = SessionLocal()
    try:
        # 解析模型ID列表
        try:
            id_list = [int(id_str.strip()) for id_str in model_ids.split(",") if id_str.strip()]
        except ValueError:
            error_msg = f"模型ID格式错误：{model_ids}，应为逗号分隔的数字，如：1,2,3"
            logger.exception(f"[TOOL-RESULT] tool_get_data_models_semantic - 失败：{error_msg}")
            return error_msg

        if not id_list:
            error_msg = "模型ID列表为空"
            logger.error(f"[TOOL-RESULT] tool_get_data_models_semantic - 失败：{error_msg}")
            return error_msg

        # 批量获取数据模型
        data_models = db.query(TbDataModel).filter(TbDataModel.id.in_(id_list)).all()

        # 构建结果列表
        result_list = []
        for model in data_models:
            # 只处理ds_id不为空且semantic不为空的模型
            if not model.ds_id or not model.semantic:
                continue

            # 获取数据源信息
            data_source = get_data_source(db=db, ds_id_or_code=str(model.ds_id))
            if not data_source:
                continue

            model_info = {
                "id": model.id,
                "code": model.code,
                "name": model.name,
                "platform": model.platform,
                "type": model.type,
                "ds_id": model.ds_id,
                "ds_code": data_source.code,  # 数据源编码
                "semantic": model.semantic,
            }

            result_list.append(model_info)

        result_json = json_dumps(result_list, ensure_ascii=False, indent=2)

        logger.info(
            f"[TOOL-RESULT] tool_get_data_models_semantic - 成功：返回 {len(result_list)} 个模型的语义信息"
        )
        return result_json

    except Exception as e:
        error_msg = f"获取数据模型语义信息时发生错误：{e!s}"
        logger.exception("[TOOL-RESULT] tool_get_data_models_semantic - 失败")
        return error_msg
    finally:
        db.close()


@tool
def tool_execute_sql_data_model(dm_id_or_code: str, sql: str) -> str:
    """
    在指定数据模型所属的数据源上执行SQL查询

    该工具用于在数据模型所属的数据源上执行SQL查询语句，并返回查询结果。通过数据模型编码(code)或数据模型ID来指定数据模型，然后找到该模型关联的数据源，并在该数据源上执行SQL.

    使用场景：
    - 查询数据模型对应的数据源中的数据
    - 执行针对特定数据模型的数据分析SQL语句
    - 验证数据模型对应的数据内容
    - 执行统计查询、聚合查询等

    重要提示：
    - 该工具只支持SELECT查询语句，不支持INSERT、UPDATE、DELETE等修改数据的操作
    - SQL语句应该经过验证，避免SQL注入攻击
    - 查询结果会自动处理特殊字段类型（时间类型、BLOB类型、DECIMAL等）
    - 如果数据模型的ds_id为空或数据源不存在，会返回相应的错误信息

    Args:
        dm_id_or_code: 数据模型标识符，可以是数据模型编码(code)或数据模型ID（字符串格式的数字）.
            如果以数字开头且全为数字，则视为数据模型ID;否则视为数据模型编码(code).
            示例:"public.users"（数据模型编码）、"1"（数据模型ID）、"123"（数据模型ID）.

        sql: 要执行的SQL查询语句。
            必须是SELECT查询语句，支持参数化查询（根据数据库类型使用不同的占位符）.
            示例:"SELECT * FROM users LIMIT 10"、"SELECT COUNT(*) as total FROM orders WHERE status = 'completed'"、
            "SELECT id, name, created_at FROM products ORDER BY created_at DESC".

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
              * 时间类型(datetime, date):转换为ISO格式字符串（如:"2023-01-01T12:00:00"）
              * BLOB类型(bytes):转换为base64编码字符串，格式为"<BLOB:base64:...>"
              * DECIMAL类型：转换为float类型
              * NULL值：保持为null

    Example:
        通过数据模型编码执行查询：
        tool_execute_sql_data_model(
            dm_id_or_code="public.users",
            sql="SELECT * FROM users LIMIT 10"
        )

        通过数据模型ID执行查询：
        tool_execute_sql_data_model(
            dm_id_or_code="1",
            sql="SELECT COUNT(*) as total FROM orders WHERE status = 'completed'"
        )

        执行带条件的查询：
        tool_execute_sql_data_model(
            dm_id_or_code="public.products",
            sql="SELECT id, name, created_at FROM products WHERE price > 100 ORDER BY created_at DESC"
        )

    Note:
        - 只支持SELECT查询，不支持数据修改操作
        - 查询结果会自动处理特殊字段类型，确保可以正确序列化为JSON
        - 如果数据模型不存在、ds_id为空或数据源不存在，会返回相应的错误信息
        - 如果SQL语句执行失败，会返回详细的错误信息
    """
    logger.info(
        f"[TOOL-CALL] tool_execute_sql_data_model - {format_tool_params(dm_id_or_code=dm_id_or_code, sql=sql[:LOG_MESSAGE_TRUNCATE_LENGTH] + '...' if len(sql) > LOG_MESSAGE_TRUNCATE_LENGTH else sql)}"
    )
    db = SessionLocal()
    try:
        data_model = get_data_model(db=db, dm_id_or_code=dm_id_or_code)

        if not data_model:
            error_msg = f"数据模型不存在：{dm_id_or_code}"
            logger.error(f"[TOOL-RESULT] tool_execute_sql_data_model - 失败：{error_msg}")
            return error_msg

        # 检查数据模型的ds_id是否存在
        if not data_model.ds_id:
            error_msg = f"数据模型的ds_id为空：{dm_id_or_code}"
            logger.error(f"[TOOL-RESULT] tool_execute_sql_data_model - 失败：{error_msg}")
            return error_msg

        # 获取数据源配置
        data_source = get_data_source(db=db, ds_id_or_code=str(data_model.ds_id))

        if not data_source:
            error_msg = f"数据源不存在：ds_id={data_model.ds_id}"
            logger.error(f"[TOOL-RESULT] tool_execute_sql_data_model - 失败：{error_msg}")
            return error_msg

        setting = json.loads(data_source.setting)

        platform = data_source.platform
        host = setting.get("host")
        port = setting.get("port")
        username = setting.get("username")
        password = setting.get("password")
        database = setting.get("database")
        # 执行SQL查询
        connector = None
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
            logger.debug(
                f"[TOOL-INTERNAL] tool_execute_sql_data_model - 执行SQL查询：{sql[:LOG_MESSAGE_TRUNCATE_LENGTH]}..."
            )  # 只记录前100个字符

            # 执行查询（连接器的execute_query已经处理了特殊类型）
            results = connector.execute_query(sql)

            # 规范化查询结果（处理特殊类型）
            normalized_results = normalize_query_results(results)

            # 转换为JSON字符串
            result_json = json_dumps(normalized_results, ensure_ascii=False, indent=2)

            logger.info(
                f"[TOOL-RESULT] tool_execute_sql_data_model - 成功：返回 {len(results)} 条记录"
            )
            return result_json

        except Exception as e:
            error_msg = f"执行SQL查询时发生错误：{e!s}"
            logger.error(
                f"[TOOL-RESULT] tool_execute_sql_data_model - 失败：{error_msg}", exc_info=True
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
            f"[TOOL-RESULT] tool_execute_sql_data_model - 失败：{error_msg}", exc_info=True
        )
        return error_msg
    finally:
        db.close()
