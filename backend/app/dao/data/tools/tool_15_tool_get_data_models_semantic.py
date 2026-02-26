"""工具初始化数据: tool_get_data_models_semantic"""

DESCRIPTION = """批量获取指定数据模型的语义信息(semantic)

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

CONTENT = """def tool_get_data_models_semantic(model_ids: str) -> str:
    import json
    from app.dao.database import SessionLocal
    from app.dao.models import TbDataModel
    from app.dao.models import TbDataSource
    from app.services.data_models_service import DataModelService
    from app.services.data_models_service import DataModelUpdate
    db = SessionLocal()
    try:
        # 解析模型ID列表
        try:
            id_list = [int(id_str.strip()) for id_str in model_ids.split(",") if id_str.strip()]
        except ValueError:
            error_msg = f"模型ID格式错误：{model_ids}，应为逗号分隔的数字，如：1,2,3"
            return error_msg

        if not id_list:
            error_msg = "模型ID列表为空"
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
            if ds_id_or_code.isdigit():
                data_source = db.query(TbDataSource).filter(TbDataSource.id == int(ds_id_or_code)).first()
            else:
                data_source = db.query(TbDataSource).filter(TbDataSource.code == ds_id_or_code).first()
            if not data_source:
                continue

            model_info = {
                "id": model.id,
                "code": model.code,
                "name": model.name,
                "platform": model.platform,
                "type": model.type,
                "ds_id": model.ds_id,
                "ds_code": data_source.code,
                "semantic": model.semantic,
            }

            result_list.append(model_info)

        result_json = json.dumps(result_list)
        return result_json

    except Exception as e:
        error_msg = f"获取数据模型语义信息时发生错误：{e!s}"
        return error_msg
    finally:
        db.close()
"""

ROW = {
    "tool": "tool_get_data_models_semantic",
    "description": DESCRIPTION,
    "parameters": "",
    "content": CONTENT,
    "extend": "",
    "id": 15,
}
