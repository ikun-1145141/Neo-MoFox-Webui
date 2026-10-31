"""请求监视器原生记录接口。

提供需要身份认证的请求生命周期记录查询和清理接口。
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from fastapi import Response
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
            response_model=BaseResponse[InspectorRecordsSnapshot],
            dependencies=[VerifiedDep],
        )
        async def list_records(
            response: Response,
        ) -> BaseResponse[InspectorRecordsSnapshot]:
            """读取当前内存缓冲区的记录摘要和统计信息。

            Args:
                response: 用于设置 HTTP 状态码的响应对象。

            Returns:
                记录快照及当前缓冲区统计。
            """
            try:
                return BaseResponse.ok(data=self.inspector_manager.list_records())
            except Exception:
                logger.error("读取请求记录列表失败")
                response.status_code = 500
                return BaseResponse.error(code=500, message="请求监视器操作失败，请稍后重试")

        @self.app.get(
            "/records/{record_id}",
            response_model=BaseResponse[InspectorRecordDetail],
            dependencies=[VerifiedDep],
        )
        async def get_record(
            record_id: int, response: Response
        ) -> BaseResponse[InspectorRecordDetail]:
            """读取指定请求记录的详情。

            Args:
                record_id: 请求记录编号。
                response: 用于设置 HTTP 状态码的响应对象。

            Returns:
                记录详情；记录不存在时返回 404 响应。
            """
            try:
                data = self.inspector_manager.get_record(record_id)
                if data is None:
                    response.status_code = 404
                    return BaseResponse.error(code=404, message="记录已清空或淘汰")
                return BaseResponse.ok(data=data)
            except Exception:
                logger.error("读取请求记录详情失败")
                response.status_code = 500
                return BaseResponse.error(code=500, message="请求监视器操作失败，请稍后重试")

        @self.app.delete(
            "/records",
            response_model=BaseResponse[InspectorClearResult],
            dependencies=[VerifiedDep],
        )
        async def clear_records(
            response: Response,
        ) -> BaseResponse[InspectorClearResult]:
            """清空当前保留的请求记录，不影响正在执行的模型调用。

            Args:
                response: 用于设置 HTTP 状态码的响应对象。

            Returns:
                清理数量及更新后的缓冲区版本。
            """
            try:
                return BaseResponse.ok(data=self.inspector_manager.clear_records())
            except Exception:
                logger.error("清空请求记录失败")
                response.status_code = 500
                return BaseResponse.error(code=500, message="请求监视器操作失败，请稍后重试")
