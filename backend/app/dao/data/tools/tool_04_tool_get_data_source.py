"""工具初始化数据: tool_get_data_source"""

DESCRIPTION = """根据数据源ID或编码获取数据源信息（主要是code）

该工具用于根据数据源ID或编码获取数据源的基本信息，特别是数据源的编码（code）。
获取正确的数据源code非常重要，因为所有执行SQL的工具（tool_execute_sql_data_source）都需要使用数据源的code。

使用场景：
- 从数据模型中获取ds_id后，需要获取对应的数据源code
- 验证数据源是否存在
- 获取数据源的基本信息（code、platform等）

Args:
    ds_id_or_code: 数据源标识符（必填）
        - 如果为数字字符串，视为数据源ID
        - 否则视为数据源编码（code）
        - 示例：
          * "1" - 数据源ID
          * "mysql_prod_192_168_1_100_users" - 数据源编码

Returns:
    str: 数据源信息，JSON格式
        - 格式示例：
          ```json
          {
            "id": 1,
            "code": "mysql_prod_192_168_1_100_users",
            "name": "MySQL生产环境-用户数据库",
            "platform": "mysql",
            "ds_id": 1
          }
          ```
        - 如果数据源不存在，返回错误信息

Example:
    根据ID获取数据源：
    tool_get_data_source(ds_id_or_code="1")

    根据编码获取数据源：
    tool_get_data_source(ds_id_or_code="mysql_prod_192_168_1_100_users")

Note:
    - 该工具主要用于获取数据源的code，以便后续使用tool_execute_sql_data_source时传入正确的code
    - code是执行SQL时必须使用的标识符
"""

CONTENT = """def tool_get_data_source(ds_id_or_code: str) -> str:
    import json
    from app.dao.database import SessionLocal
    from app.dao.models import TbDataSource
    db = SessionLocal()
    try:
        if ds_id_or_code.isdigit():
            data_source = db.query(TbDataSource).filter(TbDataSource.id == int(ds_id_or_code)).first()
        else:
            data_source = db.query(TbDataSource).filter(TbDataSource.code == ds_id_or_code).first()

        if not data_source:
            error_msg = f"数据源不存在：{ds_id_or_code}"
            return error_msg

        # 转换为字典，只返回必要的信息
        result = {
            "id": data_source.id,
            "code": data_source.code,
            "name": data_source.name,
            "platform": data_source.platform,
            "ds_id": data_source.id,  # 为了兼容，也提供ds_id字段
        }

        result_json = json.dumps(db_config)
        return result_json
    except Exception as e:
        error_msg = f"获取数据源信息时发生错误：{e!s}"
        return error_msg
    finally:
        db.close()
"""

ROW = {
    "tool": "tool_get_data_source",
    "description": DESCRIPTION,
    "parameters": "",
    "content": CONTENT,
    "extend": "",
    "id": 4,
}
