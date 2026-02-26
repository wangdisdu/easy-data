"""工具初始化数据: tool_check_models_semantic"""

DESCRIPTION = """检查指定数据源下的模型是否已经生成了语义说明

该工具用于检查指定数据源下的所有模型是否已经生成了语义说明（semantic字段不为空）。

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
            "models_with_semantic": 3,
            "models_without_semantic": 2,
            "without_semantic_list": [
              {
                "code": "public.users",
                "name": "users",
                "type": "table"
              }
            ]
          }
          ```
"""

CONTENT = """def tool_check_models_semantic(ds_id_or_code: str) -> str:
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

        if len(models) == 0:
            result = {
                "ds_id": data_source.id,
                "ds_code": data_source.code,
                "total_models": 0,
                "models_with_semantic": 0,
                "models_without_semantic": 0,
                "without_semantic_list": [],
                "message": "数据源下没有模型",
            }
            result_json = json.dumps(result, ensure_ascii=False, indent=2)
            return result_json

        without_semantic_list = []
        for model in models:
            if not model.semantic:
                without_semantic_list.append(
                    {"code": model.code, "name": model.name, "type": model.type}
                )

        with_semantic_count = len(models) - len(without_semantic_list)

        result = {
            "ds_id": data_source.id,
            "ds_code": data_source.code,
            "total_models": len(models),
            "models_with_semantic": with_semantic_count,
            "models_without_semantic": len(without_semantic_list),
            "without_semantic_list": without_semantic_list,
        }

        result_json = json.dumps(result, ensure_ascii=False, indent=2)
        return result_json

    except Exception as e:
        error_msg = f"检查模型语义说明时发生错误：{e!s}"
        return error_msg
    finally:
        db.close()
"""

ROW = {
    "tool": "tool_check_models_semantic",
    "description": DESCRIPTION,
    "parameters": "",
    "content": CONTENT,
    "extend": "",
    "id": 21,
}
