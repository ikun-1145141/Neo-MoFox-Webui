"""插件市场 API 数据模型。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# 对外 API 使用封闭字面量，避免前后端对状态字符串作不同解释。
CompatibilityStatus = Literal["compatible", "incompatible", "unknown"]
OperationKind = Literal["install", "uninstall"]
OperationStatus = Literal["queued", "running", "succeeded", "failed"]


class CompatibilityInfo(BaseModel):
    """插件版本与当前宿主的兼容性结果。"""

    status: CompatibilityStatus = Field(description="兼容、明确不兼容或信息不足")
    summary: str = Field(description="供界面展示的兼容性摘要")
    reasons: list[str] = Field(default_factory=list, description="兼容性判断依据或阻塞原因")


class MarketLocalState(BaseModel):
    """市场插件在本机的安装状态。"""

    installed: bool = Field(default=False, description="本机是否已发现该插件")
    loaded: bool = Field(default=False, description="插件是否已由当前 Neo-MoFox 进程加载")
    installed_version: str | None = Field(default=None, description="本机插件版本")
    plugin_path: str | None = Field(default=None, description="本机插件包或目录的绝对路径")
    has_config: bool = Field(default=False, description="已加载插件是否声明可管理配置")
    update_available: bool = Field(default=False, description="市场最新版本是否高于本机版本")
    can_uninstall: bool = Field(default=False, description="市场后端能否安全卸载或覆盖该插件")
    uninstall_reason: str | None = Field(default=None, description="不能由市场管理时的原因")
    dependent_plugins: list[str] = Field(
        default_factory=list,
        description="当前依赖该插件的本机插件标识",
    )


class MarketPlugin(BaseModel):
    """市场插件摘要；忽略上游新增字段以保持读取兼容。"""

    model_config = ConfigDict(extra="ignore")

    plugin_id: str = Field(description="市场中的插件唯一标识")
    display_name: str = Field(description="插件展示名称")
    summary: str = Field(default="", description="插件短摘要")
    description: str = Field(default="", description="插件完整介绍")
    icon_url: str | None = Field(default=None, description="插件图标地址")
    has_readme: bool = Field(default=False, description="市场是否提供渲染后的插件 README")
    homepage: str | None = Field(default=None, description="插件主页地址")
    repository_url: str | None = Field(default=None, description="插件源代码仓库地址")
    license: str | None = Field(default=None, description="插件许可证标识")
    categories: list[str] = Field(default_factory=list, description="插件分类")
    tags: list[str] = Field(default_factory=list, description="插件标签")
    status: str = Field(default="published", description="市场发布状态")
    owner_login: str | None = Field(default=None, description="市场所有者登录名")
    owner_display_name: str | None = Field(default=None, description="市场所有者展示名称")
    owner_avatar_url: str | None = Field(default=None, description="市场所有者头像地址")
    maintainers: list[str] = Field(default_factory=list, description="插件维护者列表")
    trust_level: str = Field(default="community", description="市场提供的信任级别")
    risk_notice: str | None = Field(default=None, description="安装前需要展示的风险提示")
    created_at: str | None = Field(default=None, description="市场记录创建时间")
    updated_at: str | None = Field(default=None, description="市场记录更新时间")
    likes_count: int = Field(default=0, description="点赞数量")
    rating_avg: float = Field(default=0, description="平均评分")
    rating_count: int = Field(default=0, description="评分数量")
    comments_count: int = Field(default=0, description="评论数量")
    downloads_count: int = Field(default=0, description="累计下载数量")
    latest_version: str | None = Field(default=None, description="市场最新版本号")
    latest_version_published_at: str | None = Field(
        default=None,
        description="最新版本发布时间",
    )
    local_state: MarketLocalState = Field(
        default_factory=MarketLocalState,
        description="由 WebUI 后端合并的本机状态",
    )


class MarketVersion(BaseModel):
    """市场插件版本；忽略上游新增字段以保持读取兼容。"""

    model_config = ConfigDict(extra="ignore")

    plugin_id: str = Field(description="所属插件唯一标识")
    version: str = Field(description="插件版本号")
    release_tag: str | None = Field(default=None, description="上游发布标签")
    release_title: str | None = Field(default=None, description="上游发布标题")
    release_url: str | None = Field(default=None, description="发布详情地址")
    asset_name: str = Field(description="插件包文件名")
    asset_download_url: str = Field(description="插件包 HTTPS 下载地址")
    checksum_sha256: str = Field(description="插件包预期 SHA-256")
    file_size: int | None = Field(default=None, description="插件包预期字节数")
    published_at: str | None = Field(default=None, description="版本发布时间")
    is_prerelease: bool = Field(default=False, description="是否为预发布版本")
    is_yanked: bool = Field(default=False, description="版本是否已撤回")
    status: str = Field(default="published", description="版本发布状态")
    plugin_api_version: str | None = Field(default=None, description="声明的插件 API 版本")
    min_host_version: str | None = Field(default=None, description="支持的最低 Neo-MoFox 版本")
    max_host_version: str | None = Field(default=None, description="支持的最高 Neo-MoFox 版本")
    supported_platforms: list[str] = Field(default_factory=list, description="支持的操作系统标识")
    download_count: int = Field(default=0, description="该版本下载数量")
    compatibility: CompatibilityInfo = Field(
        default_factory=lambda: CompatibilityInfo(
            status="unknown",
            summary="兼容性信息不足",
        ),
        description="WebUI 后端根据当前宿主计算的兼容性",
    )


class MarketDependency(BaseModel):
    """市场声明的插件依赖；忽略上游新增字段以保持读取兼容。"""

    model_config = ConfigDict(extra="ignore")

    plugin_id: str = Field(description="依赖插件唯一标识")
    version_constraint: str | None = Field(default=None, description="依赖版本约束")
    required_version: str | None = Field(default=None, description="上游兼容字段中的依赖版本")
    exists_in_market: bool = Field(default=False, description="依赖是否存在于市场")
    installed: bool = Field(default=False, description="依赖是否已安装到本机")
    installed_version: str | None = Field(default=None, description="本机依赖版本")
    satisfied: bool = Field(default=False, description="本机版本是否满足依赖约束")


class MarketPluginList(BaseModel):
    """市场列表响应数据。"""

    plugins: list[MarketPlugin] = Field(description="合并本机状态后的市场插件")
    total: int = Field(description="返回的插件总数")
    refreshed_at: str = Field(description="本次响应生成时间")


class MarketPluginDetail(BaseModel):
    """市场插件详情响应数据。"""

    plugin: MarketPlugin = Field(description="插件元数据和本机状态")
    versions: list[MarketVersion] = Field(description="经过兼容性判断的市场版本")
    dependencies: list[MarketDependency] = Field(description="合并本机状态后的插件依赖")
    recommended_version: MarketVersion | None = Field(
        default=None,
        description="当前宿主可优先安装的稳定版本",
    )


class MarketPluginReadme(BaseModel):
    """市场为插件详情页渲染的 README 文档。"""

    model_config = ConfigDict(extra="ignore")

    plugin_id: str = Field(description="文档所属插件唯一标识")
    exists: bool = Field(description="市场是否保存了该插件的 README")
    html: str | None = Field(default=None, description="由市场渲染的 README HTML")


class MarketCapabilities(BaseModel):
    """插件市场能力开关。"""

    market_enabled: bool = Field(description="是否允许浏览插件市场")
    install_enabled: bool = Field(description="是否允许创建安装或更新任务")
    uninstall_enabled: bool = Field(description="是否允许创建卸载任务")
    supports_streaming_progress: bool = Field(
        default=False,
        description="是否支持推送式进度；当前通过轮询读取",
    )


class InstallPlanRequest(BaseModel):
    """安装计划请求。"""

    version: str | None = Field(
        default=None,
        max_length=64,
        description="目标版本；不提供时由后端选择推荐版本",
    )


class InstallPlan(BaseModel):
    """安装前展示并确认的计划。"""

    plugin: MarketPlugin = Field(description="目标插件及本机状态")
    version: MarketVersion = Field(description="实际选择的目标版本")
    dependencies: list[MarketDependency] = Field(description="安装前检查的依赖状态")
    action: Literal["install", "update"] = Field(description="本次写操作类型")
    can_install: bool = Field(description="当前计划是否通过所有阻塞性检查")
    blocking_reasons: list[str] = Field(default_factory=list, description="禁止执行的原因")
    warnings: list[str] = Field(default_factory=list, description="需要用户确认的非阻塞风险")


class StartInstallRequest(BaseModel):
    """创建安装任务请求。"""

    version: str | None = Field(
        default=None,
        max_length=64,
        description="目标版本；不提供时由后端选择推荐版本",
    )


class MarketOperationResult(BaseModel):
    """市场写操作结果。"""

    plugin_id: str = Field(description="已处理的插件唯一标识")
    version: str | None = Field(default=None, description="安装或卸载涉及的插件版本")
    restart_required: bool = Field(default=True, description="是否需要重启 Neo-MoFox 后生效")


class MarketOperation(BaseModel):
    """可轮询的插件市场写操作。"""

    operation_id: str = Field(description="可用于轮询的操作唯一标识")
    plugin_id: str = Field(description="操作目标插件唯一标识")
    kind: OperationKind = Field(description="安装或卸载操作")
    status: OperationStatus = Field(description="操作生命周期状态")
    stage: str = Field(description="当前业务阶段")
    progress: int = Field(ge=0, le=100, description="当前百分比进度")
    message: str = Field(description="供界面展示的当前状态说明")
    created_at: str = Field(description="操作创建时间")
    updated_at: str = Field(description="操作最后更新时间")
    error_message: str | None = Field(default=None, description="失败时的错误说明")
    result: MarketOperationResult | None = Field(default=None, description="成功后的结构化结果")


class UpstreamPluginList(BaseModel):
    """官方市场列表原始响应。"""

    items: list[MarketPlugin] = Field(default_factory=list, description="当前分页插件")
    total: int = Field(default=0, description="市场插件总数")


class UpstreamVersionList(BaseModel):
    """官方市场版本列表原始响应。"""

    items: list[MarketVersion] = Field(default_factory=list, description="插件版本列表")
    total: int = Field(default=0, description="版本总数")


class UpstreamDependencyList(BaseModel):
    """官方市场依赖列表原始响应。"""

    plugin_id: str = Field(description="依赖信息所属插件")
    items: list[MarketDependency] = Field(default_factory=list, description="插件依赖列表")


class UpstreamInstallInfo(BaseModel):
    """官方市场推荐安装版本响应。"""

    plugin: MarketPlugin = Field(description="目标插件元数据")
    version: MarketVersion = Field(description="市场推荐的安装版本")


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
    "MarketPluginReadme",
    "MarketVersion",
    "OperationKind",
    "StartInstallRequest",
    "UpstreamDependencyList",
    "UpstreamInstallInfo",
    "UpstreamPluginList",
    "UpstreamVersionList",
]
