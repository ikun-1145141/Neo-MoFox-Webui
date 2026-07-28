"""插件市场 API 数据模型。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CompatibilityStatus = Literal["compatible", "incompatible", "unknown"]
OperationKind = Literal["install", "uninstall"]
OperationStatus = Literal["queued", "running", "succeeded", "failed"]


class CompatibilityInfo(BaseModel):
    """插件版本与当前宿主的兼容性结果。"""

    status: CompatibilityStatus
    summary: str
    reasons: list[str] = Field(default_factory=list)


class MarketLocalState(BaseModel):
    """市场插件在本机的安装状态。"""

    installed: bool = False
    loaded: bool = False
    installed_version: str | None = None
    plugin_path: str | None = None
    has_config: bool = False
    update_available: bool = False
    can_uninstall: bool = False
    uninstall_reason: str | None = None
    dependent_plugins: list[str] = Field(default_factory=list)


class MarketPlugin(BaseModel):
    """市场插件摘要。"""

    model_config = ConfigDict(extra="ignore")

    plugin_id: str
    display_name: str
    summary: str = ""
    description: str = ""
    icon_url: str | None = None
    homepage: str | None = None
    repository_url: str | None = None
    license: str | None = None
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    status: str = "published"
    owner_login: str | None = None
    owner_display_name: str | None = None
    owner_avatar_url: str | None = None
    maintainers: list[str] = Field(default_factory=list)
    trust_level: str = "community"
    risk_notice: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    likes_count: int = 0
    rating_avg: float = 0
    rating_count: int = 0
    comments_count: int = 0
    downloads_count: int = 0
    latest_version: str | None = None
    latest_version_published_at: str | None = None
    local_state: MarketLocalState = Field(default_factory=MarketLocalState)


class MarketVersion(BaseModel):
    """市场插件版本。"""

    model_config = ConfigDict(extra="ignore")

    plugin_id: str
    version: str
    release_tag: str | None = None
    release_title: str | None = None
    release_url: str | None = None
    asset_name: str
    asset_download_url: str
    checksum_sha256: str
    file_size: int | None = None
    published_at: str | None = None
    is_prerelease: bool = False
    is_yanked: bool = False
    status: str = "published"
    plugin_api_version: str | None = None
    min_host_version: str | None = None
    max_host_version: str | None = None
    supported_platforms: list[str] = Field(default_factory=list)
    download_count: int = 0
    compatibility: CompatibilityInfo = Field(
        default_factory=lambda: CompatibilityInfo(
            status="unknown",
            summary="兼容性信息不足",
        )
    )


class MarketDependency(BaseModel):
    """市场声明的插件依赖。"""

    model_config = ConfigDict(extra="ignore")

    plugin_id: str
    version_constraint: str | None = None
    required_version: str | None = None
    exists_in_market: bool = False
    installed: bool = False
    installed_version: str | None = None
    satisfied: bool = False


class MarketPluginList(BaseModel):
    """市场列表响应数据。"""

    plugins: list[MarketPlugin]
    total: int
    refreshed_at: str


class MarketPluginDetail(BaseModel):
    """市场插件详情响应数据。"""

    plugin: MarketPlugin
    versions: list[MarketVersion]
    dependencies: list[MarketDependency]
    recommended_version: MarketVersion | None = None


class MarketCapabilities(BaseModel):
    """插件市场能力开关。"""

    market_enabled: bool
    install_enabled: bool
    uninstall_enabled: bool
    supports_streaming_progress: bool = False


class InstallPlanRequest(BaseModel):
    """安装计划请求。"""

    version: str | None = Field(default=None, max_length=64)


class InstallPlan(BaseModel):
    """安装前展示并确认的计划。"""

    plugin: MarketPlugin
    version: MarketVersion
    dependencies: list[MarketDependency]
    action: Literal["install", "update"]
    can_install: bool
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class StartInstallRequest(BaseModel):
    """创建安装任务请求。"""

    version: str | None = Field(default=None, max_length=64)


class MarketOperationResult(BaseModel):
    """市场写操作结果。"""

    plugin_id: str
    version: str | None = None
    restart_required: bool = True


class MarketOperation(BaseModel):
    """可轮询的插件市场写操作。"""

    operation_id: str
    plugin_id: str
    kind: OperationKind
    status: OperationStatus
    stage: str
    progress: int = Field(ge=0, le=100)
    message: str
    created_at: str
    updated_at: str
    error_message: str | None = None
    result: MarketOperationResult | None = None


class UpstreamPluginList(BaseModel):
    """官方市场列表原始响应。"""

    items: list[MarketPlugin] = Field(default_factory=list)
    total: int = 0


class UpstreamVersionList(BaseModel):
    """官方市场版本列表原始响应。"""

    items: list[MarketVersion] = Field(default_factory=list)
    total: int = 0


class UpstreamDependencyList(BaseModel):
    """官方市场依赖列表原始响应。"""

    plugin_id: str
    items: list[MarketDependency] = Field(default_factory=list)


class UpstreamInstallInfo(BaseModel):
    """官方市场推荐安装版本响应。"""

    plugin: MarketPlugin
    version: MarketVersion


__all__ = [
    "CompatibilityInfo",
    "InstallPlan",
    "InstallPlanRequest",
    "MarketCapabilities",
    "MarketDependency",
    "MarketLocalState",
    "MarketOperation",
    "MarketOperationResult",
    "MarketPlugin",
    "MarketPluginDetail",
    "MarketPluginList",
    "MarketVersion",
    "OperationKind",
    "StartInstallRequest",
    "UpstreamDependencyList",
    "UpstreamInstallInfo",
    "UpstreamPluginList",
    "UpstreamVersionList",
]
