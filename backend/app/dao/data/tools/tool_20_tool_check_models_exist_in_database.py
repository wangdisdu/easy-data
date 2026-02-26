"""工具初始化数据: tool_check_models_exist_in_database"""

DESCRIPTION = """检查指定数据源下的模型是否在数据库的表/视图中存在

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

CONTENT = """def tool_check_models_exist_in_database(ds_id_or_code: str) -> str:
    import contextlib
    import json
    from app.connector.factory import ConnectorFactory
    from app.dao.database import SessionLocal
    from app.dao.models import TbDataModel, TbDataSource

    db = SessionLocal()
    connector = None
    try:
        if ds_id_or_code.isdigit():
            ds_id = int(ds_id_or_code)
            data_source = db.query(TbDataSource).filter(TbDataSource.id == ds_id).first()
        else:
            data_source = db.query(TbDataSource).filter(TbDataSource.code == ds_id_or_code).first()

        if not data_source:
            error_msg = f"数据源不存在：{ds_id_or_code}"
            return error_msg

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
            result_json = json.dumps(result, ensure_ascii=False, indent=2)
            return result_json

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

        result_json = json.dumps(result, ensure_ascii=False, indent=2)
        return result_json

    except Exception as e:
        error_msg = f"检查模型是否存在时发生错误：{e!s}"
        return error_msg
    finally:
        if connector:
            with contextlib.suppress(Exception):
                connector.close()
        db.close()
"""

ROW = {
    "tool": "tool_check_models_exist_in_database",
    "description": DESCRIPTION,
    "parameters": "",
    "content": CONTENT,
    "extend": "",
    "id": 20,
}
