"""
JSON工具类
提供通用的JSON序列化和反序列化功能，处理特殊类型（如Decimal、datetime等）
"""

import base64
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any


def json_dumps(obj: Any, **kwargs) -> str:
    """
    将Python对象序列化为JSON字符串

    自动处理以下特殊类型：
    - Decimal: 转换为 float
    - datetime: 转换为 ISO 格式字符串
    - date: 转换为 ISO 格式字符串
    - 其他不可序列化类型：转换为字符串

    Args:
        obj: 要序列化的Python对象
        **kwargs: 传递给 json.dumps 的其他参数（如 indent, ensure_ascii 等）

    Returns:
        str: JSON字符串

    Example:
        >>> from decimal import Decimal
        >>> data = {"price": Decimal("99.99"), "name": "test"}
        >>> json_dumps(data)
        '{"price": 99.99, "name": "test"}'

        >>> json_dumps(data, indent=2, ensure_ascii=False)
        '{\\n  "price": 99.99,\\n  "name": "test"\\n}'
    """

    def convert_value(value: Any) -> Any:
        """递归转换值，处理特殊类型"""
        if isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, datetime | date):
            return value.isoformat()
        elif isinstance(value, dict):
            return {key: convert_value(val) for key, val in value.items()}
        elif isinstance(value, list | tuple | set):
            return [convert_value(item) for item in value]
        else:
            # 对于其他不可序列化类型，尝试转换为字符串
            try:
                json.dumps(value)
                return value
            except (TypeError, ValueError):
                return str(value)

    # 转换对象
    converted_obj = convert_value(obj)

    # 序列化为JSON
    return json.dumps(converted_obj, **kwargs)


def json_loads(s: str, **kwargs) -> Any:
    """
    将JSON字符串反序列化为Python对象

    这是 json.loads 的简单封装，保持接口一致性

    Args:
        s: JSON字符串
        **kwargs: 传递给 json.loads 的其他参数

    Returns:
        Any: Python对象
    """
    return json.loads(s, **kwargs)


def normalize_query_result(value: Any) -> Any:
    """
    规范化查询结果中的值，处理特殊类型

    处理以下特殊类型：
    - Decimal: 转换为 float
    - datetime: 转换为 ISO 格式字符串
    - date: 转换为 ISO 格式字符串
    - bytes/BLOB: 转换为 base64 编码字符串，并添加标识前缀
    - 其他不可序列化类型：转换为字符串

    Args:
        value: 要规范化的值

    Returns:
        Any: 规范化后的值

    Example:
        >>> from decimal import Decimal
        >>> from datetime import datetime
        >>> normalize_query_result(Decimal("99.99"))
        99.99
        >>> normalize_query_result(datetime(2023, 1, 1, 12, 0, 0))
        '2023-01-01T12:00:00'
        >>> normalize_query_result(b'\\x00\\x01\\x02')
        '<BLOB:base64:AAEC>'
    """
    if value is None:
        return None
    elif isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, datetime | date):
        return value.isoformat()
    elif isinstance(value, bytes):
        # BLOB类型：转换为base64编码，并添加标识前缀
        try:
            base64_str = base64.b64encode(value).decode("utf-8")
            return f"<BLOB:base64:{base64_str}>"
        except Exception:
            # 如果base64编码失败，返回十六进制字符串
            return f"<BLOB:hex:{value.hex()}>"
    elif isinstance(value, dict):
        return {key: normalize_query_result(val) for key, val in value.items()}
    elif isinstance(value, list | tuple | set):
        return [normalize_query_result(item) for item in value]
    else:
        # 对于其他不可序列化类型，尝试转换为字符串
        try:
            json.dumps(value)
            return value
        except (TypeError, ValueError):
            return str(value)


def normalize_query_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    规范化查询结果列表，处理所有特殊类型

    Args:
        results: 查询结果列表，每个元素是一个字典（行数据）

    Returns:
        List[Dict[str, Any]]: 规范化后的查询结果列表

    Example:
        >>> results = [{"id": 1, "price": Decimal("99.99"), "data": b'\\x00\\x01'}]
        >>> normalize_query_results(results)
        [{"id": 1, "price": 99.99, "data": "<BLOB:base64:AAEC>"}]
    """
    return [normalize_query_result(row) for row in results]
