"""仪表盘数据聚合管理器。

负责聚合 WebUI 首页所需的运行总览、业务核心和 LLM 运营指标，
为 Router 提供统一读取入口。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Date, case, cast, func, or_, select

from src.core.components.registry import get_global_registry  # type: ignore
from src.core.components.types import ComponentType  # type: ignore
from src.core.managers.adapter_manager import get_adapter_manager  # type: ignore
from src.core.managers.event_manager import get_event_manager  # type: ignore
from src.core.managers.plugin_manager import get_plugin_manager  # type: ignore
from src.core.managers.stream_manager import get_stream_manager  # type: ignore
from src.core.models.sql_alchemy import Messages  # type: ignore
from src.kernel.concurrency import get_task_manager  # type: ignore
from src.kernel.db.api.query import QueryBuilder  # type: ignore
from src.kernel.db.core.engine import get_configured_db_type  # type: ignore
from src.kernel.db.core.session import get_db_session  # type: ignore
from src.kernel.scheduler import get_unified_scheduler  # type: ignore

from ..utils import get_llm_metrics_helper


class DashboardManager:
    """仪表盘管理器。"""

    async def get_overview(self) -> dict[str, Any]:
        """获取首页总览数据。"""
        runtime_overview = self._get_runtime_overview()
        business_overview = await self._get_business_overview()
        llm_overview = await get_llm_metrics_helper().get_overview()

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

        async with get_db_session() as session:
            today_total_stmt = select(func.count(Messages.id)).where(
                Messages.time >= day_start,
            )
            today_inbound_stmt = select(func.count(Messages.id)).where(
                Messages.time >= day_start,
                Messages.person_id.isnot(None),
                Messages.person_id != "bot",
            )
            today_outbound_stmt = select(func.count(Messages.id)).where(
                Messages.time >= day_start,
                or_(Messages.person_id.is_(None), Messages.person_id == "bot"),
            )

            today_total = await session.scalar(today_total_stmt) or 0
            today_inbound = await session.scalar(today_inbound_stmt) or 0
            today_outbound = await session.scalar(today_outbound_stmt) or 0

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
        start_timestamp = start_date.timestamp()

        # 获取数据库类型以构建兼容的日期表达式
        db_type = get_configured_db_type()
        
        # 使用数据库聚合查询，避免加载所有数据到内存
        async with get_db_session() as session:
            # 按日期统计消息数（总数、入站、出站）
            # 使用 CASE WHEN 在数据库层面区分入站/出站
            # 根据数据库类型构建日期转换表达式
            if db_type == "postgresql":
                # PostgreSQL: to_char(to_timestamp(time), 'YYYY-MM-DD')
                date_expr = func.to_char(func.to_timestamp(Messages.time), 'YYYY-MM-DD')
            else:
                # SQLite: strftime('%Y-%m-%d', datetime(time, 'unixepoch'))
                date_expr = func.strftime('%Y-%m-%d', func.datetime(Messages.time, 'unixepoch'))
            
            stmt = select(
                date_expr.label('date'),
                func.count(Messages.id).label('total'),
                func.sum(case(
                    (
                        Messages.person_id.isnot(None) & (Messages.person_id != "bot"),
                        1,
                    ),
                    else_=0,
                )).label('inbound'),
                func.sum(case(
                    (
                        or_(Messages.person_id.is_(None), Messages.person_id == "bot"),
                        1,
                    ),
                    else_=0,
                )).label('outbound'),
            ).where(
                Messages.time >= start_timestamp
            ).group_by('date')
            
            result = await session.execute(stmt)
            daily_rows = result.all()
            
            # 按平台统计
            platform_stmt = select(
                Messages.platform,
                func.count(Messages.id).label('count')
            ).where(
                Messages.time >= start_timestamp
            ).group_by(Messages.platform)
            
            platform_result = await session.execute(platform_stmt)
            platform_rows = platform_result.all()

        # 构建每日统计字典
        daily_stats: dict[str, dict[str, int]] = {}
        for row in daily_rows:
            daily_stats[row.date] = {
                "total": int(row.total),
                "inbound": int(row.inbound),
                "outbound": int(row.outbound),
            }

        # 构建平台统计字典
        platform_totals: dict[str, int] = {}
        for row in platform_rows:
            platform_totals[row.platform or "unknown"] = int(row.count)

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
        """获取平台消息统计（近30天）。

        Returns:
            包含各平台消息分布的字典
        """
        # 计算30天前的时间戳
        now = datetime.now()
        start_date = now - timedelta(days=30)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        start_timestamp = start_date.timestamp()
        
        # 统计近30天消息的平台分布
        async with get_db_session() as session:
            stmt = select(
                Messages.platform,
                func.count(Messages.id).label("count")
            ).where(
                Messages.time >= start_timestamp
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
