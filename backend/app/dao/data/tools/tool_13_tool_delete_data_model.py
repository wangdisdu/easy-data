"""工具初始化数据: tool_delete_data_model"""

DESCRIPTION = """删除数据模型

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

CONTENT = """def tool_delete_data_model(dm_id_or_code: str) -> str:
    import json
    from app.dao.database import SessionLocal
    from app.dao.models import TbDataModel
    from app.services.data_models_service import DataModelService
    db = SessionLocal()
    try:
        if dm_id_or_code.isdigit():
            data_model = db.query(TbDataModel).filter(TbDataModel.id == int(dm_id_or_code)).first()
        else:
            data_model = db.query(TbDataModel).filter(TbDataModel.code == dm_id_or_code).first()

        if not data_model:
            error_msg = f"数据模型不存在：{dm_id_or_code}"
            return error_msg

        dm_id = data_model.id

        # 删除数据模型
        DataModelService.delete_data_model(db=db, data_model_id=dm_id)

        success_msg = f"数据模型删除成功：{dm_id_or_code} (ID: {dm_id})"
        return success_msg
    except Exception as e:
        error_msg = f"处理数据模型删除时发生错误：{e!s}"
        return error_msg
    finally:
        db.close()
"""

ROW = {
    "tool": "tool_delete_data_model",
    "description": DESCRIPTION,
    "parameters": "",
    "content": CONTENT,
    "extend": "",
    "id": 13,
}
