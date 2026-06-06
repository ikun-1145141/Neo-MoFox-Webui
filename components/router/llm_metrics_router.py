"""LLM Metrics Router 组件。

提供 WebUI 大模型统计后端接口，覆盖 Neo-MoFox 现有 LLM 统计后端的查询能力。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Query

from src.app.plugin_system.api.log_api import get_logger  # type: ignore
from src.core.components.base.router import BaseRouter  # type: ignore
from src.core.utils.security import VerifiedDep  # type: ignore

from ...managers.llm_metrics_manager import get_llm_metrics_manager
from ...utils.response import BaseResponse

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin  # type: ignore

logger = get_logger("llm_metrics_router")


class LLMMetricsRouter(BaseRouter):
    """WebUI LLM 统计 Router 组件。"""

    router_name: str = "llm-metrics"
    router_description: str = "WebUI 大模型统计接口"
    custom_route_path: str = "/webui/api/llm-metrics"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化 Router。

        Args:
            plugin: 所属插件实例。
        """
        super().__init__(plugin)
        self.metrics_manager = get_llm_metrics_manager()

    def register_endpoints(self) -> None:
        """注册 LLM 统计 API 端点。"""

        @self.app.get("/overview", response_model=BaseResponse[dict[str, Any]], dependencies=[VerifiedDep])
        async def get_overview() -> BaseResponse[dict[str, Any]]:
            """获取数据库中的 LLM 统计摘要。"""
            try:
                data = await self.metrics_manager.get_overview()
                return BaseResponse.ok(data=data, message="获取 LLM 统计总览成功")
            except Exception as exc:
                logger.error(f"获取 LLM 统计总览失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取 LLM 统计总览失败: {exc}")

        @self.app.get("/recent-by-time", response_model=BaseResponse[list[dict[str, Any]]], dependencies=[VerifiedDep])
        async def get_recent_requests_by_time(
            hours: float = Query(default=5.0, ge=0.0, le=8760.0, description="向前查询的小时数"),
            limit: int = Query(default=1000, ge=1, le=1000, description="返回数量上限"),
            offset: int = Query(default=0, ge=0, description="分页偏移量"),
        ) -> BaseResponse[list[dict[str, Any]]]:
            """获取最近若干小时内的 LLM 请求明细。"""
            try:
                data = await self.metrics_manager.get_recent_requests_by_hours(
                    hours=hours,
                    limit=limit,
                    offset=offset,
                )
                return BaseResponse.ok(data=data, message="获取最近 LLM 请求明细成功")
            except Exception as exc:
                logger.error(f"获取最近 LLM 请求明细失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取最近 LLM 请求明细失败: {exc}")

        @self.app.get("/streams", response_model=BaseResponse[list[dict[str, Any]]], dependencies=[VerifiedDep])
        async def list_streams() -> BaseResponse[list[dict[str, Any]]]:
            """获取按 stream_id 分组的持久化统计。"""
            try:
                data = await self.metrics_manager.list_streams()
                return BaseResponse.ok(data=data, message="获取 LLM 流统计成功")
            except Exception as exc:
                logger.error(f"获取 LLM 流统计失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取 LLM 流统计失败: {exc}")

        @self.app.get("/last-hours", response_model=BaseResponse[dict[str, Any]], dependencies=[VerifiedDep])
        async def get_last_hours_summary(
            hours: float = Query(default=5.0, ge=0.0, le=8760.0, description="向前统计的小时数"),
        ) -> BaseResponse[dict[str, Any]]:
            """获取最近若干小时的持久化统计摘要。"""
            try:
                data = await self.metrics_manager.get_last_hours_summary(hours=hours)
                return BaseResponse.ok(data=data, message="获取最近 LLM 统计成功")
            except Exception as exc:
                logger.error(f"获取最近 LLM 统计失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取最近 LLM 统计失败: {exc}")

