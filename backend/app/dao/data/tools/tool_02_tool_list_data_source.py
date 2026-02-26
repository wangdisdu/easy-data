"""工具初始化数据: tool_list_data_source"""

DESCRIPTION = """获取系统中所有已配置的数据源列表

该工具用于查询和展示系统中所有已保存的数据源配置信息。返回结果使用markdown格式，便于阅读和展示。
使用场景：
- 查看系统中已配置的所有数据源
- 了解数据源的连接配置信息
- 查找特定数据源的编码、名称或者连接配置
- 检查数据源是否已经存在了
- 检查数据源的语义说明和描述信息

返回信息包括：
- 数据源ID：系统内部唯一标识
- 编码（code）：用户定义的唯一标识符
- 名称（name）：数据源的显示名称
- 平台（platform）：数据库类型
- 连接配置（setting）：完整的连接配置JSON，包含host、port、username、password、database
- 语义说明（semantic）：数据源的业务语义描述（如果有）
- 描述（description）：数据源的详细描述（如果有）
- 创建时间（create_time）：数据源创建的时间戳

Args:
     没有参数

Returns:
    str: 数据源列表信息，使用markdown格式返回。如果有数据源，返回格式化的markdown列表，每个数据源包含完整信息。
        如果没有数据源，返回 "当前系统内没有配置任何数据源。"。
        格式示例：
        ```
        # 数据源列表
        系统内共找到 1 个数据源：
        ## MySQL生产环境-用户数据库 (mysql_prod_192_168_1_100_users)
        **ID**: 1
        **编码**: mysql_prod_192_168_1_100_users
        **名称**: MySQL生产环境-用户数据库
        **平台**: mysql
        **连接配置**:
        ```json
        {"host": "192.168.1.100", "port": 3306, "username": "dbuser", "password": "***", "database": "users"}
        ```
        **创建时间**: 1234567890
        ```
"""

CONTENT = '''def tool_list_data_source() -> str:
    from app.dao.database import SessionLocal
    from app.dao.models import TbDataSource
    from jinja2 import Template
    DATA_SOURCES_TEMPLATE = """# 数据源列表

{% if data_sources %}
系统内共找到 {{ total }} 个数据源：

{% for ds in data_sources %}
## {{ ds.name }} ({{ ds.code }})

- **ID**: {{ ds.id }}
- **编码**: {{ ds.code }}
- **名称**: {{ ds.name }}
- **平台**: {{ ds.platform }}
- **连接配置**:
  ```json
  {{ ds.setting }}
  ```
{% if ds.semantic %}
- **语义说明**:
  {{ ds.semantic }}
{% endif %}
{% if ds.description %}
- **描述**: {{ ds.description }}
{% endif %}
- **创建时间**: {{ ds.create_time }}

---
{% endfor %}
{% else %}
当前系统内没有配置任何数据源。
{% endif %}
"""
    db = SessionLocal()
    try:
        # 直接查询所有数据源，不分页
        data_sources = db.query(TbDataSource).all()
        total = len(data_sources)

        # 使用模板渲染markdown
        template = Template(DATA_SOURCES_TEMPLATE)
        result = template.render(data_sources=data_sources, total=total)

        return result

    except Exception as e:
        error_msg = f"获取数据源列表时发生错误：{e!s}"
        return error_msg
    finally:
        db.close()
'''

ROW = {
    "tool": "tool_list_data_source",
    "description": DESCRIPTION,
    "parameters": "",
    "content": CONTENT,
    "extend": "",
    "id": 2,
}
