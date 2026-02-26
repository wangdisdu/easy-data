"""工具初始化数据: tool_delete_data_source"""

DESCRIPTION = """删除数据源（若存在关联数据模型则拒绝）

该工具用于删除指定的数据源。如果数据源下存在关联的数据模型（tb_data_model.ds_id = 数据源ID），将拒绝删除并提示先处理关联模型。

使用场景：
- 删除不再需要的数据源配置
- 清理无关联模型的数据源

重要提示：
- 当数据源下存在关联的数据模型时，会拒绝删除并返回提示
- 删除操作不可逆，请谨慎使用
- 删除操作会同时删除关联的工作空间关系

Args:
    ds_id_or_code: 数据源标识符（必填）。
        如果为数字字符串，视为数据源ID；否则视为数据源编码（code）。
        示例："1"（数据源ID）、"mysql01"（数据源编码）。

Returns:
    str: 删除结果
        - 成功时：返回 "数据源删除成功：ID={ds_id}"
        - 失败时：返回错误原因
        - 常见错误：
          * "数据源不存在：{ds_id_or_code}" - 数据源不存在
          * "数据源下存在 X 个关联的数据模型，无法删除，请先删除关联模型" - 存在关联模型
          * "删除数据源失败：{错误信息}" - 删除失败

Example:
    删除数据源（使用ID）:
    tool_delete_data_source(ds_id_or_code="1")

    删除数据源（使用编码）:
    tool_delete_data_source(ds_id_or_code="mysql01")

Note:
    - ds_id_or_code 必须是已存在的数据源ID或编码
    - 如果存在关联数据模型会直接拒绝删除，请先清理关联模型
"""

CONTENT = """def tool_delete_data_source(ds_id_or_code: str) -> str:
    import json
    from app.dao.database import SessionLocal
    from app.dao.models import TbDataModel
    from app.dao.models import TbDataSource
    from app.services.data_sources_service import DataSourceService
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

        # 检查是否存在关联数据模型，如果有则拒绝删除
        related_model_count = db.query(TbDataModel).filter(TbDataModel.ds_id == ds_id).count()
        if related_model_count > 0:
            error_msg = f"数据源下存在 {related_model_count} 个关联的数据模型，无法删除，请先删除关联模型"
            return error_msg

        # 删除数据源
        DataSourceService.delete_data_source(db=db, data_source_id=ds_id)

        success_msg = f"数据源删除成功：{ds_id_or_code} (ID: {ds_id})"
        return success_msg

    except Exception as e:
        error_msg = f"删除数据源失败：{e!s}"
        return error_msg
    finally:
        db.close()
"""

ROW = {
    "tool": "tool_delete_data_source",
    "description": DESCRIPTION,
    "parameters": "",
    "content": CONTENT,
    "extend": "",
    "id": 6,
}
