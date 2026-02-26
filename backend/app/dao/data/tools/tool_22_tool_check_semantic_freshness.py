"""工具初始化数据: tool_check_semantic_freshness"""

DESCRIPTION = """检查指定数据源下的模型的语义说明的更新时间是否太旧了

该工具用于检查指定数据源下的所有模型的语义说明是否过期（超过一周未更新）。
语义说明应该至少一周更新一次。

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
            "total_models_with_semantic": 5,
            "fresh_models": 3,
            "outdated_models": 2,
            "outdated_list": [
              {
                "code": "public.users",
                "name": "users",
                "type": "table",
                "last_update": 1234567890,
                "days_old": 10
              }
            ]
          }
          ```
"""

CONTENT = """def tool_check_semantic_freshness(ds_id_or_code: str) -> str:
    import json
    from datetime import datetime, timedelta

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

        models = (
            db.query(TbDataModel)
            .filter(TbDataModel.ds_id == data_source.id, TbDataModel.semantic.isnot(None))
            .all()
        )

        if len(models) == 0:
            result = {
                "ds_id": data_source.id,
                "ds_code": data_source.code,
                "total_models_with_semantic": 0,
                "fresh_models": 0,
                "outdated_models": 0,
                "outdated_list": [],
                "message": "数据源下没有有语义说明的模型",
            }
            result_json = json.dumps(result, ensure_ascii=False, indent=2)
            return result_json

        one_week_ago = datetime.now() - timedelta(days=7)
        one_week_ago_timestamp = int(one_week_ago.timestamp())

        outdated_list = []
        for model in models:
            if model.update_time and model.update_time < one_week_ago_timestamp:
                days_old = int((datetime.now().timestamp() - model.update_time) / 86400)
                outdated_list.append(
                    {
                        "code": model.code,
                        "name": model.name,
                        "type": model.type,
                        "last_update": model.update_time,
                        "days_old": days_old,
                    }
                )

        fresh_count = len(models) - len(outdated_list)

        result = {
            "ds_id": data_source.id,
            "ds_code": data_source.code,
            "total_models_with_semantic": len(models),
            "fresh_models": fresh_count,
            "outdated_models": len(outdated_list),
            "outdated_list": outdated_list,
        }

        result_json = json.dumps(result, ensure_ascii=False, indent=2)
        return result_json

    except Exception as e:
        error_msg = f"检查语义说明新鲜度时发生错误：{e!s}"
        return error_msg
    finally:
        db.close()
"""

ROW = {
    "tool": "tool_check_semantic_freshness",
    "description": DESCRIPTION,
    "parameters": "",
    "content": CONTENT,
    "extend": "",
    "id": 22,
}
