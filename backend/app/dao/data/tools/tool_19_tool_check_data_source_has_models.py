"""工具初始化数据: tool_check_data_source_has_models"""

DESCRIPTION = """检查指定数据源下是否有模型

该工具用于检查指定数据源下是否已经创建了数据模型。

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
            "has_models": true,
            "model_count": 5,
            "message": "数据源下有5个模型"
          }
          ```
"""

CONTENT = """def tool_check_data_source_has_models(ds_id_or_code: str) -> str:
    import json
    from app.dao.database import SessionLocal
    from app.dao.models import TbDataModel, TbDataSource

    db = SessionLocal()
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
        model_count = len(models)

        result = {
            "ds_id": data_source.id,
            "ds_code": data_source.code,
            "has_models": model_count > 0,
            "model_count": model_count,
            "message": (
                f"数据源下有 {model_count} 个模型" if model_count > 0 else "数据源下没有模型"
            ),
        }

        result_json = json.dumps(result, ensure_ascii=False, indent=2)
        return result_json

    except Exception as e:
        error_msg = f"检查数据源模型时发生错误：{e!s}"
        return error_msg
    finally:
        db.close()
"""

ROW = {
    "tool": "tool_check_data_source_has_models",
    "description": DESCRIPTION,
    "parameters": "",
    "content": CONTENT,
    "extend": "",
    "id": 19,
}
