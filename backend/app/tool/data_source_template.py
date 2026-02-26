"""
模板常量定义
"""

# 数据源列表模板
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
