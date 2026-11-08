"""插件 UI 页面注册服务。

提供给其他 Neo-MoFox 插件调用的 Service 接口，用于注册/卸载/查询插件 UI 页面。
其他插件通过 get_service("neo-mofox-webui:service:plugin_ui") 获取此服务实例。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from src.app.plugin_system.api.log_api import get_logger  # type: ignore
from src.app.plugin_system.api.plugin_api import get_plugin_path  # type: ignore
from src.core.components.base.service import BaseService  # type: ignore

from ...managers.plugin_ui_manager import get_plugin_ui_manager
from ...utils.plugin_ui.plugin_ui_types import (
    HTMLAssets,
    PageMode,
    PageRegistration,
    PageSchemaResponse,
    PageSummary,
    RegisteredPage,
)
from ...utils.plugin_ui.plugin_ui_validators import (
    AssetMissingError,
    AssetPathError,
    AssetSizeError,
    PluginUIValidators,
    XMLValidationError,
)

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin  # type: ignore

logger = get_logger("plugin_ui_service")


class PluginUIService(BaseService):
    """插件 UI 页面注册服务。

    暴露给其他 Neo-MoFox 插件的 Service 接口。
    签名为 neo-mofox-webui:service:plugin_ui。
    """

    name: str = "plugin_ui"
    description: str = "Neo-MoFox WebUI 插件页面注册服务"
    version: str = "1.0.0"

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化 Service。

        Args:
            plugin: 所属插件实例
        """
        super().__init__(plugin)
        self._manager = get_plugin_ui_manager()

    async def register_ui_page(
        self,
        *,
        plugin_name: str,
        page_id: str,
        title: str,
        mode: str,
        icon: str | None = None,
        description: str | None = None,
        order: int = 100,
        xml: str | None = None,
        assets: dict | None = None,
        mobile_xml: str | None = None,
        mobile_assets: dict | None = None,
        i18n_path: str | None = None,
    ) -> RegisteredPage:
        """注册一个插件 UI 页面。

        执行完整校验后注册到内存 Registry。同 key 视为更新。
        所有参数均为基本类型，外部插件无需导入任何 WebUI 内部类型。

        移动端强制与桌面端使用相同的渲染模式：
        - mode="xml" 时只能传 mobile_xml，不能传 mobile_assets
        - mode="html" 时只能传 mobile_assets，不能传 mobile_xml

        HTML 模式下，所有资源路径以「插件根目录」为基准——
        系统通过 plugin_name 调用插件系统 API（get_plugin_path）解析出
        插件根目录的绝对路径，再以此为基准对相对路径做路径穿越校验，
        确保资源不会跳出插件根目录树。

        i18n_path 同样以「插件根目录」为基准；XML 模式下若声明了 i18n_path，
        也会调用 _resolve_plugin_root 解析真实插件根目录（不再用占位值），
        以确保路径穿越校验有意义。

        Args:
            plugin_name: 调用方插件名称
            page_id: 同插件内唯一标识（小写字母、数字、连字符）
            title: 页面显示名
            mode: 渲染模式，"xml" 或 "html"（桌面端和移动端共用）
            icon: Material Symbols 图标名，可选
            description: 页面简介，可选
            order: 排序权重（升序），默认 100
            xml: XML 模式下的桌面端 XML 字符串
            assets: HTML 模式下的桌面端资源声明 dict，结构：
                {"entry_html": "path/to/index.html",
                 "styles": ["path/to/style.css"],
                 "scripts": ["path/to/main.js"],
                 "assets_dir": "path/to/assets"}
                 所有路径相对于「插件根目录」（由 plugin_name 解析）
            mobile_xml: XML 模式下的移动端 XML 字符串（可选，空则 fallback 到桌面端）
            mobile_assets: HTML 模式下的移动端资源声明 dict（可选，结构同 assets）
            i18n_path: i18n JSON 文件相对插件根目录的路径（可选）。
                文件结构为 {"zh-CN": {...}, "en-US": {...}}，每个 locale 下是嵌套 dict。
                前端注册时会自动在最外层包一层 {plugin_name: ...}，使插件 key 自动
                落入 <plugin_name>.<key> 命名空间，避免与 WebUI 内置 key 冲突。

        Returns:
            加工后的 RegisteredPage 实例

        Raises:
            ValueError: 参数校验失败（含 mode 非法、mode 与移动端参数不匹配、
                插件未加载/路径不可用、i18n JSON 解析或结构不合法等）
            XMLValidationError: XML 校验失败
            AssetPathError: 路径不合法/穿越
            AssetMissingError: 文件不存在
            AssetSizeError: 文件超大
        """
        # 校验 mode
        try:
            mode_enum = PageMode(mode)
        except ValueError:
            raise ValueError(
                f"mode 参数非法: '{mode}'，必须为 'xml' 或 'html'"
            )

        # 构造桌面端 assets
        assets_obj = HTMLAssets.model_validate(assets) if assets else None

        # 构造移动端 assets
        mobile_assets_obj = (
            HTMLAssets.model_validate(mobile_assets) if mobile_assets else None
        )

        # 构造 PageRegistration（内部 model_validator 会校验 mode 与字段一致性）
        metadata = PageRegistration(
            plugin_name=plugin_name,
            page_id=page_id,
            title=title,
            icon=icon,
            description=description,
            order=order,
            mode=mode_enum,
            xml=xml,
            assets=assets_obj,
            mobile_xml=mobile_xml,
            mobile_assets=mobile_assets_obj,
            i18n_path=i18n_path,
        )

        logger.debug(
            f"收到注册请求: {metadata.plugin_name}/{metadata.page_id}"
        )

        # 确定插件根目录
        # HTML 模式或声明了 i18n_path 时都需要真实 plugin_root 做路径穿越校验；
        # 纯 XML 模式且无 i18n 时不读取本地资源，可用占位值满足字段约束
        needs_plugin_root = (
            metadata.mode == PageMode.HTML or metadata.i18n_path is not None
        )
        if needs_plugin_root:
            plugin_root = self._resolve_plugin_root(metadata.plugin_name)
        else:
            plugin_root = Path.cwd().resolve()

        # 执行校验（HTML 模式下校验器会以 plugin_root 为基准做路径穿越检查）
        PluginUIValidators.validate(metadata, plugin_root)

        # 校验并加载 i18n bundle（若有）
        i18n_bundle = PluginUIValidators.validate_i18n(metadata, plugin_root)

        # 注册到 Manager
        page = await self._manager.register(metadata, plugin_root, i18n_bundle)
        logger.info(
            f"页面注册成功: {metadata.plugin_name}/{metadata.page_id} "
            f"(mode={metadata.mode.value}"
            f"{', i18n=yes' if i18n_bundle else ', i18n=no'})"
        )
        return page

    @staticmethod
    def _resolve_plugin_root(plugin_name: str) -> Path:
        """通过插件名查找插件根目录绝对路径。

        HTML 模式下所有资源相对路径均以此目录为基准。
        找不到插件时抛 ValueError，让注册流程提前失败。

        Args:
            plugin_name: 插件名称

        Returns:
            插件根目录的绝对路径

        Raises:
            ValueError: 插件未加载或路径不可用
        """
        raw_path = get_plugin_path(plugin_name)
        if not raw_path:
            raise ValueError(
                f"无法解析插件根目录：插件 '{plugin_name}' 未加载或未注册路径"
            )
        resolved = Path(raw_path).resolve()
        if not resolved.is_dir():
            raise ValueError(
                f"插件根目录不存在或不是目录: {raw_path} (插件: {plugin_name})"
            )
        return resolved

    async def unregister_ui_page(self, plugin_name: str, page_id: str) -> bool:
        """卸载单个插件 UI 页面。

        幂等操作：page 不存在时返回 False。

        Args:
            plugin_name: 插件名称
            page_id: 页面标识

        Returns:
            是否真的存在并被移除
        """
        result = await self._manager.unregister(plugin_name, page_id)
        if result:
            logger.info(f"页面卸载: {plugin_name}/{page_id}")
        return result

    async def unregister_plugin_pages(self, plugin_name: str) -> int:
        """批量卸载指定插件的所有 UI 页面。

        Args:
            plugin_name: 插件名称

        Returns:
            被清理的页面数量
        """
        count = await self._manager.unregister_all(plugin_name)
        if count > 0:
            logger.info(f"批量卸载: {plugin_name} ({count} pages)")
        return count

    async def list_pages(
        self, *, plugin_filter: str | None = None
    ) -> list[PageSummary]:
        """获取页面摘要列表。

        Args:
            plugin_filter: 可选的插件名过滤

        Returns:
            按 order 升序排列的 PageSummary 列表
        """
        return self._manager.list_pages(filter_plugin=plugin_filter)

    async def get_page_schema(
        self,
        plugin_name: str,
        page_id: str,
        variant: str = "desktop",
    ) -> PageSchemaResponse | None:
        """获取页面渲染 schema。

        Args:
            plugin_name: 插件名称
            page_id: 页面标识
            variant: 变体类型 (desktop/mobile)

        Returns:
            PageSchemaResponse 或 None（page 不存在 / mobile 缺失时）

        Raises:
            ValueError: variant 参数非法
        """
        if variant not in ("desktop", "mobile"):
            raise ValueError(f"variant 参数非法: '{variant}'，必须为 desktop 或 mobile")

        return self._manager.get_schema(plugin_name, page_id, variant)  # type: ignore[arg-type]
