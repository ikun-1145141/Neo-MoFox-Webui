"""Plugin market configuration for Neo-MoFox WebUI."""

from __future__ import annotations

from typing import ClassVar

from src.core.components.base.config import BaseConfig, Field, SectionBase, config_section


class WebUIConfig(BaseConfig):
    """WebUI configuration, including plugin market policies."""

    name: ClassVar[str] = "config"
    description: ClassVar[str] = "Neo-MoFox WebUI 配置"
    config_name: ClassVar[str] = name
    config_description: ClassVar[str] = description

    @config_section("market")
    class MarketSection(SectionBase):
        """市场索引连接设置。"""

        enabled: bool = Field(
            default=True,
            description="是否启用插件市场页面与后端 API，修改后需重启 Neo-MoFox",
            label="启用插件市场",
            tag="security",
            input_type="switch",
            hint="关闭后不会注册市场 Router，直接访问页面或 API 也会返回 404",
        )
        # 市场列表 API。官方接口常分页（默认约 50 条/页），插件会自动翻页。
        index_url: str = Field(
            default="https://39.96.71.162/api/v1/plugins",
            description="插件市场列表 API 地址（支持分页，会自动拉全量）",
        )
        # 请求超时秒数
        request_timeout_seconds: int = Field(
            default=20,
            description="读取市场索引或下载安装包的超时时间（秒）",
        )
        # 单包大小上限 MiB
        max_package_size_mb: int = Field(
            default=50,
            description="允许下载的单个插件包最大体积（MiB）",
        )
        # 列表缓存秒数
        index_cache_seconds: int = Field(
            default=30,
            description="市场列表本地缓存秒数（0 表示不缓存）",
        )
        # 单页数量
        page_size: int = Field(
            default=50,
            description="拉取市场列表时的单页数量（会自动翻页直到取完）",
        )

    @config_section("install")
    class InstallSection(SectionBase):
        """本地安装策略。"""

        enabled: bool = Field(
            default=False,
            description="是否允许通过市场写入插件包，修改后需重启 Neo-MoFox",
            label="允许市场安装插件",
            tag="security",
            input_type="switch",
            hint="开启后仍需使用服务器生成的独立安装授权码",
        )
        # 是否允许覆盖已存在的 .mfp
        allow_overwrite: bool = Field(
            default=False,
            description="校验通过后是否允许覆盖已存在的插件安装包",
            label="允许覆盖插件包",
            tag="security",
            input_type="switch",
        )
        # 安装后是否立即加载
        auto_load_after_install: bool = Field(
            default=False,
            description="安装成功后是否立即尝试加载插件",
            label="安装后立即加载",
            tag="security",
            input_type="switch",
        )
        max_installs_per_10_minutes: int = Field(
            default=5,
            ge=1,
            le=20,
            description="十分钟内允许完成的市场安装次数上限",
            label="安装频率上限",
            tag="security",
            input_type="number",
        )

    market: MarketSection = Field(default_factory=MarketSection)
    install: InstallSection = Field(default_factory=InstallSection)
