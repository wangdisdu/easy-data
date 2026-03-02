"""工具初始化数据: tool_delete_data_models_by_data_source"""

DESCRIPTION = """删除指定数据源下的所有数据模型

该工具用于删除指定数据源下的所有数据模型。支持通过数据源ID或编码(code)来指定数据源。

使用场景：
- 清空数据源下的所有数据模型
- 重新导入数据源的数据模型前，先清空旧模型
- 清理数据源关联的所有数据模型

重要提示：
- 删除操作不可逆，请谨慎使用
- 删除数据模型时，会同时删除关联的工作空间关系
- 该操作会删除该数据源下的所有数据模型，请确认后再执行

Args:
    ds_id_or_code: 数据源标识符（必填）.
        如果为数字字符串，视为数据源ID;否则视为数据源编码(code).
        示例:"1"（数据源ID）、"mysql01"（数据源编码）.

Returns:
    str: 删除结果
        - 成功时：返回 "已删除数据源 {ds_id_or_code} 下的 {count} 个数据模型"
        - 如果没有数据模型：返回 "数据源 {ds_id_or_code} 下没有数据模型"
        - 失败时：返回错误原因
        - 常见错误：
          * "数据源不存在：{ds_id_or_code}" - 数据源不存在
          * "删除数据模型失败：{错误信息}" - 删除失败

Example:
    删除数据源下的所有数据模型（使用ID）:
    tool_delete_data_models_by_data_source(ds_id_or_code="1")

    删除数据源下的所有数据模型（使用编码）:
    tool_delete_data_models_by_data_source(ds_id_or_code="mysql01")

Note:
    - ds_id_or_code 必须是已存在的数据源ID或编码
    - 删除操作不可逆，请确认后再执行
    - 删除操作会同时删除所有关联的工作空间关系
    - 如果数据源下没有数据模型，会返回提示信息，不会报错
"""

CONTENT = """def tool_delete_data_models_by_data_source(ds_id_or_code: str) -> str:
    from app.dao.database import SessionLocal
    from app.dao.models import TbDataSource
    from app.dao.models import TbDataModel
    from app.service.data_model_service import DataModelService
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
        related_models = db.query(TbDataModel).filter(TbDataModel.ds_id == ds_id).all()
        model_count = len(related_models)

        if model_count == 0:
            success_msg = f"数据源 {ds_id_or_code} (ID: {ds_id}) 下没有数据模型"
            return success_msg

        # 删除所有关联的数据模型(delete_data_model 会自动删除工作空间关系)
        deleted_count = 0
        failed_count = 0
        for model in related_models:
            try:
                # 删除数据模型（会自动删除关联的工作空间关系）
                DataModelService.delete_data_model(db=db, data_model_id=model.id)
                deleted_count += 1
            except Exception as e:
                failed_count += 1

        if failed_count > 0:
            error_msg = f"删除数据源 {ds_id_or_code} (ID: {ds_id}) 下的数据模型时发生错误：成功删除 {deleted_count} 个，失败 {failed_count} 个"
            return error_msg

        success_msg = f"已删除数据源 {ds_id_or_code} (ID: {ds_id}) 下的 {deleted_count} 个数据模型"
        return success_msg

    except Exception as e:
        error_msg = f"处理数据源数据模型删除时发生错误：{e!s}"
        return error_msg
    finally:
        db.close()
"""

ROW = {
    "tool": "tool_delete_data_models_by_data_source",
    "description": DESCRIPTION,
    "parameters": "",
    "content": CONTENT,
    "extend": "",
    "id": 10,
}
