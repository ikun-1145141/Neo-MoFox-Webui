"""Authenticated native request-monitor records API (paired host/WebUI upgrade)."""

from __future__ import annotations
from typing import TYPE_CHECKING, Literal
from pydantic import ValidationError
from fastapi import Response
from src.app.plugin_system.api.log_api import get_logger
from src.core.components.base.router import BaseRouter
from src.core.utils.security import VerifiedDep
from ...managers.request_inspector_manager import (
    InspectorUnavailableError,
    get_request_inspector_manager,
)
from ...utils.response import BaseResponse
from ...utils.request_inspector_types import (
    InspectorRecordsSnapshot,
    InspectorRecordDetail,
    InspectorClearResult,
)

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin

logger = get_logger("request_inspector_router")


def _failure(
    response: Response,
    operation: Literal["list", "detail", "clear"],
    error: Exception,
) -> BaseResponse:
    """Return fixed safe diagnostics: never log exception text, input or traceback."""
    category = "internal"
    message = "请求监视器操作失败，请稍后重试"
    if isinstance(error, InspectorUnavailableError):
        category = "incompatible_host"
        message = "请求监视器不可用，请确认主程序与 WebUI 已配套升级"
    elif isinstance(error, ValidationError):
        category = "invalid_contract"
        message = "请求监视器数据格式不兼容，请确认主程序与 WebUI 已配套升级"
    # Even error locations / class names may contain dynamic input. Log only constants.
    logger.error(f"Request inspector operation={operation} category={category}")
    response.status_code = 500
    return BaseResponse.error(code=500, message=message)


class RequestInspectorRouter(BaseRouter):
    """Publish only native lifecycle snapshots, not historical usage analytics."""

    name = "request-inspector"
    description = "WebUI 请求监视器接口"
    custom_route_path = "/webui/api/request-inspector"
    cors_origins = ["*"]
    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """Bind the native snapshot manager to this authenticated router."""
        super().__init__(plugin)
        self.inspector_manager = get_request_inspector_manager()

    def register_endpoints(self) -> None:
        """Register new records endpoints; no old-path compatibility aliases."""

        @self.app.get(
            "/records",
            response_model=BaseResponse[InspectorRecordsSnapshot],
            dependencies=[VerifiedDep],
        )
        async def list_records(
            response: Response,
        ) -> BaseResponse[InspectorRecordsSnapshot]:
            """Get metadata and statistics over the current in-memory buffer."""
            try:
                return BaseResponse.ok(data=self.inspector_manager.list_records())
            except Exception as error:
                return _failure(response, "list", error)

        @self.app.get(
            "/records/{record_id}",
            response_model=BaseResponse[InspectorRecordDetail],
            dependencies=[VerifiedDep],
        )
        async def get_record(
            record_id: int, response: Response
        ) -> BaseResponse[InspectorRecordDetail]:
            """Get one isolated native detail or a standard 404 envelope."""
            try:
                data = self.inspector_manager.get_record(record_id)
                if data is None:
                    response.status_code = 404
                    return BaseResponse.error(code=404, message="记录已清空或淘汰")
                return BaseResponse.ok(data=data)
            except Exception as error:
                return _failure(response, "detail", error)

        @self.app.delete(
            "/records",
            response_model=BaseResponse[InspectorClearResult],
            dependencies=[VerifiedDep],
        )
        async def clear_records(
            response: Response,
        ) -> BaseResponse[InspectorClearResult]:
            """Clear captured data only; do not cancel any model call."""
            try:
                return BaseResponse.ok(data=self.inspector_manager.clear_records())
            except Exception as error:
                return _failure(response, "clear", error)
