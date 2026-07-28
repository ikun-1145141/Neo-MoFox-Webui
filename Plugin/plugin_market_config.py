"""Neo-MoFox WebUI 插件市场配置。"""

from __future__ import annotations

from typing import ClassVar

from src.app.plugin_system.base import (
    BaseConfig,
    Field,
    SectionBase,
    config_section,
)


class WebUIConfig(BaseConfig):
    """WebUI 插件配置。"""

    config_name: ClassVar[str] = "config"
    config_description: ClassVar[str] = "Neo-MoFox WebUI 配置"

    @config_section("plugin_market")
    class PluginMarketSection(SectionBase):
        """插件市场连接设置。"""

        enabled: bool = Field(
            default=True,
            description="是否启用插件市场浏览功能",
            label="启用插件市场",
            tag="plugin",
            input_type="switch",
        )
        base_url: str = Field(
            default="https://39.96.71.162",
            description="官方插件市场 API 基础地址",
            label="市场地址",
            tag="network",
            input_type="text",
        )
        request_timeout_seconds: int = Field(
            default=30,
            ge=5,
            le=120,
            description="访问市场和下载插件包的超时时间",
            label="请求超时",
            tag="network",
            input_type="number",
        )
        page_size: int = Field(
            default=50,
            ge=10,
            le=100,
            description="从市场分页读取插件时的单页数量",
            label="市场分页大小",
            tag="network",
            input_type="number",
        )
        cache_seconds: int = Field(
            default=30,
            ge=0,
            le=600,
            description="市场列表在 WebUI 后端的缓存时长",
            label="列表缓存秒数",
            tag="performance",
            input_type="number",
        )
        max_package_size_mb: int = Field(
            default=50,
            ge=1,
            le=500,
            description="允许安装的单个插件包最大体积",
            label="安装包大小上限",
            tag="security",
            input_type="number",
        )
        trust_env: bool = Field(
            default=False,
            description="市场请求是否使用系统代理环境变量",
            label="使用系统代理",
            tag="network",
            input_type="switch",
        )

    @config_section("plugin_market_operations")
    class PluginMarketOperationsSection(SectionBase):
        """插件市场写操作设置。"""

        install_enabled: bool = Field(
            default=True,
            description="是否允许通过 WebUI 下载并安装市场插件",
            label="允许安装插件",
            tag="security",
            input_type="switch",
        )
        uninstall_enabled: bool = Field(
            default=True,
            description="是否允许卸载位于插件目录根级的压缩包插件",
            label="允许卸载插件",
            tag="security",
            input_type="switch",
        )
        max_installs_per_10_minutes: int = Field(
            default=5,
            ge=1,
            le=20,
            description="十分钟内允许创建的安装任务数量",
            label="安装频率上限",
            tag="security",
            input_type="number",
        )

    plugin_market: PluginMarketSection = Field(default_factory=PluginMarketSection)
    plugin_market_operations: PluginMarketOperationsSection = Field(
        default_factory=PluginMarketOperationsSection
    )


__all__ = ["WebUIConfig"]
