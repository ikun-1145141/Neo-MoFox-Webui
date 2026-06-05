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
            """获取内存指标和持久化统计的组合总览。"""
            try:
                data = await self.metrics_manager.get_overview()
                return BaseResponse.ok(data=data, message="获取 LLM 统计总览成功")
            except Exception as exc:
                logger.error(f"获取 LLM 统计总览失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取 LLM 统计总览失败: {exc}")

        @self.app.get("/overview/memory", response_model=BaseResponse[dict[str, Any]], dependencies=[VerifiedDep])
        async def get_memory_overview() -> BaseResponse[dict[str, Any]]:
            """获取旧内存收集器的 LLM 指标总览。"""
            try:
                data = self.metrics_manager.get_memory_overview()
                return BaseResponse.ok(data=data, message="获取内存 LLM 指标总览成功")
            except Exception as exc:
                logger.error(f"获取内存 LLM 指标总览失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取内存 LLM 指标总览失败: {exc}")

        @self.app.get("/overview/persistent", response_model=BaseResponse[dict[str, Any]], dependencies=[VerifiedDep])
        async def get_persistent_overview() -> BaseResponse[dict[str, Any]]:
            """获取持久化 LLM 统计后端的摘要。"""
            try:
                data = await self.metrics_manager.get_persistent_overview()
                return BaseResponse.ok(data=data, message="获取持久化 LLM 统计摘要成功")
            except Exception as exc:
                logger.error(f"获取持久化 LLM 统计摘要失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取持久化 LLM 统计摘要失败: {exc}")

        @self.app.get("/models", response_model=BaseResponse[list[dict[str, Any]]], dependencies=[VerifiedDep])
        async def list_models() -> BaseResponse[list[dict[str, Any]]]:
            """获取持久化统计后端中的按模型分组统计。"""
            try:
                data = await self.metrics_manager.list_models()
                return BaseResponse.ok(data=data, message="获取 LLM 模型统计成功")
            except Exception as exc:
                logger.error(f"获取 LLM 模型统计失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取 LLM 模型统计失败: {exc}")

        @self.app.get("/models/memory", response_model=BaseResponse[list[dict[str, Any]]], dependencies=[VerifiedDep])
        async def list_memory_models() -> BaseResponse[list[dict[str, Any]]]:
            """获取内存收集器中的按模型分组指标。"""
            try:
                data = self.metrics_manager.list_memory_models()
                return BaseResponse.ok(data=data, message="获取内存 LLM 模型指标成功")
            except Exception as exc:
                logger.error(f"获取内存 LLM 模型指标失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取内存 LLM 模型指标失败: {exc}")

        @self.app.get("/models/{model_name}", response_model=BaseResponse[dict[str, Any]], dependencies=[VerifiedDep])
        async def get_model(model_name: str) -> BaseResponse[dict[str, Any]]:
            """获取内存收集器中的单模型指标。

            Args:
                model_name: 模型名称或模型标识符。
            """
            try:
                data = self.metrics_manager.get_model(model_name)
                return BaseResponse.ok(data=data, message="获取单模型指标成功")
            except Exception as exc:
                logger.error(f"获取单模型指标失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取单模型指标失败: {exc}")

        @self.app.get("/request-names", response_model=BaseResponse[list[dict[str, Any]]], dependencies=[VerifiedDep])
        async def list_request_names() -> BaseResponse[list[dict[str, Any]]]:
            """获取按 request_name 分组的持久化统计。"""
            try:
                data = await self.metrics_manager.list_request_names()
                return BaseResponse.ok(data=data, message="获取 LLM 请求名称统计成功")
            except Exception as exc:
                logger.error(f"获取 LLM 请求名称统计失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取 LLM 请求名称统计失败: {exc}")

        @self.app.get("/request-names/window", response_model=BaseResponse[list[dict[str, Any]]], dependencies=[VerifiedDep])
        async def get_request_name_window_summary(
            start_ts: float = Query(..., description="起始 Unix 时间戳"),
            end_ts: float = Query(..., description="结束 Unix 时间戳"),
            limit: int = Query(default=10, ge=1, le=100, description="返回数量上限"),
        ) -> BaseResponse[list[dict[str, Any]]]:
            """获取指定时间窗口内的 Top request_name 聚合统计。"""
            try:
                data = await self.metrics_manager.get_request_name_window_summary(
                    start_ts=start_ts,
                    end_ts=end_ts,
                    limit=limit,
                )
                return BaseResponse.ok(data=data, message="获取窗口请求名称统计成功")
            except Exception as exc:
                logger.error(f"获取窗口请求名称统计失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取窗口请求名称统计失败: {exc}")

        @self.app.get("/recent", response_model=BaseResponse[list[dict[str, Any]]], dependencies=[VerifiedDep])
        async def get_recent_requests(
            limit: int = Query(default=100, ge=1, le=1000, description="返回数量上限"),
            offset: int = Query(default=0, ge=0, description="分页偏移量"),
        ) -> BaseResponse[list[dict[str, Any]]]:
            """获取最近的持久化 LLM 请求明细。"""
            try:
                data = await self.metrics_manager.get_recent_requests(limit=limit, offset=offset)
                return BaseResponse.ok(data=data, message="获取最近 LLM 请求明细成功")
            except Exception as exc:
                logger.error(f"获取最近 LLM 请求明细失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取最近 LLM 请求明细失败: {exc}")

        @self.app.get("/recent/memory", response_model=BaseResponse[list[dict[str, Any]]], dependencies=[VerifiedDep])
        async def get_recent_memory_history(
            limit: int = Query(default=100, ge=1, le=1000, description="返回数量上限"),
        ) -> BaseResponse[list[dict[str, Any]]]:
            """获取内存收集器中的最近 LLM 请求历史。"""
            try:
                data = self.metrics_manager.get_recent_memory_history(limit=limit)
                return BaseResponse.ok(data=data, message="获取内存 LLM 请求历史成功")
            except Exception as exc:
                logger.error(f"获取内存 LLM 请求历史失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取内存 LLM 请求历史失败: {exc}")

        @self.app.get("/cache-hit-rate", response_model=BaseResponse[dict[str, Any]], dependencies=[VerifiedDep])
        async def get_cache_hit_rate(
            stream_id: str | None = Query(default=None, description="可选聊天流 ID"),
        ) -> BaseResponse[dict[str, Any]]:
            """获取全局或指定聊天流的缓存命中率。"""
            try:
                data = await self.metrics_manager.get_cache_hit_rate(stream_id=stream_id)
                return BaseResponse.ok(data=data, message="获取 LLM 缓存命中率成功")
            except Exception as exc:
                logger.error(f"获取 LLM 缓存命中率失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取 LLM 缓存命中率失败: {exc}")

        @self.app.get("/streams", response_model=BaseResponse[list[dict[str, Any]]], dependencies=[VerifiedDep])
        async def list_streams() -> BaseResponse[list[dict[str, Any]]]:
            """获取按 stream_id 分组的持久化统计。"""
            try:
                data = await self.metrics_manager.list_streams()
                return BaseResponse.ok(data=data, message="获取 LLM 流统计成功")
            except Exception as exc:
                logger.error(f"获取 LLM 流统计失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取 LLM 流统计失败: {exc}")

        @self.app.get("/time-range", response_model=BaseResponse[dict[str, Any]], dependencies=[VerifiedDep])
        async def get_time_range_summary(
            start_ts: float = Query(..., description="起始 Unix 时间戳"),
            end_ts: float = Query(..., description="结束 Unix 时间戳"),
        ) -> BaseResponse[dict[str, Any]]:
            """获取指定时间范围内的持久化统计摘要。"""
            try:
                data = await self.metrics_manager.get_time_range_summary(
                    start_ts=start_ts,
                    end_ts=end_ts,
                )
                return BaseResponse.ok(data=data, message="获取 LLM 时间范围统计成功")
            except Exception as exc:
                logger.error(f"获取 LLM 时间范围统计失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取 LLM 时间范围统计失败: {exc}")

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

