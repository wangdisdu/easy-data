"""工具初始化数据: tool_execute_sql_data_model"""

DESCRIPTION = """在指定数据模型所属的数据源上执行SQL查询

该工具用于在数据模型所属的数据源上执行SQL查询语句，并返回查询结果。通过数据模型编码(code)或数据模型ID来指定数据模型，然后找到该模型关联的数据源，并在该数据源上执行SQL.

使用场景：
- 查询数据模型对应的数据源中的数据
- 执行针对特定数据模型的数据分析SQL语句
- 验证数据模型对应的数据内容
- 执行统计查询、聚合查询等

重要提示：
- 该工具只支持SELECT查询语句，不支持INSERT、UPDATE、DELETE等修改数据的操作
- SQL语句应该经过验证，避免SQL注入攻击
- 查询结果会自动处理特殊字段类型（时间类型、BLOB类型、DECIMAL等）
- 如果数据模型的ds_id为空或数据源不存在，会返回相应的错误信息

Args:
    dm_id_or_code: 数据模型标识符，可以是数据模型编码(code)或数据模型ID（字符串格式的数字）.
        如果以数字开头且全为数字，则视为数据模型ID;否则视为数据模型编码(code).
        示例:"public.users"（数据模型编码）、"1"（数据模型ID）、"123"（数据模型ID）.

    sql: 要执行的SQL查询语句。
        必须是SELECT查询语句，支持参数化查询（根据数据库类型使用不同的占位符）.
        示例:"SELECT * FROM users LIMIT 10"、"SELECT COUNT(*) as total FROM orders WHERE status = 'completed'"、
        "SELECT id, name, created_at FROM products ORDER BY created_at DESC".

Returns:
    str: SQL执行结果，JSON格式
        - 成功时：返回查询结果，格式为JSON数组，每个元素是一个字典（行数据）
        - 失败时：返回错误信息
        - 格式示例：
          ```json
          [
            {
              "id": 1,
              "name": "张三",
              "age": 25,
              "created_at": "2023-01-01T12:00:00",
              "price": 99.99,
              "avatar": "<BLOB:base64:iVBORw0KGgoAAAANS...>"
            },
            {
              "id": 2,
              "name": "李四",
              "age": 30,
              "created_at": "2023-01-02T12:00:00",
              "price": 199.99,
              "avatar": null
            }
          ]
          ```
        - 特殊字段类型处理：
          * 时间类型(datetime, date):转换为ISO格式字符串（如:"2023-01-01T12:00:00"）
          * BLOB类型(bytes):转换为base64编码字符串，格式为"<BLOB:base64:...>"
          * DECIMAL类型：转换为float类型
          * NULL值：保持为null

Example:
    通过数据模型编码执行查询：
    tool_execute_sql_data_model(
        dm_id_or_code="public.users",
        sql="SELECT * FROM users LIMIT 10"
    )

    通过数据模型ID执行查询：
    tool_execute_sql_data_model(
        dm_id_or_code="1",
        sql="SELECT COUNT(*) as total FROM orders WHERE status = 'completed'"
    )

    执行带条件的查询：
    tool_execute_sql_data_model(
        dm_id_or_code="public.products",
        sql="SELECT id, name, created_at FROM products WHERE price > 100 ORDER BY created_at DESC"
    )

Note:
    - 只支持SELECT查询，不支持数据修改操作
    - 查询结果会自动处理特殊字段类型，确保可以正确序列化为JSON
    - 如果数据模型不存在、ds_id为空或数据源不存在，会返回相应的错误信息
    - 如果SQL语句执行失败，会返回详细的错误信息
"""

CONTENT = """def tool_execute_sql_data_model(dm_id_or_code: str, sql: str) -> str:
    import base64
    import contextlib
    import json
    from typing import Any
    from datetime import date, datetime
    from decimal import Decimal
    from app.dao.database import SessionLocal
    from app.dao.models import TbDataSource
    from app.dao.models import TbDataModel
    from app.connector.factory import ConnectorFactory
    db = SessionLocal()
    try:
        if dm_id_or_code.isdigit():
            data_model = db.query(TbDataModel).filter(TbDataModel.id == int(dm_id_or_code)).first()
        else:
            data_model = db.query(TbDataModel).filter(TbDataModel.code == dm_id_or_code).first()

        if not data_model:
            error_msg = f"数据模型不存在：{dm_id_or_code}"
            return error_msg

        # 检查数据模型的ds_id是否存在
        if not data_model.ds_id:
            error_msg = f"数据模型的ds_id为空：{dm_id_or_code}"
            return error_msg

        data_source = db.query(TbDataSource).filter(TbDataSource.id == data_model.ds_id).first()

        if not data_source:
            error_msg = f"数据源不存在：ds_id={data_model.ds_id}"
            return error_msg

        setting = json.loads(data_source.setting)

        platform = data_source.platform
        host = setting.get("host")
        port = setting.get("port")
        username = setting.get("username")
        password = setting.get("password")
        database = setting.get("database")
        # 执行SQL查询
        connector = None
        try:
            # 创建连接器实例
            connector = ConnectorFactory.create_connector(
                platform,
                host=host,
                port=port,
                username=username,
                password=password,
                database=database,
            )
            results = connector.execute_query(sql)

            # 规范化查询结果（处理 Decimal/datetime/bytes 等，便于 JSON 序列化）
            def _normalize_value(value: Any) -> Any:
                if value is None:
                    return None
                if isinstance(value, Decimal):
                    return float(value)
                if isinstance(value, datetime | date):
                    return value.isoformat()
                if isinstance(value, bytes):
                    try:
                        return f"<BLOB:base64:{base64.b64encode(value).decode('utf-8')}>"
                    except Exception:
                        return f"<BLOB:hex:{value.hex()}>"
                if isinstance(value, dict):
                    return {k: _normalize_value(v) for k, v in value.items()}
                if isinstance(value, list | tuple | set):
                    return [_normalize_value(item) for item in value]
                try:
                    json.dumps(value)
                    return value
                except (TypeError, ValueError):
                    return str(value)

            normalized_results = [
                {k: _normalize_value(v) for k, v in row.items()} for row in results
            ]

            # 转换为JSON字符串
            result_json = json.dumps(normalized_results)
            return result_json

        except Exception as e:
            error_msg = f"执行SQL查询时发生错误：{e!s}"
            return error_msg
        finally:
            # 关闭连接器连接
            if connector:
                with contextlib.suppress(Exception):
                    connector.close()

    except Exception as e:
        error_msg = f"处理SQL执行请求时发生错误：{e!s}"
        return error_msg
    finally:
        db.close()
"""

ROW = {
    "tool": "tool_execute_sql_data_model",
    "description": DESCRIPTION,
    "parameters": "",
    "content": CONTENT,
    "extend": "",
    "id": 16,
}
