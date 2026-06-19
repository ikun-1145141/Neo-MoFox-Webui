"""插件 UI 页面注册服务。

提供给其他 Neo-MoFox 插件调用的 Service 接口，用于注册/卸载/查询插件 UI 页面。
其他插件通过 get_service("neo-mofox-webui:service:plugin_ui") 获取此服务实例。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from src.app.plugin_system.api.log_api import get_logger  # type: ignore
from src.core.components.base.service import BaseService  # type: ignore

from ...managers.plugin_ui_manager import get_plugin_ui_manager
from ...utils.plugin_ui.plugin_ui_types import (
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

    service_name: str = "plugin_ui"
    service_description: str = "Neo-MoFox WebUI 插件页面注册服务"
    version: str = "1.0.0"

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化 Service。

        Args:
            plugin: 所属插件实例
        """
        super().__init__(plugin)
        self._manager = get_plugin_ui_manager()

    async def register_ui_page(self, metadata: PageRegistration) -> RegisteredPage:
        """注册一个插件 UI 页面。

        执行完整校验后注册到内存 Registry。同 key 视为更新。

        Args:
            metadata: 页面注册元数据

        Returns:
            加工后的 RegisteredPage 实例

        Raises:
            ValueError: 模型校验失败
            XMLValidationError: XML 校验失败
            AssetPathError: 路径不合法/穿越
            AssetMissingError: 文件不存在
            AssetSizeError: 文件超大
        """
        logger.debug(
            f"收到注册请求: {metadata.plugin_name}/{metadata.page_id}"
        )

        # 执行校验
        PluginUIValidators.validate(metadata)

        # 确定插件根目录（使用 CWD 作为基准）
        plugin_root = Path.cwd().resolve()

        # 注册到 Manager
        page = await self._manager.register(metadata, plugin_root)
        logger.info(
            f"页面注册成功: {metadata.plugin_name}/{metadata.page_id} "
            f"(mode={metadata.mode.value})"
        )
        return page

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
