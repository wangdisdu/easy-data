"""工具初始化数据: tool_check_data_sources_basic_info"""

DESCRIPTION = """检查系统内所有数据源的基础信息是否完整

该工具用于检查系统中所有数据源的基础信息（code、name、platform、setting等）是否完整。
基础信息不能缺少，包括：
- code：数据源编码
- name：数据源名称
- platform：数据库类型
- setting：连接配置（JSON格式，包含host、port、username、password、database）

Returns:
    str: 检查结果，JSON格式
        - 格式示例：
          ```json
          {
            "status": "pass|warning",
            "message": "检查结果描述",
            "total_count": 5,
            "complete_count": 4,
            "incomplete_count": 1,
            "incomplete_list": [
              {
                "ds_id": 1,
                "ds_code": "mysql01",
                "missing_fields": ["setting.host", "setting.port"]
              }
            ]
          }
          ```
"""

CONTENT = """def tool_check_data_sources_basic_info() -> str:
    import json
    from app.dao.database import SessionLocal
    from app.dao.models import TbDataSource

    db = SessionLocal()
    try:
        data_sources = db.query(TbDataSource).all()

        if len(data_sources) == 0:
            result = {
                "status": "warning",
                "message": "系统内没有创建任何数据源",
                "total_count": 0,
                "complete_count": 0,
                "incomplete_count": 0,
                "incomplete_list": [],
            }
            result_json = json.dumps(result)
            return result_json

        def _check_data_source_fields(data_source: TbDataSource) -> list[str]:
            missing_fields = []
            if not data_source.code:
                missing_fields.append("code")
            if not data_source.name:
                missing_fields.append("name")
            if not data_source.platform:
                missing_fields.append("platform")
            if not data_source.setting:
                missing_fields.append("setting")
            else:
                try:
                    setting_dict = json.loads(data_source.setting)
                    required_fields = ["host", "port", "username", "password", "database"]
                    for field in required_fields:
                        if field not in setting_dict or not setting_dict[field]:
                            missing_fields.append(f"setting.{field}")
                except json.JSONDecodeError:
                    missing_fields.append("setting（JSON格式错误）")
            return missing_fields

        incomplete_list = []
        for ds in data_sources:
            missing_fields = _check_data_source_fields(ds)
            if missing_fields:
                incomplete_list.append(
                    {
                        "ds_id": ds.id,
                        "ds_code": ds.code,
                        "ds_name": ds.name,
                        "missing_fields": missing_fields,
                    }
                )

        complete_count = len(data_sources) - len(incomplete_list)

        if len(incomplete_list) == 0:
            result = {
                "status": "pass",
                "message": f"所有 {len(data_sources)} 个数据源的基础信息完整",
                "total_count": len(data_sources),
                "complete_count": complete_count,
                "incomplete_count": len(incomplete_list),
                "incomplete_list": [],
            }
        else:
            result = {
                "status": "warning",
                "message": f"{len(incomplete_list)} 个数据源缺少基础信息",
                "total_count": len(data_sources),
                "complete_count": complete_count,
                "incomplete_count": len(incomplete_list),
                "incomplete_list": incomplete_list,
            }

        result_json = json.dumps(result)
        return result_json

    except Exception as e:
        error_msg = f"检查数据源基础信息时发生错误：{e!s}"
        return error_msg
    finally:
        db.close()
"""

ROW = {
    "tool": "tool_check_data_sources_basic_info",
    "description": DESCRIPTION,
    "parameters": "",
    "content": CONTENT,
    "extend": "",
    "id": 17,
}
