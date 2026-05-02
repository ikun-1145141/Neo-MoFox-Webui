"""Wallpaper Router 组件。

提供壁纸上传、删除、状态查询和图片读取接口。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.app.plugin_system.api.log_api import get_logger
from src.core.components.base.router import BaseRouter
from src.core.utils.security import VerifiedDep

from ...managers.config_manager import get_config_manager
from ...managers.wallpaper_manager import get_wallpaper_manager
from ...utils.response import BaseResponse

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin

logger = get_logger("wallpaper_router")

MAX_WALLPAPER_SIZE_BYTES = 10 * 1024 * 1024
SUPPORTED_WALLPAPER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class WallpaperStatus(BaseModel):
    """壁纸状态响应模型。"""

    has_wallpaper: bool = Field(description="是否存在壁纸")
    wallpaper_blur: float = Field(description="壁纸模糊强度")
    wallpaper_opacity: float = Field(description="壁纸遮罩透明度")


class WallpaperRouter(BaseRouter):
    """壁纸 Router 组件。"""

    router_name: str = "wallpaper"
    router_description: str = "WebUI 壁纸 API"
    custom_route_path: str = "/api/wallpaper"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化壁纸 Router。"""
        super().__init__(plugin)
        self.config_manager = get_config_manager()
        self.wallpaper_manager = get_wallpaper_manager()

    async def _build_wallpaper_status(self) -> WallpaperStatus:
        """构建壁纸状态。"""
        settings = await self.config_manager.get_settings()
        has_wallpaper = await self.wallpaper_manager.has_wallpaper()

        if settings.theme.has_wallpaper != has_wallpaper:
            settings = await self.config_manager.update_settings(
                {"theme": {"has_wallpaper": has_wallpaper}}
            )

        return WallpaperStatus(
            has_wallpaper=has_wallpaper,
            wallpaper_blur=settings.theme.wallpaper_blur,
            wallpaper_opacity=settings.theme.wallpaper_opacity,
        )

    def register_endpoints(self) -> None:
        """注册壁纸 API 端点。"""

        @self.app.post("/upload", response_model=BaseResponse[WallpaperStatus], dependencies=[VerifiedDep])
        async def upload_wallpaper(file: UploadFile = File(...)) -> BaseResponse[WallpaperStatus]:
            """上传单张壁纸。"""
            try:
                filename = (file.filename or "").strip()
                extension = f".{filename.split('.')[-1].lower()}" if "." in filename else ""
                if extension not in SUPPORTED_WALLPAPER_EXTENSIONS:
                    raise HTTPException(status_code=400, detail="仅支持 jpg/jpeg/png/webp 格式")

                content = await file.read()
                if not content:
                    raise HTTPException(status_code=400, detail="上传文件不能为空")
                if len(content) > MAX_WALLPAPER_SIZE_BYTES:
                    raise HTTPException(status_code=400, detail="壁纸文件大小不能超过 10MB")

                await self.wallpaper_manager.save_wallpaper(content=content, extension=extension)
                await self.config_manager.update_settings({"theme": {"has_wallpaper": True}})

                status = await self._build_wallpaper_status()
                return BaseResponse.ok(data=status, message="壁纸上传成功")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"上传壁纸失败: {e}")
                raise HTTPException(status_code=500, detail=f"上传壁纸失败: {str(e)}")

        @self.app.delete("/delete", response_model=BaseResponse[WallpaperStatus], dependencies=[VerifiedDep])
        async def delete_wallpaper() -> BaseResponse[WallpaperStatus]:
            """删除当前壁纸。"""
            try:
                await self.wallpaper_manager.delete_wallpaper()
                await self.config_manager.update_settings({"theme": {"has_wallpaper": False}})
                status = await self._build_wallpaper_status()
                return BaseResponse.ok(data=status, message="壁纸删除成功")
            except Exception as e:
                logger.error(f"删除壁纸失败: {e}")
                raise HTTPException(status_code=500, detail=f"删除壁纸失败: {str(e)}")

        @self.app.get("/status", response_model=BaseResponse[WallpaperStatus], dependencies=[VerifiedDep])
        async def get_wallpaper_status() -> BaseResponse[WallpaperStatus]:
            """获取当前壁纸状态。"""
            try:
                status = await self._build_wallpaper_status()
                return BaseResponse.ok(data=status, message="获取壁纸状态成功")
            except Exception as e:
                logger.error(f"获取壁纸状态失败: {e}")
                raise HTTPException(status_code=500, detail=f"获取壁纸状态失败: {str(e)}")

        @self.app.get("/image")
        async def get_wallpaper_image() -> FileResponse:
            """获取当前壁纸图片文件。"""
            current = await self.wallpaper_manager.get_wallpaper_path()
            if current is None:
                raise HTTPException(status_code=404, detail="当前没有壁纸")
            return FileResponse(path=current, filename=current.name)

    async def startup(self) -> None:
        """Router 启动钩子。"""
        await self.config_manager.initialize()
        await self.wallpaper_manager.initialize()
        logger.info("Wallpaper Router 已启动")

    async def shutdown(self) -> None:
        """Router 关闭钩子。"""
        logger.info("Wallpaper Router 已关闭")
