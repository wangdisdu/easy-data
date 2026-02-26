"""工具初始化数据: tool_list_data_models_by_data_source"""

DESCRIPTION = """查询指定数据源下的所有数据模型信息（简化信息）

该工具用于查询指定数据源下的所有数据模型，返回模型的简化信息，包括：
- id：数据模型ID
- code：数据模型编码
- name：数据模型名称
- has_semantic：是否已有语义说明（semantic字段不为空）
- has_summary：是否已有总结说明（summary字段不为空）

使用场景：
- 查看数据源下有哪些数据模型
- 检查数据模型的语义说明和总结说明是否已生成
- 批量查看数据模型的基本信息

Args:
    ds_id_or_code: 数据源标识符（必填）
        - 如果为数字字符串，视为数据源ID
        - 否则视为数据源编码(code)
        - 示例：
          * "1" - 数据源ID
          * "mysql01" - 数据源编码

Returns:
    str: 数据模型列表信息，JSON格式
        - 格式示例：
          ```json
          [
            {
              "id": 1,
              "code": "public.users",
              "name": "users",
              "has_semantic": true,
              "has_summary": true
            },
            {
              "id": 2,
              "code": "public.orders",
              "name": "orders",
              "has_semantic": false,
              "has_summary": false
            }
          ]
          ```
        - 如果数据源不存在，返回错误信息
        - 如果数据源下没有数据模型，返回空数组 []

Example:
    查询数据源下的所有模型（使用ID）:
    tool_list_data_models_by_data_source(ds_id_or_code="1")

    查询数据源下的所有模型（使用编码）:
    tool_list_data_models_by_data_source(ds_id_or_code="mysql01")

Note:
    - 只返回简化信息，不包含完整的模型详情
    - 如需获取完整模型信息，请使用 tool_get_data_model
"""

CONTENT = """def tool_list_data_models_by_data_source(ds_id_or_code: str) -> str:
    import json
    from app.dao.database import SessionLocal
    from app.dao.models import TbDataSource
    from app.dao.models import TbDataModel
    db = SessionLocal()
    try:
        if ds_id_or_code.isdigit():
            data_source = db.query(TbDataSource).filter(TbDataSource.id == int(ds_id_or_code)).first()
        else:
            data_source = db.query(TbDataSource).filter(TbDataSource.code == ds_id_or_code).first()

        if not data_source:
            error_msg = f"数据源不存在：{ds_id_or_code}"
            return error_msg

        ds_id = data_source.id

        # 查询该数据源下的所有数据模型
        data_models = db.query(TbDataModel).filter(TbDataModel.ds_id == ds_id).all()

        # 构建结果列表
        result_list = []
        for model in data_models:
            model_info = {
                "id": model.id,
                "code": model.code,
                "name": model.name,
                "has_semantic": bool(model.semantic),
                "has_summary": bool(model.summary),
            }
            result_list.append(model_info)

        result_json = json.dumps(result_list)
        return result_json

    except Exception as e:
        error_msg = f"查询数据源下的数据模型时发生错误：{e!s}"
        return error_msg
    finally:
        db.close()
"""

ROW = {
    "tool": "tool_list_data_models_by_data_source",
    "description": DESCRIPTION,
    "parameters": "",
    "content": CONTENT,
    "extend": "",
    "id": 9,
}
