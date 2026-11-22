"""请求监视器原生记录接口。

提供需要身份认证的请求生命周期记录查询和清理接口。
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from fastapi import HTTPException
from src.app.plugin_system.api.log_api import get_logger
from src.core.components.base.router import BaseRouter
from src.core.utils.security import VerifiedDep
from ...managers.request_inspector_manager import get_request_inspector_manager
from ...utils.response import BaseResponse
from ...utils.request_inspector_types import (
    InspectorRecordsSnapshot,
    InspectorRecordDetail,
    InspectorClearResult,
)

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin

logger = get_logger("request_inspector_router")


class RequestInspectorRouter(BaseRouter):
    """请求监视器原生记录路由，提供请求记录的查询和清理接口。"""

    name = "request-inspector"
    description = "WebUI 请求监视器接口"
    custom_route_path = "/webui/api/request-inspector"
    cors_origins = ["*"]
    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化路由并绑定请求监视器管理器。

        Args:
            plugin: 所属插件实例。
        """
        super().__init__(plugin)
        self.inspector_manager = get_request_inspector_manager()

    def register_endpoints(self) -> None:
        """注册需要身份认证的请求记录查询和清理接口。"""

        @self.app.get(
            "/records",
            dependencies=[VerifiedDep],
        )
        async def list_records() -> BaseResponse[InspectorRecordsSnapshot]:
            """读取当前内存缓冲区的记录摘要和统计信息。

            Returns:
                记录快照及当前缓冲区统计。

            Raises:
                HTTPException: 读取请求记录列表失败时返回 500 错误。
            """
            try:
                return BaseResponse.ok(data=self.inspector_manager.list_records())
            except Exception as exc:
                logger.error("读取请求记录列表失败")
                raise HTTPException(
                    status_code=500, detail="请求监视器操作失败，请稍后重试"
                ) from exc

        @self.app.get(
            "/records/{record_id}",
            dependencies=[VerifiedDep],
        )
        async def get_record(record_id: int) -> BaseResponse[InspectorRecordDetail]:
            """读取指定请求记录的详情。

            Args:
                record_id: 请求记录编号。

            Returns:
                指定请求记录的详情。

            Raises:
                HTTPException: 记录已清空或淘汰时返回 404 错误，读取失败时返回 500 错误。
            """
            try:
                data = self.inspector_manager.get_record(record_id)
            except Exception as exc:
                logger.error("读取请求记录详情失败")
                raise HTTPException(
                    status_code=500, detail="请求监视器操作失败，请稍后重试"
                ) from exc
            if data is None:
                raise HTTPException(status_code=404, detail="记录已清空或淘汰")
            return BaseResponse.ok(data=data)

        @self.app.delete(
            "/records",
            dependencies=[VerifiedDep],
        )
        async def clear_records() -> BaseResponse[InspectorClearResult]:
            """清空当前保留的请求记录，不影响正在执行的模型调用。

            Returns:
                清理数量及更新后的缓冲区版本。

            Raises:
                HTTPException: 清空请求记录失败时返回 500 错误。
            """
            try:
                return BaseResponse.ok(data=self.inspector_manager.clear_records())
            except Exception as exc:
                logger.error("清空请求记录失败")
                raise HTTPException(
                    status_code=500, detail="请求监视器操作失败，请稍后重试"
                ) from exc
