"""Plugin market page and authenticated API integrated into WebUI."""

from __future__ import annotations

import asyncio
from collections import deque
from pathlib import Path
import time
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.api.config_api import get_config
from src.core.components.base.router import BaseRouter
from src.core.utils.security import VerifiedDep

from ...market_config import WebUIConfig
from ...managers.plugin_manager import get_plugin_management_manager
from ...managers.plugin_market_service import MarketError, PluginMarketService

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin

logger = get_logger("webui.plugin_market")

MARKET_API_VERSION = "1.0.17"
_RATE_WINDOW_SECONDS = 600.0


class InstallRequest(BaseModel):
    """Install the selected plugin version, or the latest version when omitted."""

    plugin_id: str = Field(min_length=1, max_length=128)
    version: str | None = Field(default=None, max_length=64)


class ResolveRequest(BaseModel):
    """Resolve a plugin to its latest installable version."""

    plugin_id: str = Field(min_length=1, max_length=128)


class PluginMarketRouter(BaseRouter):
    """Serve the standalone market UI and its installation API."""

    name = "plugin-market"
    description = "Standalone plugin market HTML page and installation API"
    custom_route_path = "/webui/plugin-market"
    cors_origins = None

    _ASSETS = {
        "app.js": "application/javascript; charset=utf-8",
        "style.css": "text/css; charset=utf-8",
    }

    def __init__(self, plugin: "BasePlugin") -> None:
        config = plugin.config
        if not isinstance(config, WebUIConfig):
            raise RuntimeError("WebUI plugin market configuration is unavailable")
        if not config.market.enabled:
            raise RuntimeError("WebUI plugin market is disabled")
        self._config = config
        self._market = PluginMarketService(config)
        self._plugin_manager = get_plugin_management_manager()
        self._ui_dir = Path(__file__).resolve().parents[2] / "static" / "plugin-market"
        self._install_lock = asyncio.Lock()
        self._install_attempts: deque[float] = deque()
        super().__init__(plugin)

    def register_endpoints(self) -> None:
        @self.app.get("/", include_in_schema=False)
        @self.app.get("/index.html", include_in_schema=False)
        async def market_page() -> FileResponse:
            return self._ui_file("index.html", "text/html; charset=utf-8")

        @self.app.get("/assets/{asset_name}", include_in_schema=False)
        async def market_asset(asset_name: str) -> FileResponse:
            media_type = self._ASSETS.get(asset_name)
            if media_type is None:
                return self._ui_file("missing", "text/plain")
            return self._ui_file(asset_name, media_type)

        @self.app.get("/api/health")
        async def health() -> dict[str, Any]:
            return self._ok(
                {
                    "status": "ok",
                    "mode": "integrated",
                    "version": MARKET_API_VERSION,
                    "install_enabled": self._config.install.enabled,
                }
            )

        @self.app.get("/api/plugins", dependencies=[VerifiedDep])
        async def list_plugins(
            query: str = Query(default="", max_length=128),
            refresh: bool = Query(default=False),
        ) -> dict[str, Any]:
            try:
                if refresh:
                    self._market.clear_index_cache()
                plugins = await asyncio.to_thread(self._market.get_index, query)
                local_plugins = {
                    item.plugin_name: item
                    for item in await self._plugin_manager.list_plugins()
                }
                for item in plugins:
                    local = local_plugins.get(item["plugin_id"])
                    item["installed"] = local is not None
                    item["is_loaded"] = bool(local and local.is_loaded)
                    item["has_config"] = bool(local and local.is_loaded and local.has_config)
                return self._ok(
                    {
                        "plugins": plugins,
                        "total": len(plugins),
                        "query": query,
                        "install_enabled": self._config.install.enabled,
                    }
                )
            except MarketError as error:
                return self._error(400, str(error))

        @self.app.get("/api/plugins/{plugin_id}", dependencies=[VerifiedDep])
        async def resolve_plugin(plugin_id: str) -> dict[str, Any]:
            try:
                return self._ok(self._market.resolve(plugin_id))
            except MarketError as error:
                return self._error(400, str(error))

        @self.app.post("/api/resolve", dependencies=[VerifiedDep])
        async def resolve_plugin_post(request: ResolveRequest) -> dict[str, Any]:
            try:
                return self._ok(self._market.resolve(request.plugin_id))
            except MarketError as error:
                return self._error(400, str(error))

        if self._config.install.enabled:
            self._register_install_endpoint()

    def _register_install_endpoint(self) -> None:
        @self.app.post("/api/install", dependencies=[VerifiedDep])
        async def install_plugin(
            payload: InstallRequest,
            request: Request,
        ) -> dict[str, Any]:
            client_ip = request.client.host if request.client else "unknown"
            self._check_install_rate_limit()
            if self._install_lock.locked():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="已有插件安装任务正在执行",
                )
            self._install_attempts.append(time.monotonic())

            async with self._install_lock:
                try:
                    local_plugin_names = {
                        item.plugin_name
                        for item in await self._plugin_manager.list_plugins()
                    }
                    if payload.plugin_id in local_plugin_names:
                        raise MarketError(
                            f"插件 {payload.plugin_id} 已安装，请使用插件配置或插件管理页面"
                        )
                    result = await self._market.install(payload.plugin_id, payload.version)
                    installed_version = result.get("version") or payload.version or "latest"
                    result["has_config"] = get_config(payload.plugin_id) is not None
                    logger.warning(
                        "市场安装完成: "
                        f"client={client_ip}, plugin={payload.plugin_id}, version={installed_version}, "
                        f"loaded={result.get('loaded', False)}"
                    )
                    return self._ok(result, "插件安装完成")
                except MarketError as error:
                    logger.warning(
                        f"市场安装被拒绝: client={client_ip}, plugin={payload.plugin_id}, error={error}"
                    )
                    return self._error(400, str(error))
                except Exception as error:
                    logger.error(
                        f"市场安装失败: client={client_ip}, plugin={payload.plugin_id}, error={error}",
                        exc_info=True,
                    )
                    return self._error(500, "插件安装失败，请查看服务端日志")

    def _check_install_rate_limit(self) -> None:
        now = time.monotonic()
        self._trim_timestamps(self._install_attempts, now)
        if len(self._install_attempts) >= self._config.install.max_installs_per_10_minutes:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="市场安装操作过于频繁，请稍后再试",
            )

    @staticmethod
    def _trim_timestamps(values: deque[float], now: float) -> None:
        while values and now - values[0] >= _RATE_WINDOW_SECONDS:
            values.popleft()

    def _ui_file(self, filename: str, media_type: str) -> FileResponse:
        path = self._ui_dir / filename
        if filename not in {"index.html", *self._ASSETS} or not path.is_file():
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="UI asset not found")
        return FileResponse(
            path,
            media_type=media_type,
            headers={"Cache-Control": "no-cache"},
        )

    @staticmethod
    def _ok(data: Any, message: str = "success") -> dict[str, Any]:
        return {"code": 200, "data": data, "message": message}

    @staticmethod
    def _error(code: int, message: str) -> dict[str, Any]:
        return {"code": code, "data": None, "message": message}
