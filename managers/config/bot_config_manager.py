"""机器人配置管理器。

提供机器人配置专属操作（如热重载）。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from src.app.plugin_system.api.log_api import get_logger
from src.core.config.core_config import init_core_config

logger = get_logger("bot_config_manager")


class BotConfigManager:
    """机器人配置管理器。

    提供机器人配置的专属操作。
    读写操作委托给 MainConfigManager。
    """

    def __init__(self) -> None:
        """初始化管理器。"""
        self.config_path = Path("config/core.toml")

    async def reload_config(self) -> None:
        """热重载机器人配置。

        通过重新调用 ``init_core_config`` 触发 CoreConfig 重新从文件加载，
        并重跑所有副作用（旧字段迁移、LLM policy 注入），同时更新全局单例。

        Note:
            目前仅完成"重新读盘 + 同步副作用 + 替换全局单例"，
            已缓存旧实例的组件不会自动刷新引用，需要重启或主动重新获取。
        """
        try:
            # init_core_config 会覆盖 _global_config 单例，并重跑迁移 + LLM policy 注入
            # 放到线程中执行避免阻塞事件循环（其内部为同步文件 I/O）
            await asyncio.to_thread(init_core_config, str(self.config_path))
            logger.info("机器人配置已热重载")
        except Exception as e:
            logger.error(f"热重载配置失败: {e}")
            raise ValueError(f"热重载配置失败: {e}")


# ===== 单例模式 =====

_bot_config_manager: BotConfigManager | None = None


def get_bot_config_manager() -> BotConfigManager:
    """获取机器人配置管理器单例。

    Returns:
        机器人配置管理器实例
    """
    global _bot_config_manager
    if _bot_config_manager is None:
        _bot_config_manager = BotConfigManager()
    return _bot_config_manager
