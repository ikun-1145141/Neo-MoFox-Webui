"""仪表盘数据聚合管理器。

负责聚合 WebUI 首页所需的运行总览、业务核心和 LLM 运营指标，
为 Router 提供统一读取入口。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.core.components.registry import get_global_registry  # type: ignore
from src.core.components.types import ComponentType  # type: ignore
from src.core.managers.adapter_manager import get_adapter_manager  # type: ignore
from src.core.managers.event_manager import get_event_manager  # type: ignore
from src.core.managers.plugin_manager import get_plugin_manager  # type: ignore
from src.core.managers.stream_manager import get_stream_manager  # type: ignore
from src.core.models.sql_alchemy import Messages  # type: ignore
from src.kernel.concurrency import get_task_manager  # type: ignore
from src.kernel.db.api.query import QueryBuilder  # type: ignore
from src.kernel.scheduler import get_unified_scheduler  # type: ignore

from ..utils import get_llm_metrics_helper


class DashboardManager:
    """仪表盘管理器。"""

    async def get_overview(self) -> dict[str, Any]:
        """获取首页总览数据。"""
        runtime_overview = self._get_runtime_overview()
        business_overview = await self._get_business_overview()
        llm_overview = get_llm_metrics_helper().get_overview()

        return {
            "runtime": runtime_overview,
            "business": business_overview,
            "llm": llm_overview,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

    def _get_runtime_overview(self) -> dict[str, Any]:
        """获取运行时总览数据。"""
        event_stats = get_event_manager().get_event_stats()
        task_stats = get_task_manager().get_stats()
        scheduler_stats = get_unified_scheduler().get_statistics()

        adapter_manager = get_adapter_manager()
        active_adapters = getattr(adapter_manager, "_active_adapters", {})

        return {
            "event": event_stats,
            "task": task_stats,
            "scheduler": {
                "is_running": scheduler_stats.get("is_running", False),
                "uptime_seconds": scheduler_stats.get("uptime_seconds", 0.0),
                "total_tasks": scheduler_stats.get("total_tasks", 0),
                "running_tasks": scheduler_stats.get("running_tasks", 0),
                "success_rate": scheduler_stats.get("success_rate", 0.0),
            },
            "adapter": {
                "active_count": len(active_adapters),
                "active_signatures": list(active_adapters.keys()),
            },
        }

    async def _get_business_overview(self) -> dict[str, Any]:
        """获取业务核心总览数据。"""
        day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()

        today_total = await QueryBuilder(Messages).filter(time__gte=day_start).count()
        today_inbound = await QueryBuilder(Messages).filter(time__gte=day_start, person_id__isnull=False).count()
        today_outbound = await QueryBuilder(Messages).filter(time__gte=day_start, person_id__isnull=True).count()

        stream_manager = get_stream_manager()
        active_streams = len(getattr(stream_manager, "_streams", {}))

        plugin_manager = get_plugin_manager()
        loaded_plugins = getattr(plugin_manager, "_loaded_plugins", {})
        failed_plugins = getattr(plugin_manager, "_failed_plugins", {})

        registry = get_global_registry()
        components_by_type = {
            component_type.value: len(registry.get_by_type(component_type))
            for component_type in ComponentType
        }

        return {
            "messages": {
                "today_total": int(today_total),
                "today_inbound": int(today_inbound),
                "today_outbound": int(today_outbound),
                "today_start_timestamp": day_start,
            },
            "streams": {
                "active_count": active_streams,
            },
            "plugins": {
                "loaded_count": len(loaded_plugins),
                "failed_count": len(failed_plugins),
            },
            "components": {
                "total_count": len(registry),
                "by_type": components_by_type,
            },
        }


_dashboard_manager: DashboardManager | None = None


def get_dashboard_manager() -> DashboardManager:
    """获取仪表盘管理器单例。"""
    global _dashboard_manager
    if _dashboard_manager is None:
        _dashboard_manager = DashboardManager()
    return _dashboard_manager
