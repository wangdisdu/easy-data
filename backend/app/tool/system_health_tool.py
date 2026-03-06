"""
系统健康检查相关工具
"""

import contextlib
import json

from langchain.tools import tool

from app.connector.factory import ConnectorFactory
from app.core.json_utils import json_dumps
from app.core.logging import get_logger
from app.dao.database import SessionLocal
from app.dao.models import TbDataModel, TbDataSource
from app.tool.tool_utils import format_tool_params

logger = get_logger("system_health_tool")


def _check_data_source_fields(data_source: TbDataSource) -> list[str]:
    """
    检查单个数据源的基础信息字段

    Args:
        data_source: 数据源对象

    Returns:
        缺失的字段列表
    """
    missing_fields = []
    if not data_source.code:
        missing_fields.append("code")
    if not data_source.name:
        missing_fields.append("name")
    if not data_source.platform:
        missing_fields.append("platform")
    if not data_source.setting:
        missing_fields.append("setting")
    else:
        try:
            setting_dict = json.loads(data_source.setting)
            required_fields = ["host", "port", "username", "password", "database"]
            for field in required_fields:
                if field not in setting_dict or not setting_dict[field]:
                    missing_fields.append(f"setting.{field}")
        except json.JSONDecodeError:
            missing_fields.append("setting（JSON格式错误）")
    return missing_fields


@tool
def tool_check_data_sources_basic_info() -> str:
    """
    检查系统内所有数据源的基础信息是否完整

    该工具用于检查系统中所有数据源的基础信息（code、name、platform、setting等）是否完整。
    基础信息不能缺少，包括：
    - code：数据源编码
    - name：数据源名称
    - platform：数据库类型
    - setting：连接配置（JSON格式，包含host、port、username、password、database）

    Returns:
        str: 检查结果，JSON格式
            - 格式示例：
              ```json
              {
                "status": "pass|warning",
                "message": "检查结果描述",
                "total_count": 5,
                "complete_count": 4,
                "incomplete_count": 1,
                "incomplete_list": [
                  {
                    "ds_id": 1,
                    "ds_code": "mysql01",
                    "missing_fields": ["setting.host", "setting.port"]
                  }
                ]
              }
              ```
    """
    logger.info("[TOOL-CALL] tool_check_data_sources_basic_info")
    db = SessionLocal()
    try:
        data_sources = db.query(TbDataSource).all()

        if len(data_sources) == 0:
            result = {
                "status": "warning",
                "message": "系统内没有创建任何数据源",
                "total_count": 0,
                "complete_count": 0,
                "incomplete_count": 0,
                "incomplete_list": [],
            }
            result_json = json_dumps(result, ensure_ascii=False, indent=2)
            logger.info("[TOOL-RESULT] tool_check_data_sources_basic_info - 完成")
            return result_json

        incomplete_list = []
        for ds in data_sources:
            missing_fields = _check_data_source_fields(ds)
            if missing_fields:
                incomplete_list.append(
                    {
                        "ds_id": ds.id,
                        "ds_code": ds.code,
                        "ds_name": ds.name,
                        "missing_fields": missing_fields,
                    }
                )

        complete_count = len(data_sources) - len(incomplete_list)

        if len(incomplete_list) == 0:
            result = {
                "status": "pass",
                "message": f"所有 {len(data_sources)} 个数据源的基础信息完整",
                "total_count": len(data_sources),
                "complete_count": complete_count,
                "incomplete_count": len(incomplete_list),
                "incomplete_list": [],
            }
        else:
            result = {
                "status": "warning",
                "message": f"{len(incomplete_list)} 个数据源缺少基础信息",
                "total_count": len(data_sources),
                "complete_count": complete_count,
                "incomplete_count": len(incomplete_list),
                "incomplete_list": incomplete_list,
            }

        result_json = json_dumps(result, ensure_ascii=False, indent=2)
        logger.info(
            f"[TOOL-RESULT] tool_check_data_sources_basic_info - 完成：{len(incomplete_list)} 个不完整"
        )
        return result_json

    except Exception as e:
        error_msg = f"检查数据源基础信息时发生错误：{e!s}"
        logger.exception("[TOOL-RESULT] tool_check_data_sources_basic_info - 失败")
        return error_msg
    finally:
        db.close()


@tool
def tool_check_data_source_connection(ds_id_or_code: str) -> str:
    """
    检查指定数据源的连接是否正常

    该工具用于测试指定数据源的连接是否可用。

    Args:
        ds_id_or_code: 数据源标识符（必填）
            - 如果为数字字符串，视为数据源ID
            - 否则视为数据源编码(code)
            - 示例："1"（数据源ID）、"mysql01"（数据源编码）

    Returns:
        str: 检查结果，JSON格式
            - 格式示例：
              ```json
              {
                "ds_id": 1,
                "ds_code": "mysql01",
                "status": "success|failed|error",
                "message": "连接测试结果描述"
              }
              ```
    """
    logger.info(
        f"[TOOL-CALL] tool_check_data_source_connection - {format_tool_params(ds_id_or_code=ds_id_or_code)}"
    )
    db = SessionLocal()
    try:
        # 根据ID或编码查找数据源
        if ds_id_or_code.isdigit():
            ds_id = int(ds_id_or_code)
            data_source = db.query(TbDataSource).filter(TbDataSource.id == ds_id).first()
        else:
            data_source = db.query(TbDataSource).filter(TbDataSource.code == ds_id_or_code).first()

        if not data_source:
            error_msg = f"数据源不存在：{ds_id_or_code}"
            logger.error(f"[TOOL-RESULT] tool_check_data_source_connection - 失败：{error_msg}")
            return error_msg

        try:
            setting = json.loads(data_source.setting)
            connector = ConnectorFactory.create_connector(
                data_source.platform,
                host=setting.get("host", ""),
                port=setting.get("port", 0),
                username=setting.get("username", ""),
                password=setting.get("password", ""),
                database=setting.get("database", ""),
            )
            test_result = connector.test_connection()
            connector.close()

            if test_result.success:
                result = {
                    "ds_id": data_source.id,
                    "ds_code": data_source.code,
                    "status": "success",
                    "message": test_result.message,
                }
            else:
                result = {
                    "ds_id": data_source.id,
                    "ds_code": data_source.code,
                    "status": "failed",
                    "message": test_result.message,
                }
        except Exception as e:
            result = {
                "ds_id": data_source.id,
                "ds_code": data_source.code,
                "status": "error",
                "message": str(e),
            }

        result_json = json_dumps(result, ensure_ascii=False, indent=2)
        logger.info(f"[TOOL-RESULT] tool_check_data_source_connection - 完成：{result['status']}")
        return result_json

    except Exception as e:
        error_msg = f"检查数据源连接时发生错误：{e!s}"
        logger.exception("[TOOL-RESULT] tool_check_data_source_connection - 失败")
        return error_msg
    finally:
        db.close()


@tool
def tool_check_models_exist_in_database(ds_id_or_code: str) -> str:
    """
    检查指定数据源下的模型是否在数据库的表/视图中存在

    该工具用于检查指定数据源下的所有模型是否在数据库的实际表/视图中存在。

    Args:
        ds_id_or_code: 数据源标识符（必填）
            - 如果为数字字符串，视为数据源ID
            - 否则视为数据源编码(code)
            - 示例："1"（数据源ID）、"mysql01"（数据源编码）

    Returns:
        str: 检查结果，JSON格式
            - 格式示例：
              ```json
              {
                "ds_id": 1,
                "ds_code": "mysql01",
                "total_models": 5,
                "existing_models": 4,
                "missing_models": 1,
                "missing_list": [
                  {
                    "code": "public.users",
                    "name": "users",
                    "type": "table"
                  }
                ]
              }
              ```
    """
    logger.info(
        f"[TOOL-CALL] tool_check_models_exist_in_database - {format_tool_params(ds_id_or_code=ds_id_or_code)}"
    )
    db = SessionLocal()
    connector = None
    try:
        # 根据ID或编码查找数据源
        if ds_id_or_code.isdigit():
            ds_id = int(ds_id_or_code)
            data_source = db.query(TbDataSource).filter(TbDataSource.id == ds_id).first()
        else:
            data_source = db.query(TbDataSource).filter(TbDataSource.code == ds_id_or_code).first()

        if not data_source:
            error_msg = f"数据源不存在：{ds_id_or_code}"
            logger.error(f"[TOOL-RESULT] tool_check_models_exist_in_database - 失败：{error_msg}")
            return error_msg

        # 查询该数据源下的所有数据模型
        models = db.query(TbDataModel).filter(TbDataModel.ds_id == data_source.id).all()

        if len(models) == 0:
            result = {
                "ds_id": data_source.id,
                "ds_code": data_source.code,
                "total_models": 0,
                "existing_models": 0,
                "missing_models": 0,
                "missing_list": [],
                "message": "数据源下没有模型",
            }
            result_json = json_dumps(result, ensure_ascii=False, indent=2)
            logger.info("[TOOL-RESULT] tool_check_models_exist_in_database - 完成：没有模型")
            return result_json

        # 连接数据库获取表和视图列表
        setting = json.loads(data_source.setting)
        connector = ConnectorFactory.create_connector(
            data_source.platform,
            host=setting.get("host", ""),
            port=setting.get("port", 0),
            username=setting.get("username", ""),
            password=setting.get("password", ""),
            database=setting.get("database", ""),
        )

        schema = setting.get("schema")
        db_tables = set(connector.get_tables(database=setting.get("database"), schema=schema))
        db_views = set(connector.get_views(database=setting.get("database"), schema=schema))
        db_all = db_tables | db_views

        connector.close()
        connector = None

        # 检查每个模型
        missing_list = []
        for model in models:
            model_name = model.name
            if model_name not in db_all:
                missing_list.append({"code": model.code, "name": model.name, "type": model.type})

        existing_count = len(models) - len(missing_list)

        result = {
            "ds_id": data_source.id,
            "ds_code": data_source.code,
            "total_models": len(models),
            "existing_models": existing_count,
            "missing_models": len(missing_list),
            "missing_list": missing_list,
        }

        result_json = json_dumps(result, ensure_ascii=False, indent=2)
        logger.info(
            f"[TOOL-RESULT] tool_check_models_exist_in_database - 完成：{existing_count} 个存在，{len(missing_list)} 个缺失"
        )
        return result_json

    except Exception as e:
        error_msg = f"检查模型是否存在时发生错误：{e!s}"
        logger.exception("[TOOL-RESULT] tool_check_models_exist_in_database - 失败")
        return error_msg
    finally:
        if connector:
            with contextlib.suppress(Exception):
                connector.close()
        db.close()
