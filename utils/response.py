"""统一响应模型。

所有后端接口必须返回符合此模型的 JSON 结构。
"""

from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """统一响应模型。

    Attributes:
        code: 业务状态码，200 为成功，其余为各类错误
        data: 实际业务数据，失败时可为 None
        message: 可读的状态描述

    Examples:
        >>> # 成功响应
        >>> BaseResponse.ok(data={"key": "value"})
        >>> # 错误响应
        >>> BaseResponse.error(code=400, message="参数错误")
    """

    code: int = Field(default=200, description="业务状态码")
    data: T | None = Field(default=None, description="业务数据")
    message: str = Field(default="success", description="状态描述")

    @classmethod
    def ok(cls, data: Any = None, message: str = "success") -> "BaseResponse":
        """创建成功响应。

        Args:
            data: 业务数据
            message: 状态描述

        Returns:
            成功响应实例
        """
        return cls(code=200, data=data, message=message)

    @classmethod
    def error(cls, code: int = 500, message: str = "error", data: Any = None) -> "BaseResponse":
        """创建错误响应。

        Args:
            code: 错误码
            message: 错误描述
            data: 可选的错误详情

        Returns:
            错误响应实例
        """
        return cls(code=code, data=data, message=message)
