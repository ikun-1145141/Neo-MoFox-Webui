"""插件 UI Asset Router。

提供静态资源服务，以索引形式定位文件，避免泄露插件本地目录布局。
仅支持 GET 请求，其他方法返回 405。
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import HTTPException
from fastapi.responses import FileResponse, Response

from src.app.plugin_system.api.log_api import get_logger  # type: ignore
from src.core.components.base.router import BaseRouter  # type: ignore
from src.core.utils.security import VerifiedDep  # type: ignore

from ....managers.plugin_ui_manager import get_plugin_ui_manager
from ....utils.plugin_ui.plugin_ui_constants import (
    ALLOWED_ASSET_EXTENSIONS,
    ASSET_CACHE_MAX_AGE,
    MAX_ASSET_SIZE_BYTES,
)
from ....utils.plugin_ui.plugin_ui_paths import (
    resolve_asset_in_dir,
    resolve_safe,
    validate_asset_extension,
    validate_asset_size,
)
from ....utils.plugin_ui.plugin_ui_types import PageMode

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin  # type: ignore

logger = get_logger("plugin_ui_asset_router")


class PluginUIAssetRouter(BaseRouter):
    """插件 UI 静态资源路由。

    以索引形式提供 HTML/CSS/JS 和静态资源文件服务。
    """

    router_name: str = "plugin-ui-asset"
    router_description: str = "插件 UI 静态资源服务"
    custom_route_path: str = "/webui/static/plugin-ui"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化 Asset Router。

        Args:
            plugin: 所属插件实例
        """
        super().__init__(plugin)
        self._manager = get_plugin_ui_manager()

    def register_endpoints(self) -> None:
        """注册 API 端点。"""

        @self.app.get(
            "/{plugin_name}/{page_id}/{variant}/entry",
            dependencies=[VerifiedDep],
            summary="获取 entry HTML",
            description="返回指定页面的入口 HTML 文件",
        )
        async def get_entry_html(
            plugin_name: str, page_id: str, variant: str
        ) -> Response:
            """获取 entry HTML 文件。"""
            page = self._manager.get_registered_page(plugin_name, page_id)
            if page is None:
                raise HTTPException(status_code=404, detail="page not found")

            assets = self._get_variant_assets(page, variant)
            if assets is None:
                raise HTTPException(
                    status_code=404, detail=f"no {variant} HTML assets"
                )

            return self._serve_file(assets.entry_html)

        @self.app.get(
            "/{plugin_name}/{page_id}/{variant}/style/{index:int}",
            dependencies=[VerifiedDep],
            summary="获取 CSS 文件",
            description="按索引返回指定页面的 CSS 文件",
        )
        async def get_style(
            plugin_name: str, page_id: str, variant: str, index: int
        ) -> Response:
            """获取 CSS 文件。"""
            page = self._manager.get_registered_page(plugin_name, page_id)
            if page is None:
                raise HTTPException(status_code=404, detail="page not found")

            assets = self._get_variant_assets(page, variant)
            if assets is None:
                raise HTTPException(
                    status_code=404, detail=f"no {variant} HTML assets"
                )

            if index < 0 or index >= len(assets.styles):
                raise HTTPException(
                    status_code=404, detail=f"style index {index} out of range"
                )

            return self._serve_file(assets.styles[index])

        @self.app.get(
            "/{plugin_name}/{page_id}/{variant}/script/{index:int}",
            dependencies=[VerifiedDep],
            summary="获取 JS 文件",
            description="按索引返回指定页面的 JS 文件",
        )
        async def get_script(
            plugin_name: str, page_id: str, variant: str, index: int
        ) -> Response:
            """获取 JS 文件。"""
            page = self._manager.get_registered_page(plugin_name, page_id)
            if page is None:
                raise HTTPException(status_code=404, detail="page not found")

            assets = self._get_variant_assets(page, variant)
            if assets is None:
                raise HTTPException(
                    status_code=404, detail=f"no {variant} HTML assets"
                )

            if index < 0 or index >= len(assets.scripts):
                raise HTTPException(
                    status_code=404, detail=f"script index {index} out of range"
                )

            return self._serve_file(assets.scripts[index])

        @self.app.get(
            "/{plugin_name}/{page_id}/{variant}/asset/{rel_path:path}",
            dependencies=[VerifiedDep],
            summary="获取静态资源文件",
            description="从 assets_dir 内返回指定相对路径的资源文件",
        )
        async def get_asset(
            plugin_name: str, page_id: str, variant: str, rel_path: str
        ) -> Response:
            """获取 assets_dir 内的静态资源文件。"""
            page = self._manager.get_registered_page(plugin_name, page_id)
            if page is None:
                raise HTTPException(status_code=404, detail="page not found")

            assets = self._get_variant_assets(page, variant)
            if assets is None:
                raise HTTPException(
                    status_code=404, detail=f"no {variant} HTML assets"
                )

            if not assets.assets_dir:
                raise HTTPException(
                    status_code=404, detail="assets_dir not declared"
                )

            # 解析 assets_dir 绝对路径
            assets_dir = Path(assets.assets_dir).resolve()
            cwd = Path.cwd().resolve()
            if not assets_dir.is_relative_to(cwd):
                raise HTTPException(status_code=403, detail="path traversal blocked")

            # 在 assets_dir 内安全解析子路径
            try:
                abs_path = resolve_asset_in_dir(assets_dir, rel_path)
            except PermissionError:
                logger.warning(
                    f"路径穿越尝试: {plugin_name}/{page_id}/{variant}/asset/{rel_path}"
                )
                raise HTTPException(status_code=403, detail="path traversal blocked")
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail="asset not found")

            # 运行时再校验扩展名和大小
            try:
                validate_asset_extension(abs_path)
                validate_asset_size(abs_path)
            except PermissionError as e:
                logger.warning(f"资源校验失败: {e}")
                raise HTTPException(status_code=403, detail=str(e))

            return self._build_file_response(abs_path)

    @staticmethod
    def _get_variant_assets(page, variant: str):
        """根据 variant 获取对应的 HTMLAssets。

        Args:
            page: RegisteredPage 实例
            variant: 变体类型（desktop/mobile）

        Returns:
            HTMLAssets 或 None
        """
        if variant == "desktop":
            if page.mode == PageMode.HTML:
                return page.assets
            return None
        elif variant == "mobile":
            if page.mode == PageMode.HTML and page.mobile_assets:
                return page.mobile_assets
            return None
        return None

    def _serve_file(self, rel_path: str) -> Response:
        """安全地提供文件响应。

        执行运行时路径穿越防御（双保险：注册时已校验一次）。

        Args:
            rel_path: 相对于 CWD 的文件路径

        Returns:
            FileResponse

        Raises:
            HTTPException: 文件不存在或路径穿越
        """
        try:
            abs_path = resolve_safe(rel_path)
        except PermissionError:
            logger.warning(f"路径穿越尝试: {rel_path}")
            raise HTTPException(status_code=403, detail="path traversal blocked")
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="asset not found")

        # 运行时再校验
        try:
            validate_asset_extension(abs_path)
            validate_asset_size(abs_path)
        except PermissionError as e:
            logger.warning(f"资源校验失败: {e}")
            raise HTTPException(status_code=403, detail=str(e))

        return self._build_file_response(abs_path)

    @staticmethod
    def _build_file_response(abs_path: Path) -> FileResponse:
        """构建带缓存头的 FileResponse。

        Args:
            abs_path: 文件绝对路径

        Returns:
            FileResponse 实例
        """
        # 推断 Content-Type
        content_type, _ = mimetypes.guess_type(str(abs_path))
        if content_type is None:
            content_type = "application/octet-stream"

        return FileResponse(
            path=str(abs_path),
            media_type=content_type,
            headers={
                "Cache-Control": f"public, max-age={ASSET_CACHE_MAX_AGE}",
            },
        )
