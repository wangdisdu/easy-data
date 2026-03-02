"""工具初始化数据: tool_update_data_source"""

DESCRIPTION = """更新数据源的名称、账号密码等信息

该工具用于更新已存在数据源的部分信息，支持更新名称、账号密码等。

使用场景：
- 修改数据源的显示名称
- 更新数据源的账号密码
- 修改数据源的连接配置

重要提示：
- 只能更新名称、账号密码，不能修改数据源编码（code）、平台类型（platform）等核心信息
- 如果只更新账号密码，需要提供完整的连接配置（host、port、database等保持不变）
- 更新账号密码时，需要重新构建 setting JSON

Args:
    ds_id_or_code: 数据源标识符（必填）。
        如果为数字字符串，视为数据源ID；否则视为数据源编码（code）。
        示例："1"（数据源ID）、"mysql01"（数据源编码）。
    name: 数据源显示名称（可选）.如果提供，则更新数据源的名称。
    username: 新的用户名（可选）.如果提供，则更新数据源的账号。
    password: 新的密码（可选）.如果提供，则更新数据源的密码。

Returns:
    str: 更新结果
        - 成功时：返回 "数据源更新成功：ID={ds_id}"
        - 失败时：返回错误原因
        - 常见错误：
          * "数据源不存在：{ds_id_or_code}" - 数据源不存在
          * "更新数据源失败：{错误信息}" - 更新失败
          * "必须提供至少一个要更新的字段（name、username、password）" - 未提供任何更新字段

Example:
    只更新名称：
    tool_update_data_source(
        ds_id_or_code="1",
        name="MySQL生产环境-新名称"
    )

    只更新账号密码：
    tool_update_data_source(
        ds_id_or_code="mysql01",
        username="newuser",
        password="newpassword"
    )

    同时更新名称和账号密码：
    tool_update_data_source(
        ds_id_or_code="1",
        name="MySQL生产环境-新名称",
        username="newuser",
        password="newpassword"
    )

Note:
    - ds_id_or_code 必须是已存在的数据源ID或编码
    - 必须提供至少一个要更新的字段（name、username、password）
    - 更新账号密码时，会保留原有的 host、port、database 等配置
"""

CONTENT = """def tool_update_data_source(
    ds_id_or_code: str,
    name: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> str:
    import json
    from app.dao.database import SessionLocal
    from app.dao.models import TbDataSource
    from app.service.data_source_service import DataSourceUpdate
    from app.service.data_source_service import DataSourceService
    db = SessionLocal()
    try:
        # 检查是否提供了至少一个更新字段
        if not any([name, username, password]):
            error_msg = "必须提供至少一个要更新的字段（name、username、password）"
            return error_msg

        if ds_id_or_code.isdigit():
            data_source = db.query(TbDataSource).filter(TbDataSource.id == int(ds_id_or_code)).first()
        else:
            data_source = db.query(TbDataSource).filter(TbDataSource.code == ds_id_or_code).first()

        if not data_source:
            error_msg = f"数据源不存在：{ds_id_or_code}"
            return error_msg

        ds_id = data_source.id

        # 构建更新对象
        data_source_update = DataSourceUpdate()

        # 更新名称
        if name is not None:
            data_source_update.name = name

        # 更新账号密码（需要更新 setting）
        if username is not None or password is not None:
            # 解析现有的 setting
            try:
                setting = json.loads(data_source.setting)
            except json.JSONDecodeError:
                error_msg = f"数据源配置格式错误：ID={ds_id}"
                return error_msg

            # 更新账号密码
            if username is not None:
                setting["username"] = username
            if password is not None:
                setting["password"] = password

            # 重新序列化为JSON
            data_source_update.setting = json.dumps(db_config)

            # 执行更新
            DataSourceService.update_data_source(
                db=db,
                data_source_id=ds_id,
                data_source_update=data_source_update,
                update_user_id=1,  # 使用系统用户ID
            )

        success_msg = f"数据源更新成功：{ds_id_or_code} (ID: {ds_id})"
        return success_msg

    except Exception as e:
        error_msg = f"更新数据源失败：{e!s}"
        return error_msg

    finally:
        db.close()
"""

ROW = {
    "tool": "tool_update_data_source",
    "description": DESCRIPTION,
    "parameters": "",
    "content": CONTENT,
    "extend": "",
    "id": 5,
}
