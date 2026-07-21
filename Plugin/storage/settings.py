"""WebUI 全局设置存储。

管理 WebUI 的全局配置，包括主题、语言、自动更新等设置。
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from .base import BaseStorage


class ThemeSettings(BaseModel):
    """主题设置。

    Attributes:
        mode: 主题模式，可选 "light"、"dark"、"auto"
        primary_color: 主色调，HEX 颜色值
        has_wallpaper: 是否存在壁纸
        wallpaper_blur: 壁纸模糊强度，范围 0-20
        wallpaper_opacity: 壁纸遮罩透明度，范围 0-1
    """

    mode: str = Field(default="auto", description="主题模式")
    primary_color: str = Field(default="#0058bd", description="主色调")
    has_wallpaper: bool = Field(default=False, description="是否存在壁纸")
    wallpaper_blur: float = Field(default=0.0, ge=0.0, le=20.0, description="壁纸模糊强度")
    wallpaper_opacity: float = Field(default=0.5, ge=0.0, le=1.0, description="壁纸遮罩透明度")


class UISettings(BaseModel):
    """界面设置。

    Attributes:
        language: 界面语言，可选 "zh-CN"、"en-US"
        font_size: 字体大小，可选 "small"、"medium"、"large"
    """

    language: str = Field(default="zh-CN", description="界面语言")
    font_size: str = Field(default="medium", description="字体大小")


class SystemSettings(BaseModel):
    """系统设置。

    Attributes:
        auto_update: 是否自动更新
        check_update_on_startup: 启动时检查更新
    """

    auto_update: bool = Field(default=False, description="自动更新")
    check_update_on_startup: bool = Field(default=True, description="启动时检查更新")


class ConfigSettings(BaseModel):
    """配置编辑器设置。

    Attributes:
        auto_reload_after_save: 在 WebUI 保存配置后是否自动触发运行时热重载
    """

    auto_reload_after_save: bool = Field(
        default=True,
        description="保存配置后自动热重载到运行时",
    )


class WebuiSettings(BaseModel):
    """WebUI 全局设置模型。

    Attributes:
        theme: 主题设置
        ui: 界面设置
        system: 系统设置
        config: 配置编辑器设置
    """

    theme: ThemeSettings = Field(default_factory=ThemeSettings, description="主题设置")
    ui: UISettings = Field(default_factory=UISettings, description="界面设置")
    system: SystemSettings = Field(default_factory=SystemSettings, description="系统设置")
    config: ConfigSettings = Field(default_factory=ConfigSettings, description="配置编辑器设置")


class SettingsStorage(BaseStorage):
    """设置存储类。

    管理 WebUI 全局设置的读写。
    数据存储在 data/json_storage/WebUI_data/settings.json

    Examples:
        >>> storage = SettingsStorage()
        >>> settings = await storage.get_settings()
        >>> settings.theme.mode = "dark"
        >>> await storage.save_settings(settings)
    """

    def __init__(self) -> None:
        """初始化设置存储。"""
        super().__init__(data_key="settings")

    async def get_settings(self) -> WebuiSettings:
        """获取设置。

        Returns:
            设置对象，如果不存在则返回默认值

        Examples:
            >>> settings = await storage.get_settings()
            >>> print(settings.theme.mode)
        """
        data = await self.load()
        if data is None:
            # 不存在则返回默认设置
            return WebuiSettings()
        return WebuiSettings(**data)

    async def save_settings(self, settings: WebuiSettings) -> None:
        """保存设置。

        Args:
            settings: 设置对象

        Examples:
            >>> settings = WebuiSettings()
            >>> settings.theme.mode = "dark"
            >>> await storage.save_settings(settings)
        """
        await self.save(settings.model_dump())

    async def update_settings(self, updates: dict[str, Any]) -> WebuiSettings:
        """更新设置（部分更新）。

        Args:
            updates: 要更新的字段字典

        Returns:
            更新后的设置对象

        Examples:
            >>> settings = await storage.update_settings({
            ...     "theme": {"mode": "dark"}
            ... })
        """
        current = await self.get_settings()
        current_dict = current.model_dump()

        # 递归更新字典
        def deep_update(base: dict, updates: dict) -> dict:
            for key, value in updates.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    base[key] = deep_update(base[key], value)
                else:
                    base[key] = value
            return base

        updated_dict = deep_update(current_dict, updates)
        updated = WebuiSettings(**updated_dict)
        await self.save_settings(updated)
        return updated

    async def reset_settings(self) -> WebuiSettings:
        """重置设置为默认值。

        Returns:
            重置后的设置对象

        Examples:
            >>> settings = await storage.reset_settings()
        """
        default = WebuiSettings()
        await self.save_settings(default)
        return default
