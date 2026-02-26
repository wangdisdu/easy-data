"""工具初始化数据: tool_import_data_models_by_data_source"""

DESCRIPTION = """自动将指定数据源的所有表和视图转为数据模型

该工具用于自动扫描指定数据源中的所有表和视图，并为每个表和视图创建对应的数据模型。
可以一次性批量创建多个数据模型，提高创建效率。

使用场景：
- 从数据源自动生成数据模型
- 批量导入数据库表和视图为数据模型
- 快速建立数据模型目录

重要提示：
- 数据模型的 `code` 必须唯一，如果已存在相同code的数据模型，该条记录会跳过并记录错误
- 批量创建时，如果某条记录失败，不会影响其他记录的创建
- 返回结果会包含成功和失败的详细信息

模型code生成说明：
  * 如果数据库支持schema且设置了schema：code格式为 `{database}.{schema}.{table/view}`
  * 如果不支持schema或未设置schema：code格式为 `{database}.{table/view}`

模型name生成说明：
  * name直接使用表名或视图名

Args:
    ds_id_or_code: 数据源标识符，可以是数据源编码(code)或数据源ID（字符串格式的数字）.
        如果以数字开头且全为数字，则视为数据源ID，否则视为数据源编码(code).
        示例:"mysql01"（数据源编码）、"1"（数据源ID）、"123"（数据源ID）.
        注意：数据源必须已配置 database 字段，否则会返回错误。

Returns:
    str: 批量创建结果，JSON格式
        - 成功时：返回创建结果摘要，包括成功数量、失败数量、成功记录详情和失败记录详情
        - 格式示例：
          ```json
          {
            "success_count": 5,
            "failure_count": 1,
            "total_count": 6,
            "table_count": 4,
            "view_count": 2,
            "success_items": [
              {
                "code": "public.users",
                "name": "users",
                "type": "table",
                "id": 1
              },
              {
                "code": "public.orders",
                "name": "orders",
                "type": "table",
                "id": 2
              },
              {
                "code": "public.user_view",
                "name": "user_view",
                "type": "view",
                "id": 3
              }
            ],
            "failure_items": [
              {
                "code": "public.duplicate_table",
                "name": "duplicate_table",
                "type": "table",
                "error": "数据模型编码已存在"
              }
            ]
          }
          ```
        - 如果所有记录都成功:failure_count 为 0,failure_items 为空数组
        - 如果所有记录都失败:success_count 为 0,success_items 为空数组

Example:
    自动创建数据模型（PostgreSQL，使用数据源配置中的database和默认schema 'public'）:
    tool_import_data_models_auto(
        ds_id_or_code="postgresql01"
    )

    自动创建数据模型（MySQL，使用数据源配置中的database）:
    tool_import_data_models_auto(
        ds_id_or_code="mysql01"
    )

    自动创建数据模型（SQLite，使用数据源配置中的database文件路径）:
    tool_import_data_models_auto(
        ds_id_or_code="sqlite01"
    )

Note:
    - code 必须唯一，如果已存在相同code的数据模型，该条记录会跳过
    - 批量创建时，如果某条记录失败，不会影响其他记录的创建
    - 如果数据源配置中缺少 database 字段，会返回错误
"""

CONTENT = """def tool_import_data_models_by_data_source(ds_id_or_code: str) -> str:
    import json
    import contextlib
    from app.dao.database import SessionLocal
    from app.dao.models import TbDataSource
    from app.dao.models import TbDataModel
    from app.services.data_models_service import DataModelService
    from app.services.data_models_service import DataModelCreate
    from app.connector.factory import ConnectorFactory
    db = SessionLocal()
    try:
        if ds_id_or_code.isdigit():
            data_source = db.query(TbDataSource).filter(TbDataSource.id == int(ds_id_or_code)).first()
        else:
            data_source = db.query(TbDataSource).filter(TbDataSource.code == ds_id_or_code).first()

        if not data_source:
            error_msg = f"数据源不存在：{ds_id_or_code}"
            return error_msg

        setting = json.loads(data_source.setting)

        platform = data_source.platform
        host = setting.get("host")
        port = setting.get("port")
        username = setting.get("username")
        password = setting.get("password")
        database = setting.get("database")
        schema = setting.get("schema")

        # 从数据源配置中获取database
        if not database:
            error_msg = "数据源配置中缺少 database 字段，无法自动导入数据模型"
            return error_msg

        # 创建连接器实例
        connector = None
        # 获取表和视图列表
        try:
            connector = ConnectorFactory.create_connector(
                platform,
                host=host,
                port=port,
                username=username,
                password=password,
                database=database,
            )
            # 获取所有表
            tables = connector.get_tables(database=database, schema=schema)

            # 获取所有视图
            views = connector.get_views(database=database, schema=schema)

        except Exception as e:
            error_msg = f"获取表和视图列表时发生错误：{e!s}"
            return error_msg
        finally:
            # 关闭连接器连接
            if connector:
                with contextlib.suppress(Exception):
                    connector.close()

        # 生成code的前缀
        # 如果提供了schema，code格式为 {database}.{schema}.{table/view}，否则为 {database}.{table/view}
        code_prefix = f"{database}.{schema}" if schema else database

        success_items = []
        failure_items = []

        def create_data_model_for_item(item_name: str, item_type: str, type_label: str) -> None:
            model_code = f"{code_prefix}.{item_name}"
            try:
                # 构建DataModelCreate对象
                data_model_create = DataModelCreate(
                    code=model_code,
                    name=item_name,
                    platform=platform,
                    type=item_type,
                    ds_id=data_source.id,
                    description=None,
                    extend=None,
                    workspace_ids=None,
                )
                # 创建数据模型
                created_model = DataModelService.create_data_model(
                    db=db,
                    data_model_data=data_model_create,
                    create_user_id=1,  # 使用系统用户ID
                )
                success_items.append(
                    {
                        "code": created_model.code,
                        "name": created_model.name,
                        "type": item_type,
                        "id": created_model.id,
                    }
                )
            except BizError as e:
                failure_items.append(
                    {
                        "code": model_code,
                        "name": item_name,
                        "type": item_type,
                        "error": e.message,
                    }
                )

        # 为每个表创建数据模型
        for table_name in tables:
            create_data_model_for_item(table_name, "table", "表")

        # 为每个视图创建数据模型
        for view_name in views:
            create_data_model_for_item(view_name, "view", "视图")

        # 构建返回结果
        total_count = len(tables) + len(views)

        result = {
            "success_count": len(success_items),
            "failure_count": len(failure_items),
            "total_count": total_count,
            "table_count": len(tables),
            "view_count": len(views),
            "success_items": success_items,
            "failure_items": failure_items,
        }

        result_json = json.dumps(result)
        return result_json

    except Exception as e:
        error_msg = f"自动创建数据模型时发生错误：{e!s}"
        return error_msg
    finally:
        db.close()
"""

ROW = {
    "tool": "tool_import_data_models_by_data_source",
    "description": DESCRIPTION,
    "parameters": "",
    "content": CONTENT,
    "extend": "",
    "id": 11,
}
