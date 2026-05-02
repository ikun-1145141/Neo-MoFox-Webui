"""仪表盘数据聚合管理器。

负责聚合 WebUI 首页所需的运行总览、业务核心和 LLM 运营指标，
为 Router 提供统一读取入口。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from src.core.components.registry import get_global_registry  # type: ignore
from src.core.components.types import ComponentType  # type: ignore
from src.core.managers.adapter_manager import get_adapter_manager  # type: ignore
from src.core.managers.event_manager import get_event_manager  # type: ignore
from src.core.managers.plugin_manager import get_plugin_manager  # type: ignore
from src.core.managers.stream_manager import get_stream_manager  # type: ignore
from src.core.models.sql_alchemy import Messages  # type: ignore
from src.kernel.concurrency import get_task_manager  # type: ignore
from src.kernel.db.api.query import QueryBuilder  # type: ignore
from src.kernel.db.core.session import get_db_session  # type: ignore
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

    async def get_message_trend(self, days: int = 7) -> dict[str, Any]:
        """获取消息趋势数据。

        Args:
            days: 统计天数（默认7天）

        Returns:
            包含每日消息统计的字典
        """
        now = datetime.now()
        start_date = now - timedelta(days=days - 1)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

        # 获取所有消息数据
        messages = await QueryBuilder(Messages).filter(
            time__gte=start_date.timestamp()
        ).all(as_dict=True)

        # 按日期和平台分组统计
        daily_stats: dict[str, dict[str, int]] = {}
        platform_totals: dict[str, int] = {}

        for msg in messages:
            msg_date = datetime.fromtimestamp(msg["time"]).strftime("%Y-%m-%d")
            platform = msg.get("platform", "unknown")

            if msg_date not in daily_stats:
                daily_stats[msg_date] = {"total": 0, "inbound": 0, "outbound": 0}

            daily_stats[msg_date]["total"] += 1

            # 区分入站/出站消息（person_id 存在表示入站）
            if msg.get("person_id"):
                daily_stats[msg_date]["inbound"] += 1
            else:
                daily_stats[msg_date]["outbound"] += 1

            # 平台统计
            platform_totals[platform] = platform_totals.get(platform, 0) + 1

        # 填充缺失日期（确保所有日期都有数据）
        date_range = []
        for i in range(days):
            date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            date_range.append(date)
            if date not in daily_stats:
                daily_stats[date] = {"total": 0, "inbound": 0, "outbound": 0}

        # 计算统计指标
        total_messages = sum(day["total"] for day in daily_stats.values())
        avg_per_day = total_messages / days if days > 0 else 0

        # 计算增长率（与前一天比较）
        sorted_dates = sorted(date_range)
        growth_rate = 0.0
        if len(sorted_dates) >= 2:
            yesterday = daily_stats[sorted_dates[-2]]["total"]
            today = daily_stats[sorted_dates[-1]]["total"]
            if yesterday > 0:
                growth_rate = ((today - yesterday) / yesterday) * 100

        return {
            "date_range": date_range,
            "daily_stats": {date: daily_stats[date] for date in sorted_dates},
            "summary": {
                "total_messages": total_messages,
                "avg_per_day": round(avg_per_day, 2),
                "growth_rate": round(growth_rate, 2),
            },
            "platform_distribution": platform_totals,
        }

    async def get_platform_statistics(self) -> dict[str, Any]:
        """获取平台消息统计。

        Returns:
            包含各平台消息分布的字典
        """
        # 统计所有消息的平台分布
        async with get_db_session() as session:
            stmt = select(
                Messages.platform,
                func.count(Messages.id).label("count")
            ).group_by(Messages.platform)

            result = await session.execute(stmt)
            platform_counts = result.all()

        # 转换为字典格式
        platforms = []
        total = 0
        for row in platform_counts:
            platforms.append({
                "platform": row.platform or "unknown",
                "count": int(row.count),
            })
            total += int(row.count)

        # 计算百分比
        for platform in platforms:
            platform["percentage"] = round((platform["count"] / total * 100), 2) if total > 0 else 0

        # 按消息数排序
        platforms.sort(key=lambda x: x["count"], reverse=True)

        return {
            "platforms": platforms,
            "total": total,
        }


_dashboard_manager: DashboardManager | None = None


def get_dashboard_manager() -> DashboardManager:
    """获取仪表盘管理器单例。"""
    global _dashboard_manager
    if _dashboard_manager is None:
        _dashboard_manager = DashboardManager()
    return _dashboard_manager
