"""机器人配置管理器。

提供机器人配置专属操作（如热重载）。
"""

from __future__ import annotations

from src.app.plugin_system.api.log_api import get_logger
from src.core.config.core_config import CoreConfig

logger = get_logger("bot_config_manager")


class BotConfigManager:
    """机器人配置管理器。

    提供机器人配置的专属操作。
    读写操作委托给 MainConfigManager。
    """

    async def reload_config(self) -> None:
        """热重载机器人配置。

        触发 CoreConfig 重新从文件加载，无需重启进程。

        Note:
            目前简单地重新加载配置类，未来可能需要通知相关组件应用新配置。
        """
        try:
            # 重新加载配置
            CoreConfig.load("config/core.toml", auto_update=True)
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
