"""插件市场管理器。

负责对接远端 Neo-MoFox Plugin Market API，并完成插件下载、安装、更新与版本切换。
"""

from __future__ import annotations

import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.api.plugin_api import (
    get_manifest,
    get_plugin_path,
    is_plugin_loaded,
    list_loaded_plugins,
    list_unloaded_plugins,
    load_plugin,
    unload_plugin,
)

from ..utils.market_types import (
    InstalledMarketPlugin,
    InstalledPluginListResponse,
    MarketPlugin,
    MarketPluginListResponse,
    MarketPluginQuery,
    MarketPluginReadmeResponse,
    MarketPluginVersion,
    MarketPluginVersionListResponse,
    PluginInstallRequest,
    PluginInstallResult,
    PluginMarketSettings,
    PluginVersionSwitchRequest,
)

logger = get_logger("plugin_market_manager")


class PluginMarketManager:
    """插件市场业务管理器。"""

    def __init__(self) -> None:
        """初始化插件市场管理器。"""

        self.settings = PluginMarketSettings()

    async def list_market_plugins(self, query: MarketPluginQuery) -> MarketPluginListResponse:
        """分页获取市场插件。

        Args:
            query: 市场插件查询参数。

        Returns:
            市场插件分页响应。
        """

        params = query.model_dump(exclude_none=True)
        payload = await self._market_get("/api/v1/plugins", params=params)
        return MarketPluginListResponse.model_validate(payload)

    async def get_market_plugin(self, plugin_id: str) -> MarketPlugin:
        """获取市场插件详情。

        Args:
            plugin_id: 插件 ID。

        Returns:
            市场插件详情。
        """

        payload = await self._market_get(f"/api/v1/plugins/{plugin_id}")
        return MarketPlugin.model_validate(payload)

    async def get_plugin_readme(self, plugin_id: str) -> MarketPluginReadmeResponse:
        """获取市场插件 README。

        Args:
            plugin_id: 插件 ID。

        Returns:
            插件 README 响应。
        """

        payload = await self._market_get(f"/api/v1/plugins/{plugin_id}/readme")
        return MarketPluginReadmeResponse.model_validate(payload)

    async def list_plugin_versions(self, plugin_id: str) -> MarketPluginVersionListResponse:
        """获取插件版本列表。

        Args:
            plugin_id: 插件 ID。

        Returns:
            插件版本列表。
        """

        payload = await self._market_get(f"/api/v1/plugins/{plugin_id}/versions")
        return MarketPluginVersionListResponse.model_validate(payload)

    async def get_plugin_version(self, plugin_id: str, version: str) -> MarketPluginVersion:
        """获取指定插件版本。

        Args:
            plugin_id: 插件 ID。
            version: 版本号。

        Returns:
            插件版本记录。
        """

        payload = await self._market_get(f"/api/v1/plugins/{plugin_id}/versions/{version}")
        return MarketPluginVersion.model_validate(payload)

    async def list_installed_plugins(self) -> InstalledPluginListResponse:
        """从核心插件管理器获取本机已安装插件列表。

        Returns:
            本机已安装插件列表。
        """

        items: list[InstalledMarketPlugin] = []
        loaded_names = set(list_loaded_plugins())
        unloaded_plugins = await list_unloaded_plugins()
        all_names = sorted(loaded_names | set(unloaded_plugins.keys()))

        for plugin_id in all_names:
            item = await self._build_installed_plugin_item(plugin_id, plugin_id in loaded_names, unloaded_plugins)
            items.append(item)

        return InstalledPluginListResponse(items=items, total=len(items))

    async def install_plugin(self, plugin_id: str, request: PluginInstallRequest) -> PluginInstallResult:
        """安装市场插件。

        Args:
            plugin_id: 插件 ID。
            request: 安装请求。

        Returns:
            安装结果。
        """

        version = await self._resolve_install_version(plugin_id, request)
        return await self._install_plugin_version(plugin_id, version, force=request.force)

    async def update_plugin(self, plugin_id: str, request: PluginInstallRequest) -> PluginInstallResult:
        """更新市场插件到指定版本或推荐版本。

        Args:
            plugin_id: 插件 ID。
            request: 更新请求。

        Returns:
            更新结果。
        """

        merged_request = request.model_copy(update={"force": True})
        version = await self._resolve_install_version(plugin_id, merged_request)
        return await self._install_plugin_version(plugin_id, version, force=True)

    async def switch_plugin_version(
        self, plugin_id: str, request: PluginVersionSwitchRequest
    ) -> PluginInstallResult:
        """切换或降级插件版本。

        Args:
            plugin_id: 插件 ID。
            request: 版本切换请求。

        Returns:
            版本切换结果。
        """

        return await self._install_plugin_version(plugin_id, request.version, force=True)

    async def _build_installed_plugin_item(
        self,
        plugin_id: str,
        loaded: bool,
        unloaded_plugins: dict[str, dict[str, Any]],
    ) -> InstalledMarketPlugin:
        """构建本机已安装插件条目。

        Args:
            plugin_id: 插件 ID。
            loaded: 是否已加载。
            unloaded_plugins: 未加载插件元数据映射。

        Returns:
            已安装插件条目。
        """

        manifest = get_manifest(plugin_id) if loaded else None
        unloaded_info = unloaded_plugins.get(plugin_id, {})
        plugin_path = get_plugin_path(plugin_id) if loaded else unloaded_info.get("path", "")
        installed_version = getattr(manifest, "version", None) or unloaded_info.get("version", "")
        description = getattr(manifest, "description", None) or unloaded_info.get("description", "")

        market_plugin: MarketPlugin | None = None
        latest_version: str | None = None
        try:
            market_plugin = await self.get_market_plugin(plugin_id)
            latest_version = market_plugin.latest_version
        except Exception as exc:
            logger.debug(f"插件 {plugin_id} 未匹配到市场数据或市场不可用: {exc}")

        return InstalledMarketPlugin(
            plugin_id=plugin_id,
            display_name=(market_plugin.display_name if market_plugin else plugin_id),
            summary=description,
            installed_version=installed_version,
            latest_version=latest_version,
            plugin_path=str(plugin_path or ""),
            is_loaded=loaded,
            source="market" if market_plugin else "local",
            market=market_plugin,
        )

    async def _resolve_install_version(self, plugin_id: str, request: PluginInstallRequest) -> str:
        """解析目标安装版本。

        Args:
            plugin_id: 插件 ID。
            request: 安装请求。

        Returns:
            目标版本号。
        """

        if request.version:
            return request.version

        params = {
            "host_version": request.host_version,
            "plugin_api_version": request.plugin_api_version,
            "platform": request.platform,
        }
        payload = await self._market_get(
            f"/api/v1/plugins/{plugin_id}/recommended-version",
            params={key: value for key, value in params.items() if value is not None},
        )
        version = MarketPluginVersion.model_validate(payload)
        return version.version

    async def _install_plugin_version(self, plugin_id: str, version: str, force: bool) -> PluginInstallResult:
        """安装指定插件版本。

        Args:
            plugin_id: 插件 ID。
            version: 目标版本。
            force: 是否覆盖已有安装。

        Returns:
            安装结果。
        """

        current_path = self._find_existing_plugin_path(plugin_id)
        if current_path is not None and not force:
            current_version = self._get_local_plugin_version(plugin_id)
            if current_version == version:
                return PluginInstallResult(
                    success=True,
                    plugin_id=plugin_id,
                    version=version,
                    plugin_path=str(current_path),
                    loaded=is_plugin_loaded(plugin_id),
                    message="插件版本已安装，未重复安装",
                )
            raise FileExistsError(f"插件 {plugin_id} 已存在，请使用更新接口或启用 force")

        market_version = await self.get_plugin_version(plugin_id, version)
        downloaded_path = await self._download_plugin_asset(plugin_id, market_version)

        was_loaded = is_plugin_loaded(plugin_id)
        if was_loaded:
            unload_ok = await unload_plugin(plugin_id)
            if not unload_ok:
                raise RuntimeError(f"插件 {plugin_id} 正在运行，卸载失败，已取消安装")

        if current_path is not None:
            self._backup_existing_plugin(current_path)

        final_path = self._move_downloaded_plugin(plugin_id, downloaded_path)
        load_ok = await load_plugin(str(final_path))

        try:
            await self._market_post(f"/api/v1/plugins/{plugin_id}/install-record", params={"version": version})
        except Exception as exc:
            logger.warning(f"记录插件安装次数失败: {plugin_id}@{version}: {exc}")

        return PluginInstallResult(
            success=load_ok,
            plugin_id=plugin_id,
            version=version,
            plugin_path=str(final_path),
            loaded=load_ok,
            backup_path="",
            message="插件安装成功" if load_ok else "插件文件已安装，但加载失败，请检查日志",
        )

    async def _download_plugin_asset(self, plugin_id: str, version: MarketPluginVersion) -> Path:
        """下载插件资产文件，不做解压。

        Args:
            plugin_id: 插件 ID。
            version: 市场版本记录。

        Returns:
            临时下载文件路径。
        """

        plugins_dir = Path(self.settings.plugins_dir)
        plugins_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(version.asset_name).suffix or ".mfp"
        target_path = plugins_dir / f".{plugin_id}-{version.version}.download{suffix}"
        await self._download_file(version.asset_download_url, target_path)
        return target_path

    async def _download_file(self, url: str, target_path: Path) -> None:
        """下载远端文件。

        Args:
            url: 文件下载地址。
            target_path: 目标文件路径。
        """

        if not url:
            raise ValueError("插件版本缺少 asset_download_url，无法下载安装")

        async with httpx.AsyncClient(timeout=self.settings.request_timeout, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            target_path.write_bytes(response.content)

    def _find_existing_plugin_path(self, plugin_id: str) -> Path | None:
        """查找本机已有插件路径。

        Args:
            plugin_id: 插件 ID。

        Returns:
            插件路径；不存在时返回 None。
        """

        runtime_path = get_plugin_path(plugin_id)
        if runtime_path:
            return Path(runtime_path)

        plugins_dir = Path(self.settings.plugins_dir)
        candidates = [plugins_dir / plugin_id, plugins_dir / f"{plugin_id}.zip", plugins_dir / f"{plugin_id}.mfp"]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _get_local_plugin_version(self, plugin_id: str) -> str | None:
        """获取本机已加载插件版本。

        Args:
            plugin_id: 插件 ID。

        Returns:
            版本号；未加载或无 manifest 时返回 None。
        """

        manifest = get_manifest(plugin_id)
        return getattr(manifest, "version", None) if manifest is not None else None

    def _backup_existing_plugin(self, plugin_path: Path) -> Path:
        """备份已有插件。

        文件夹插件会压缩为 zip 后换备份后缀；插件文件或压缩包直接重命名为备份后缀。

        Args:
            plugin_path: 已有插件路径。

        Returns:
            备份路径。
        """

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        backup_path = plugin_path.with_name(f"{plugin_path.name}.{timestamp}.bak")
        if plugin_path.is_dir():
            zip_path = backup_path.with_suffix(f"{backup_path.suffix}.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for file_path in plugin_path.rglob("*"):
                    if file_path.is_file():
                        archive.write(file_path, file_path.relative_to(plugin_path.parent))
            shutil.rmtree(plugin_path)
            logger.info(f"已压缩备份插件文件夹: {zip_path}")
            return zip_path

        plugin_path.rename(backup_path)
        logger.info(f"已重命名备份插件文件: {backup_path}")
        return backup_path

    def _move_downloaded_plugin(self, plugin_id: str, downloaded_path: Path) -> Path:
        """移动下载完成的插件文件到插件目录。

        Args:
            plugin_id: 插件 ID。
            downloaded_path: 临时下载路径。

        Returns:
            最终插件文件路径。
        """

        target_suffix = downloaded_path.suffix if downloaded_path.suffix in {".zip", ".mfp"} else ".mfp"
        target_path = Path(self.settings.plugins_dir) / f"{plugin_id}{target_suffix}"
        if target_path.exists():
            self._backup_existing_plugin(target_path)
        downloaded_path.rename(target_path)
        return target_path

    async def _market_get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """请求市场 GET API。

        Args:
            path: API 路径。
            params: 查询参数。

        Returns:
            JSON 响应。
        """

        async with httpx.AsyncClient(base_url=str(self.settings.base_url), timeout=self.settings.request_timeout) as client:
            response = await client.get(path, params=params)
            response.raise_for_status()
            return response.json()

    async def _market_post(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """请求市场 POST API。

        Args:
            path: API 路径。
            params: 查询参数。

        Returns:
            JSON 响应。
        """

        async with httpx.AsyncClient(base_url=str(self.settings.base_url), timeout=self.settings.request_timeout) as client:
            response = await client.post(path, params=params)
            response.raise_for_status()
            return response.json()


_plugin_market_manager: PluginMarketManager | None = None


def get_plugin_market_manager() -> PluginMarketManager:
    """获取插件市场管理器单例。

    Returns:
        插件市场管理器实例。
    """

    global _plugin_market_manager
    if _plugin_market_manager is None:
        _plugin_market_manager = PluginMarketManager()
    return _plugin_market_manager


__all__ = ["PluginMarketManager", "get_plugin_market_manager"]
