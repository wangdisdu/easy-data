"""
业务异常定义
"""


class BizErrorCode:
    """业务错误码定义"""

    # 通用错误 1000-1099
    UNKNOWN_ERROR = 1000
    INVALID_PARAM = 1001

    # 认证相关错误 1100-1199
    INVALID_TOKEN = 1100
    TOKEN_EXPIRED = 1101
    USER_NOT_FOUND = 1102
    INVALID_CREDENTIALS = 1103

    # 用户相关错误 1200-1299
    USER_ALREADY_EXISTS = 1200
    USER_NOT_EXIST = 1201

    # 工作空间相关错误 1300-1399
    WORKSPACE_CODE_EXISTS = 1300
    WORKSPACE_NOT_EXIST = 1301

    # 数据源相关错误 1400-1499
    DATASOURCE_CODE_EXISTS = 1400
    DATASOURCE_NOT_EXIST = 1401
    DATASOURCE_CONFIG_ERROR = 1402
    DATASOURCE_CONNECTION_ERROR = 1403
    DATASOURCE_SQL_ERROR = 1404
    DATASOURCE_DELETE_ERROR = 1405

    # 数据模型相关错误 1500-1599
    DATAMODEL_CODE_EXISTS = 1500
    DATAMODEL_NOT_EXIST = 1501

    # 智能体相关错误 1600-1699
    AGENT_NOT_EXIST = 1600
    AGENT_NODE_NOT_EXIST = 1602
    AGENT_EDGE_NOT_EXIST = 1603

    # 工具相关错误 1700-1799
    TOOL_NOT_EXIST = 1700
    TOOL_NAME_EXISTS = 1701
    TOOL_DELETE_ERROR = 1702

    # LLM相关错误 1800-1899
    LLM_NOT_EXIST = 1800
    LLM_DELETE_ERROR = 1801

    # 作业相关错误 1900-1999
    JOB_NOT_EXIST = 1900


class BizError(Exception):
    """业务异常类"""

    def __init__(self, code: int, message: str):
        """
        初始化业务异常

        Args:
            code: 错误码
            message: 错误信息
        """
        self.code = code
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"BizError(code={self.code}, message={self.message})"

    def __repr__(self):
        return self.__str__()
