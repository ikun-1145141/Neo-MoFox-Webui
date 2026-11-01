"""配置管理器。

负责接收前端请求、校验数据、调用存储层进行读写操作。
"""

from __future__ import annotations

from typing import Any

from ..storage.settings import SettingsStorage, WebuiSettings


class ConfigManager:
    """配置管理器。

    管理 WebUI 设置的业务逻辑，作为前端 API 和存储层之间的桥梁。

    Attributes:
        settings_storage: 设置存储实例

    Examples:
        >>> manager = ConfigManager()
        >>> await manager.initialize()
        >>> settings = await manager.get_settings()
    """

    def __init__(self) -> None:
        """初始化配置管理器。"""
        self.settings_storage = SettingsStorage()
        self._initialized = False

    async def initialize(self) -> None:
        """初始化管理器。

        确保默认设置存在。
        """
        if self._initialized:
            return

        # 如果设置不存在，创建默认设置
        if not await self.settings_storage.exists():
            default_settings = WebuiSettings()
            await self.settings_storage.save_settings(default_settings)

        self._initialized = True

    async def get_settings(self) -> WebuiSettings:
        """获取当前设置。

        Returns:
            设置对象

        Examples:
            >>> settings = await manager.get_settings()
        """
        return await self.settings_storage.get_settings()

    async def update_settings(self, updates: dict[str, Any]) -> WebuiSettings:
        """更新设置。

        Args:
            updates: 要更新的字段字典

        Returns:
            更新后的设置对象

        Examples:
            >>> settings = await manager.update_settings({
            ...     "theme": {"mode": "dark"}
            ... })
        """
        return await self.settings_storage.update_settings(updates)

    async def replace_settings(self, settings: WebuiSettings) -> WebuiSettings:
        """完全替换设置。

        Args:
            settings: 新的设置对象

        Returns:
            保存后的设置对象

        Examples:
            >>> new_settings = WebuiSettings()
            >>> new_settings.theme.mode = "dark"
            >>> settings = await manager.replace_settings(new_settings)
        """
        await self.settings_storage.save_settings(settings)
        return settings

    async def reset_settings(self) -> WebuiSettings:
        """重置设置为默认值。

        Returns:
            重置后的设置对象

        Examples:
            >>> settings = await manager.reset_settings()
        """
        return await self.settings_storage.reset_settings()


# 全局单例
_config_manager: ConfigManager | None = None


def get_config_manager() -> ConfigManager:
    """获取配置管理器单例。

    Returns:
        配置管理器实例

    Examples:
        >>> manager = get_config_manager()
        >>> settings = await manager.get_settings()
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
