"""工具初始化数据: tool_check_data_source_connection"""

DESCRIPTION = """检查指定数据源的连接是否正常

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

CONTENT = """def tool_check_data_source_connection(ds_id_or_code: str) -> str:
    import json
    from app.connector.factory import ConnectorFactory
    from app.dao.database import SessionLocal
    from app.dao.models import TbDataSource

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

        result_json = json.dumps(result, ensure_ascii=False, indent=2)
        return result_json

    except Exception as e:
        error_msg = f"检查数据源连接时发生错误：{e!s}"
        return error_msg
    finally:
        db.close()
"""

ROW = {
    "tool": "tool_check_data_source_connection",
    "description": DESCRIPTION,
    "parameters": "",
    "content": CONTENT,
    "extend": "",
    "id": 18,
}
