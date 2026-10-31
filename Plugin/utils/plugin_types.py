"""插件管理数据模型。

定义插件管理 API 使用的所有数据模型。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class PluginComponentInfo(BaseModel):
    """插件组件信息。

    Attributes:
        signature: 组件签名（plugin_name:component_type:component_name）
        component_type: 组件类型
        component_name: 组件名称
        description: 组件描述
        status: 组件状态（active/inactive/error）
        extra: 组件类型特有的扩展属性
    """

    signature: str = Field(..., description="组件签名（plugin:type:name）")
    component_type: str = Field(..., description="组件类型")
    component_name: str = Field(..., description="组件名称")
    description: str = Field(default="", description="组件描述")
    status: Literal["active", "inactive", "error"] = Field(default="active", description="组件状态")
    extra: dict[str, Any] | None = Field(default=None, description="组件类型特有的扩展属性")


class PluginSummary(BaseModel):
    """插件摘要信息（列表展示）。

    Attributes:
        plugin_name: 插件名称
        plugin_description: 插件描述
        plugin_version: 版本号
        is_loaded: 是否已加载
        has_config: 是否有配置文件
        component_count: 组件总数
        component_types: 包含的组件类型列表
        plugin_path: 插件路径（可选，未加载插件会包含）
    """

    plugin_name: str = Field(..., description="插件名称")
    plugin_description: str = Field(default="", description="插件描述")
    plugin_version: str = Field(default="1.0.0", description="版本号")
    is_loaded: bool = Field(..., description="是否已加载")
    has_config: bool = Field(default=False, description="是否有配置文件")
    component_count: int = Field(default=0, description="组件总数")
    component_types: list[str] = Field(default_factory=list, description="包含的组件类型列表")
    plugin_path: str | None = Field(default=None, description="插件路径（未加载插件会包含）")


class PluginDetail(PluginSummary):
    """插件详细信息（详情展示）。

    Attributes:
        manifest: 插件清单（原始数据）
        components: 组件列表
        dependencies: 依赖的组件签名列表
    
    Note:
        plugin_path 继承自 PluginSummary，在详情中应始终存在
    """

    manifest: dict[str, Any] = Field(..., description="插件清单（原始数据）")
    components: list[PluginComponentInfo] = Field(default_factory=list, description="组件列表")
    dependencies: list[str] = Field(default_factory=list, description="依赖的组件签名列表")


class PluginReloadResult(BaseModel):
    """插件重载结果。

    Attributes:
        success: 是否成功
        plugin_name: 插件名称
        reload_time: 重载时间（ISO 8601 格式）
        error_message: 错误信息
    """

    success: bool = Field(..., description="是否成功")
    plugin_name: str = Field(..., description="插件名称")
    reload_time: str = Field(..., description="重载时间（ISO 8601 格式）")
    error_message: str | None = Field(default=None, description="错误信息")


class PluginLoadResult(BaseModel):
    """插件加载结果。

    Attributes:
        success: 是否成功
        plugin_name: 插件名称
        plugin_path: 插件路径
        load_time: 加载时间（ISO 8601 格式）
        error_message: 错误信息
    """

    success: bool = Field(..., description="是否成功")
    plugin_name: str = Field(..., description="插件名称")
    plugin_path: str = Field(..., description="插件路径")
    load_time: str = Field(..., description="加载时间（ISO 8601 格式）")
    error_message: str | None = Field(default=None, description="错误信息")


class PluginUnloadResult(BaseModel):
    """插件卸载结果。

    Attributes:
        success: 是否成功
        plugin_name: 插件名称
        unload_time: 卸载时间（ISO 8601 格式）
        error_message: 错误信息
    """

    success: bool = Field(..., description="是否成功")
    plugin_name: str = Field(..., description="插件名称")
    unload_time: str = Field(..., description="卸载时间（ISO 8601 格式）")
    error_message: str | None = Field(default=None, description="错误信息")


class PluginImportResult(BaseModel):
    """插件包导入结果。

    Attributes:
        success: 是否导入成功（conflict 为 True 时表示需要用户确认覆盖）
        conflict: 是否检测到同名插件，等待用户确认是否覆盖
        plugin_name: 插件名称（取自包内 manifest）
        plugin_version: 插件版本
        plugin_path: 落盘后的插件包路径（冲突或失败时为空）
        existing_version: 已存在的同名插件版本
        existing_loaded: 已存在的同名插件当前是否正在运行
        dependents: 依赖该插件的已加载插件列表
        replaced: 是否覆盖了已存在的插件包
        loaded: 是否已完成热加载
        restart_required: 是否需要重启 Neo-MoFox 才能生效
        warnings: 不阻断导入的提示信息
        import_time: 导入时间（ISO 8601 格式）
        error_message: 错误信息或热加载失败原因
    """

    success: bool = Field(..., description="是否导入成功")
    conflict: bool = Field(default=False, description="是否检测到同名插件待用户确认")
    plugin_name: str = Field(..., description="插件名称")
    plugin_version: str = Field(default="", description="插件版本")
    plugin_path: str | None = Field(default=None, description="落盘后的插件包路径")
    existing_version: str | None = Field(default=None, description="已存在的同名插件版本")
    existing_loaded: bool = Field(default=False, description="已存在的同名插件是否正在运行")
    dependents: list[str] = Field(default_factory=list, description="依赖该插件的已加载插件列表")
    replaced: bool = Field(default=False, description="是否覆盖了已存在的插件包")
    loaded: bool = Field(default=False, description="是否已完成热加载")
    restart_required: bool = Field(default=False, description="是否需要重启 Neo-MoFox 才能生效")
    warnings: list[str] = Field(default_factory=list, description="不阻断导入的提示信息")
    import_time: str = Field(..., description="导入时间（ISO 8601 格式）")
    error_message: str | None = Field(default=None, description="错误信息")


__all__ = [
    "PluginComponentInfo",
    "PluginSummary",
    "PluginDetail",
    "PluginReloadResult",
    "PluginLoadResult",
    "PluginUnloadResult",
    "PluginImportResult",
]
