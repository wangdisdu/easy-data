from typing import Optional

from pydantic import BaseModel, Field


class Resp[T](BaseModel):
    """
    统一响应模型

    Attributes:
        code: 响应码，0000表示成功，其他表示失败
        msg: 响应消息
        data: 响应数据，根据不同接口返回不同类型
    """

    code: str = Field(default="0000", description="响应码，0000表示成功，其他表示失败")
    msg: str = Field(default="成功", description="响应消息")
    data: Optional[T] = Field(default=None, description="响应数据")


class PagedResp[T](BaseModel):
    """
    分页响应模型

    Attributes:
        code: 响应码，0000表示成功，其他表示失败
        msg: 响应消息
        data: 分页数据列表
        total: 总记录数
    """

    code: str = Field(default="0000", description="响应码，0000表示成功，其他表示失败")
    msg: str = Field(default="成功", description="响应消息")
    data: list[T] = Field(default_factory=list, description="分页数据列表")
    total: int = Field(default=0, description="总记录数")
