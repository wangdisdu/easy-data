"""
工具辅助函数
"""

from app.core.logging import get_logger

logger = get_logger("tool_utils")

# 日志消息截取长度常量
LOG_MESSAGE_TRUNCATE_LENGTH = 100


def format_tool_params(**kwargs) -> str:
    """
    格式化工具参数，隐藏敏感信息

    该函数用于格式化工具函数的参数，以便在日志中记录。
    会自动隐藏敏感信息（如密码、token等），并截断过长的字符串。

    Args:
        **kwargs: 工具函数的参数

    Returns:
        str: 格式化后的参数字符串，格式为 "key1=value1, key2=value2, ..."

    Example:
        >>> format_tool_params(username="admin", password="secret123", database="testdb")
        'username=admin, password=***, database=testdb'
    """
    safe_params = {}
    sensitive_keys = ["password", "token", "secret", "api_key"]

    for key, value in kwargs.items():
        if key in sensitive_keys:
            safe_params[key] = "***"
        elif isinstance(value, str) and len(value) > LOG_MESSAGE_TRUNCATE_LENGTH:
            safe_params[key] = value[:LOG_MESSAGE_TRUNCATE_LENGTH] + "..."
        else:
            safe_params[key] = value

    return ", ".join([f"{k}={v}" for k, v in safe_params.items()])
