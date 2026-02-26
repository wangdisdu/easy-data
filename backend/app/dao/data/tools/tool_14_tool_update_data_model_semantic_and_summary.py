"""工具初始化数据: tool_update_data_model_semantic_and_summary"""

DESCRIPTION = """同时更新数据模型的语义说明(semantic)和摘要说明(summary)字段

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

CONTENT = """def tool_update_data_model_semantic_and_summary(
    dm_id_or_code: str, semantic: str, summary: str
) -> str:
    import json
    from app.dao.database import SessionLocal
    from app.dao.models import TbDataModel
    from app.services.data_models_service import DataModelService
    from app.services.data_models_service import DataModelUpdate
    db = SessionLocal()
    try:
        if dm_id_or_code.isdigit():
            data_model = db.query(TbDataModel).filter(TbDataModel.id == int(dm_id_or_code)).first()
        else:
            data_model = db.query(TbDataModel).filter(TbDataModel.code == dm_id_or_code).first()

        if not data_model:
            error_msg = f"数据模型不存在：{dm_id_or_code}"
            return error_msg

        # 同时更新 semantic 和 summary 字段
        data_model_update = DataModelUpdate(semantic=semantic, summary=summary)

        DataModelService.update_data_model(
            db=db,
            data_model_id=data_model.id,
            data_model_update=data_model_update,
            update_user_id=1,
        )

        success_msg = f"数据模型语义说明和摘要说明更新成功：{dm_id_or_code} (ID: {data_model.id})"
        return success_msg

    except Exception as e:
        error_msg = f"更新数据模型语义说明和摘要说明失败：{e!s}"
        return error_msg
    finally:
        db.close()
"""

ROW = {
    "tool": "tool_update_data_model_semantic_and_summary",
    "description": DESCRIPTION,
    "parameters": "",
    "content": CONTENT,
    "extend": "",
    "id": 14,
}
