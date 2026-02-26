"""工具初始化数据: tool_get_data_model"""

DESCRIPTION = """获取指定数据模型的详细信息

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
        "semantic": "{\"type\": \"table\"}",
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

CONTENT = """def tool_get_data_model(dm_id_or_code: str) -> str:
    import json
    from app.dao.database import SessionLocal
    from app.dao.models import TbDataModel
    db = SessionLocal()
    try:
        if dm_id_or_code.isdigit():
            data_model = db.query(TbDataModel).filter(TbDataModel.id == int(dm_id_or_code)).first()
        else:
            data_model = db.query(TbDataModel).filter(TbDataModel.code == dm_id_or_code).first()

        if not data_model:
            error_msg = f"数据模型不存在：{dm_id_or_code}"
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

        result_json = json.dumps(result)
        return result_json

    except Exception as e:
        error_msg = f"获取数据模型信息时发生错误：{e!s}"
        return error_msg
    finally:
        db.close()
"""

ROW = {
    "tool": "tool_get_data_model",
    "description": DESCRIPTION,
    "parameters": "",
    "content": CONTENT,
    "extend": "",
    "id": 12,
}
