"""插件市场数据模型。

定义 WebUI 插件市场后端接口的请求体、响应体以及市场 API 适配模型。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class MarketPlugin(BaseModel):
    """市场插件记录。"""

    plugin_id: str = Field(..., description="市场插件 ID，与 manifest.name 保持一致")
    display_name: str = Field(..., description="插件展示名称")
    summary: str = Field(default="", description="插件摘要")
    description: str = Field(default="", description="插件描述")
    icon_url: str | None = Field(default=None, description="插件图标 URL")
    has_readme: bool = Field(default=False, description="是否存在 README")
    homepage: str | None = Field(default=None, description="插件主页")
    repository_url: str = Field(default="", description="插件仓库地址")
    license: str = Field(default="", description="许可证")
    categories: list[str] = Field(default_factory=list, description="分类列表")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    status: Literal["draft", "pending_review", "published", "deprecated", "blocked", "archived"] = Field(
        default="published", description="市场发布状态"
    )
    owner_id: str = Field(default="", description="所有者 ID")
    owner_login: str | None = Field(default=None, description="所有者登录名")
    owner_display_name: str | None = Field(default=None, description="所有者展示名")
    owner_avatar_url: str | None = Field(default=None, description="所有者头像 URL")
    maintainers: list[str] = Field(default_factory=list, description="维护者列表")
    trust_level: Literal["official", "verified", "community"] = Field(default="community", description="信任等级")
    risk_notice: str | None = Field(default=None, description="风险提示")
    created_at: str = Field(default="", description="创建时间")
    updated_at: str = Field(default="", description="更新时间")
    likes_count: int = Field(default=0, description="点赞数")
    rating_avg: float = Field(default=0.0, description="平均评分")
    rating_count: int = Field(default=0, description="评分数量")
    comments_count: int = Field(default=0, description="评论数量")
    downloads_count: int = Field(default=0, description="下载数量")
    latest_version: str | None = Field(default=None, description="最新版本")
    latest_version_published_at: str | None = Field(default=None, description="最新版本发布时间")
    viewer_has_liked: bool = Field(default=False, description="当前用户是否点赞")
    viewer_rating: int | None = Field(default=None, description="当前用户评分")


class MarketPluginListResponse(BaseModel):
    """市场插件分页列表响应。"""

    items: list[MarketPlugin] = Field(default_factory=list, description="插件条目")
    total: int = Field(default=0, description="总数")


class MarketPluginReadmeResponse(BaseModel):
    """市场插件 README 响应。"""

    plugin_id: str = Field(..., description="插件 ID")
    exists: bool = Field(..., description="README 是否存在")
    html: str | None = Field(default=None, description="已渲染的 README HTML")


class MarketPluginVersion(BaseModel):
    """市场插件版本记录。"""

    plugin_id: str = Field(..., description="插件 ID")
    version: str = Field(..., description="版本号")
    release_tag: str = Field(default="", description="Release 标签")
    release_title: str = Field(default="", description="Release 标题")
    release_url: str = Field(default="", description="Release URL")
    asset_name: str = Field(default="", description="资产文件名")
    asset_download_url: str = Field(default="", description="资产下载地址")
    checksum_sha256: str = Field(default="", description="SHA256 校验值")
    file_size: int = Field(default=0, description="文件大小")
    published_at: str = Field(default="", description="发布时间")
    is_prerelease: bool = Field(default=False, description="是否为预发布")
    is_yanked: bool = Field(default=False, description="是否已撤回")
    status: Literal["submitted", "pending_review", "published", "yanked", "blocked"] = Field(
        default="published", description="版本状态"
    )
    plugin_api_version: str = Field(default="", description="插件 API 版本")
    min_host_version: str = Field(default="", description="最小宿主版本")
    max_host_version: str | None = Field(default=None, description="最大宿主版本")
    supported_platforms: list[str] = Field(default_factory=list, description="支持平台")
    last_sync_status: Literal["none", "success", "failed"] = Field(default="none", description="同步状态")
    last_sync_error: str | None = Field(default=None, description="同步错误")
    download_count: int = Field(default=0, description="下载次数")


class MarketPluginVersionListResponse(BaseModel):
    """市场插件版本列表响应。"""

    items: list[MarketPluginVersion] = Field(default_factory=list, description="版本条目")
    total: int = Field(default=0, description="总数")


class InstalledMarketPlugin(BaseModel):
    """本机已安装市场插件记录。"""

    plugin_id: str = Field(..., description="插件 ID")
    display_name: str = Field(default="", description="展示名称")
    summary: str = Field(default="", description="本机 manifest 描述或市场摘要")
    installed_version: str = Field(default="", description="已安装版本")
    latest_version: str | None = Field(default=None, description="市场最新版本")
    plugin_path: str = Field(default="", description="本地插件路径")
    is_loaded: bool = Field(default=False, description="当前是否已加载")
    source: Literal["market", "local"] = Field(default="local", description="来源")
    market: MarketPlugin | None = Field(default=None, description="市场插件摘要")


class InstalledPluginListResponse(BaseModel):
    """本机已安装插件列表响应。"""

    items: list[InstalledMarketPlugin] = Field(default_factory=list, description="已安装插件条目")
    total: int = Field(default=0, description="总数")


class PluginInstallRequest(BaseModel):
    """安装市场插件请求。"""

    version: str | None = Field(default=None, description="指定安装版本；为空时安装推荐版本")
    host_version: str | None = Field(default=None, description="宿主版本约束")
    plugin_api_version: str | None = Field(default=None, description="插件 API 版本约束")
    platform: str | None = Field(default=None, description="目标平台")
    force: bool = Field(default=False, description="是否覆盖已有安装")


class PluginVersionSwitchRequest(BaseModel):
    """切换市场插件版本请求。"""

    version: str = Field(..., min_length=1, description="目标版本")
    force: bool = Field(default=False, description="是否覆盖已有安装")


class PluginInstallResult(BaseModel):
    """插件安装或版本切换结果。"""

    success: bool = Field(..., description="是否成功")
    plugin_id: str = Field(..., description="插件 ID")
    version: str = Field(default="", description="目标版本")
    plugin_path: str = Field(default="", description="安装路径")
    loaded: bool = Field(default=False, description="安装后是否已加载")
    backup_path: str | None = Field(default=None, description="更新或降级前生成的备份路径")
    message: str = Field(default="", description="结果说明")


class PluginMarketSettings(BaseModel):
    """插件市场后端设置。"""

    base_url: HttpUrl | str = Field(default="https://plugin-market.mofox.dev", description="插件市场 API 根地址")
    request_timeout: float = Field(default=20.0, gt=0, description="市场 API 请求超时时间")
    plugins_dir: str = Field(default="plugins", description="本地插件安装目录")


class PluginMarketState(BaseModel):
    """插件市场本地持久化状态。"""

    settings: PluginMarketSettings = Field(default_factory=PluginMarketSettings, description="市场设置")
    installed: dict[str, InstalledMarketPlugin] = Field(default_factory=dict, description="已安装插件索引")


class MarketPluginQuery(BaseModel):
    """市场插件查询参数。"""

    q: str | None = Field(default=None, description="搜索关键字")
    status: str | None = Field(default=None, description="发布状态")
    category: str | None = Field(default=None, description="分类")
    tag: str | None = Field(default=None, description="标签")
    trust_level: str | None = Field(default=None, description="信任等级")
    sort: str = Field(default="updated", description="排序方式")
    offset: int = Field(default=0, ge=0, description="分页偏移")
    limit: int = Field(default=50, ge=1, le=100, description="分页大小")


def model_from_mapping(model_type: type[BaseModel], data: dict[str, Any]) -> BaseModel:
    """从字典构建 Pydantic 模型。

    Args:
        model_type: 目标模型类型。
        data: 原始字典。

    Returns:
        构建后的模型实例。
    """

    return model_type.model_validate(data)


__all__ = [
    "InstalledMarketPlugin",
    "InstalledPluginListResponse",
    "MarketPlugin",
    "MarketPluginListResponse",
    "MarketPluginQuery",
    "MarketPluginReadmeResponse",
    "MarketPluginVersion",
    "MarketPluginVersionListResponse",
    "PluginInstallRequest",
    "PluginInstallResult",
    "PluginMarketSettings",
    "PluginMarketState",
    "PluginVersionSwitchRequest",
    "model_from_mapping",
]
