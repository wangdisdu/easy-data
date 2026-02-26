from dataclasses import dataclass


@dataclass
class ConnectionTestResult:
    """
    数据库连接测试结果
    """

    success: bool
    """连接是否成功"""
    message: str
    """连接信息"""
