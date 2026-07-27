"""Market index retrieval and safe local plugin installation."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import shutil
import socket
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packaging.version import InvalidVersion, Version

from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.api.plugin_api import load_plugin

from ..market_config import WebUIConfig

logger = get_logger("webui.plugin_market")

_PLUGIN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class MarketError(RuntimeError):
    """市场索引或安装包校验失败。"""


@dataclass(frozen=True)
class PackageVersion:
    """标准化后的市场版本元数据。"""

    version: str
    asset_download_url: str
    checksum_sha256: str
    file_size: int | None
    min_host_version: str | None
    max_host_version: str | None


class PluginMarketService:
    """读取市场索引并安全安装插件包。"""

    def __init__(self, config: WebUIConfig) -> None:
        self._config = config
        self._index_cache: list[dict[str, Any]] | None = None
        self._index_cache_at: float = 0.0

    def get_index(self, query: str = "") -> list[dict[str, Any]]:
        """获取并标准化市场插件列表。

        官方市场常见返回：
        ``{"items": [...], "total": n, "page": 1, "page_size": 50}``

        本方法会自动翻页，直到拿完。也兼容：
        - ``{"plugins": [...]}``
        - 顶层数组
        """
        plugins = self._load_all_plugins()
        needle = query.strip().lower()
        if not needle:
            return plugins
        return [
            item
            for item in plugins
            if needle in item["plugin_id"].lower()
            or needle in item["display_name"].lower()
            or needle in item["summary"].lower()
            or needle in item["description"].lower()
            or any(needle in tag.lower() for tag in item["tags"])
            or any(needle in category.lower() for category in item["categories"])
        ]

    def clear_index_cache(self) -> None:
        """Force the next market read to fetch every page again."""
        self._index_cache = None
        self._index_cache_at = 0.0

    def resolve(self, plugin_id: str) -> dict[str, Any]:
        """解析单个插件及其最新可安装版本。"""
        plugin = self._find_plugin(plugin_id)
        latest_version = str(plugin.get("latest_version") or "").strip()
        if not latest_version:
            raise MarketError(f"插件 {plugin['plugin_id']} 没有可安装的最新版本")
        return {
            "plugin_id": plugin["plugin_id"],
            "display_name": plugin["display_name"],
            "summary": plugin["summary"],
            "latest_version": latest_version,
        }

    async def install(self, plugin_id: str, version: str | None = None) -> dict[str, Any]:
        """下载、校验并写入 plugins 目录。"""
        import asyncio

        result = await asyncio.to_thread(self._download_and_store, plugin_id, version)

        loaded = False
        load_error: str | None = None
        if self._config.install.auto_load_after_install:
            try:
                loaded = await load_plugin(result["install_path"])
            except Exception as error:
                load_error = str(error)
                logger.warning(f"安装后立即加载失败: {error}")

        result["loaded"] = loaded
        result["load_error"] = load_error
        return result

    def _download_and_store(self, plugin_id: str, version: str | None) -> dict[str, Any]:
        """在线程中完成下载、校验和原子写入。"""
        self._validate_plugin_id(plugin_id)
        plugin = self._find_plugin(plugin_id)
        selected_version = (version or "").strip() or str(plugin.get("latest_version") or "").strip()
        if not selected_version:
            raise MarketError(f"插件 {plugin['plugin_id']} 没有可安装的最新版本")
        selected = self._find_version(plugin, selected_version)
        package = self._download_package(selected)
        try:
            result = self._store_package(plugin["plugin_id"], package, selected)
        finally:
            package.unlink(missing_ok=True)

        return result

    def _load_all_plugins(self) -> list[dict[str, Any]]:
        cache_seconds = max(0, int(self._config.market.index_cache_seconds))
        now = time.time()
        if (
            cache_seconds > 0
            and self._index_cache is not None
            and (now - self._index_cache_at) < cache_seconds
        ):
            return list(self._index_cache)

        url = self._config.market.index_url.strip()
        if not url:
            raise MarketError("未配置市场索引地址，请先设置 config.toml 中的 market.index_url")

        items = self._fetch_all_index_items(url)
        normalized = [self._normalize_plugin(item) for item in items if isinstance(item, dict)]

        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for item in normalized:
            plugin_id = item["plugin_id"]
            if plugin_id in seen:
                continue
            seen.add(plugin_id)
            unique.append(item)

        self._index_cache = unique
        self._index_cache_at = now
        logger.info(f"已加载市场索引：{len(unique)} 个插件，来源 {url}")
        return list(unique)

    def _fetch_all_index_items(self, base_url: str) -> list[Any]:
        """读取第一页，并在存在分页时继续翻页。"""
        requested_page_size = max(1, int(self._config.market.page_size or 50))
        first_url = self._with_query(
            base_url,
            {
                "page": "1",
                "page_size": str(requested_page_size),
                "pageSize": str(requested_page_size),
                "limit": str(requested_page_size),
                "offset": "0",
                "per_page": str(requested_page_size),
            },
        )
        first_payload = self._download_json(first_url)
        first_items, total, reported_page_size = self._extract_page(first_payload)
        if not isinstance(first_items, list):
            # 兼容 index_url 已带查询参数且服务端不接受重复参数的情况
            first_payload = self._download_json(base_url)
            first_items, total, reported_page_size = self._extract_page(first_payload)
        if not isinstance(first_items, list):
            raise MarketError("市场索引格式无效：需要 plugins/items/results 数组或顶层数组")

        all_items: list[Any] = list(first_items)
        effective_page_size = (
            int(reported_page_size)
            if reported_page_size and reported_page_size > 0
            else len(first_items) or requested_page_size
        )

        # 没有 total 时，也继续翻页，直到某一页返回空或不足一页。
        page = 2
        request_count = 1
        max_pages = 200
        if total is not None and total > 0:
            max_pages = max(
                2,
                (int(total) + effective_page_size - 1) // effective_page_size + 2,
            )

        while page <= max_pages:
            if total is not None and len(all_items) >= int(total):
                break
            # The market currently caps a requested limit of 100 at 50. Advance
            # offset by the number actually received so entries are never skipped.
            offset = len(all_items)
            page_url = self._with_query(
                base_url,
                {
                    "page": str(page),
                    "page_size": str(requested_page_size),
                    "pageSize": str(requested_page_size),
                    "limit": str(requested_page_size),
                    "offset": str(offset),
                    "per_page": str(requested_page_size),
                },
            )
            payload = self._download_json(page_url)
            request_count += 1
            items, page_total, _ = self._extract_page(payload)
            if page_total is not None:
                total = int(page_total)
            if not isinstance(items, list) or not items:
                break
            # 防止服务端忽略分页参数时死循环
            new_ids = {
                str(item.get("plugin_id") or item.get("name") or "")
                for item in items
                if isinstance(item, dict)
            }
            old_ids = {
                str(item.get("plugin_id") or item.get("name") or "")
                for item in all_items
                if isinstance(item, dict)
            }
            if new_ids and new_ids.issubset(old_ids):
                logger.warning("市场分页返回重复数据，停止继续翻页")
                break
            all_items.extend(items)
            if total is not None and len(all_items) >= int(total):
                break
            if total is None and len(items) < effective_page_size:
                break
            page += 1

        logger.info(
            f"市场分页完成：获取 {len(all_items)}"
            + (f"/{total}" if total is not None else "")
            + f" 条，共请求 {request_count} 次"
        )
        return all_items

    @staticmethod
    def _extract_page(payload: Any) -> tuple[list[Any] | None, int | None, int | None]:
        if isinstance(payload, list):
            return payload, None, None
        if not isinstance(payload, dict):
            return None, None, None

        # 兼容 {code, data:{items,total}} / {data:[...]} 等包裹
        data = payload.get("data")
        if isinstance(data, list):
            return data, None, None
        if isinstance(data, dict):
            payload = data

        items = payload.get("items", payload.get("plugins", payload.get("results")))
        total_raw = payload.get("total", payload.get("count", payload.get("total_count")))
        page_size_raw = payload.get(
            "page_size",
            payload.get("pageSize", payload.get("limit", payload.get("per_page"))),
        )

        total: int | None = None
        if isinstance(total_raw, bool):
            total = None
        elif isinstance(total_raw, int | float):
            total = int(total_raw)
        elif isinstance(total_raw, str) and total_raw.strip().isdigit():
            total = int(total_raw.strip())

        page_size: int | None = None
        if isinstance(page_size_raw, bool):
            page_size = None
        elif isinstance(page_size_raw, int | float):
            page_size = int(page_size_raw)
        elif isinstance(page_size_raw, str) and page_size_raw.strip().isdigit():
            page_size = int(page_size_raw.strip())

        if isinstance(items, list):
            return items, total, page_size
        return None, total, page_size

    @staticmethod
    def _with_query(url: str, params: dict[str, str]) -> str:
        parts = urllib.parse.urlsplit(url)
        query = dict(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))
        query.update(params)
        return urllib.parse.urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path,
                urllib.parse.urlencode(query),
                parts.fragment,
            )
        )

    def _download_json(self, url: str) -> Any:
        raw = self._request(url, self._config.market.max_package_size_mb * 1024 * 1024)
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise MarketError(f"市场索引不是有效 JSON: {error}") from error

    def _normalize_plugin(self, item: dict[str, Any]) -> dict[str, Any]:
        plugin_id = str(item.get("plugin_id") or item.get("name") or "").strip()
        if not plugin_id:
            raise MarketError("市场索引存在缺少 plugin_id/name 的插件条目")
        self._validate_plugin_id(plugin_id)
        versions = item.get("versions") or []
        if not isinstance(versions, list):
            versions = []
        if not versions and item.get("latest_version"):
            versions = [{"version": str(item["latest_version"])}]
        normalized_versions = [
            self._normalize_version(plugin_id, value, allow_summary=True)
            for value in versions
            if isinstance(value, dict)
        ]
        latest_version = self._latest_version(
            str(item.get("latest_version") or "").strip(),
            normalized_versions,
        )
        return {
            "plugin_id": plugin_id,
            "display_name": str(item.get("display_name") or plugin_id),
            "summary": str(item.get("summary") or item.get("description") or ""),
            "description": str(item.get("description") or item.get("summary") or ""),
            "icon_url": str(item.get("icon_url") or ""),
            "homepage": str(item.get("homepage") or ""),
            "repository_url": str(item.get("repository_url") or ""),
            "license": str(item.get("license") or ""),
            "categories": self._string_list(item.get("categories")),
            "tags": self._string_list(item.get("tags")),
            "owner_login": str(item.get("owner_login") or ""),
            "owner_display_name": str(item.get("owner_display_name") or ""),
            "trust_level": str(item.get("trust_level") or ""),
            "downloads_count": int(item.get("downloads_count") or 0),
            "likes_count": int(item.get("likes_count") or 0),
            "rating_avg": float(item.get("rating_avg") or 0),
            "latest_version": latest_version,
            "versions": normalized_versions,
        }

    @staticmethod
    def _latest_version(declared_latest: str, versions: list[dict[str, Any]]) -> str:
        if declared_latest:
            return declared_latest
        if not versions:
            return ""

        def sort_key(item: dict[str, Any]) -> tuple[int, Version | str]:
            value = str(item["version"])
            try:
                return (1, Version(value))
            except InvalidVersion:
                return (0, value)

        return str(max(versions, key=sort_key)["version"])

    def _normalize_version(
        self,
        plugin_id: str,
        item: dict[str, Any],
        *,
        allow_summary: bool = False,
    ) -> dict[str, Any]:
        version = str(item.get("version") or "").strip()
        url = str(item.get("asset_download_url") or item.get("download_url") or "").strip()
        checksum = str(item.get("checksum_sha256") or "").strip().lower()
        if not version:
            raise MarketError(f"插件 {plugin_id} 的版本元数据缺少 version")
        if not allow_summary and (
            not url
            or len(checksum) != 64
            or any(char not in "0123456789abcdef" for char in checksum)
        ):
            raise MarketError(
                f"插件 {plugin_id} 的版本元数据不完整：需要 version、asset_download_url 和 SHA-256"
            )
        size = item.get("file_size")
        return {
            "version": version,
            "asset_download_url": url,
            "checksum_sha256": checksum,
            "file_size": int(size) if isinstance(size, int | float) else None,
            "min_host_version": item.get("min_host_version"),
            "max_host_version": item.get("max_host_version"),
        }

    def _find_plugin(self, plugin_id: str) -> dict[str, Any]:
        for plugin in self.get_index():
            if plugin["plugin_id"] == plugin_id:
                return plugin
        raise MarketError(f"市场中未找到插件: {plugin_id}")

    def _find_version(self, plugin: dict[str, Any], version: str) -> PackageVersion:
        for item in plugin["versions"]:
            if item["version"] != version:
                continue
            if item["asset_download_url"] and item["checksum_sha256"]:
                return PackageVersion(**item)

        detail_url = self._build_official_version_url(plugin["plugin_id"], version)
        if detail_url is None:
            raise MarketError(
                f"插件 {plugin['plugin_id']} 的索引没有完整下载元数据，且无法推导版本详情接口"
            )
        payload = self._download_json(detail_url)
        if not isinstance(payload, dict):
            raise MarketError("市场版本详情格式无效")
        if isinstance(payload.get("data"), dict):
            payload = payload["data"]
        return PackageVersion(
            **self._normalize_version(plugin["plugin_id"], payload, allow_summary=False)
        )

    def _build_official_version_url(self, plugin_id: str, version: str) -> str | None:
        base = self._config.market.index_url.rstrip("/")
        # 去掉可能存在的 query
        base = base.split("?", 1)[0].rstrip("/")
        if not base.endswith("/plugins"):
            return None
        return (
            f"{base}/{urllib.parse.quote(plugin_id, safe='')}/versions/"
            f"{urllib.parse.quote(version, safe='')}"
        )

    def _download_package(self, package: PackageVersion) -> Path:
        package_url = package.asset_download_url.lower().split("?", 1)[0]
        if not package_url.endswith((".mfp", ".zip")):
            raise MarketError("当前安装器只接受 .mfp 或 .zip 插件包")
        max_bytes = self._config.market.max_package_size_mb * 1024 * 1024
        data = self._request(package.asset_download_url, max_bytes)
        digest = hashlib.sha256(data).hexdigest()
        if digest != package.checksum_sha256:
            raise MarketError("安装包 SHA-256 校验失败，文件未写入 plugins 目录")
        if package.file_size is not None and len(data) != package.file_size:
            raise MarketError("安装包大小与市场索引不一致，文件未写入 plugins 目录")
        temp = tempfile.NamedTemporaryFile(prefix="plugin-market-", suffix=".zip", delete=False)
        try:
            temp.write(data)
            return Path(temp.name)
        finally:
            temp.close()

    def _store_package(self, requested_id: str, archive_path: Path, package: PackageVersion) -> dict[str, Any]:
        self._validate_plugin_id(requested_id)
        plugins_dir = (Path.cwd() / "plugins").resolve()
        plugins_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path) as archive:
            self._validate_zip(
                archive,
                self._config.market.max_package_size_mb * 1024 * 1024,
            )
            manifest = self._read_archive_manifest(archive)

        manifest_name = str(manifest.get("name") or "")
        if manifest_name != requested_id:
            raise MarketError(
                f"安装包插件名不匹配：市场为 {requested_id}，包内为 {manifest_name or '空'}"
            )
        if str(manifest.get("version") or "") != package.version:
            raise MarketError("安装包版本与市场索引不匹配")

        destination = (plugins_dir / f"{requested_id}.mfp").resolve()
        if destination.parent != plugins_dir:
            raise MarketError("插件安装路径无效")
        existing_directory = plugins_dir / requested_id
        existing_archives = [plugins_dir / f"{requested_id}.zip", destination]
        if existing_directory.exists():
            raise MarketError(f"插件目录 {requested_id} 已存在，市场安装器不会自动删除目录版插件")
        if any(path.exists() for path in existing_archives) and not self._config.install.allow_overwrite:
            raise MarketError(f"插件 {requested_id} 已存在。请先卸载，或显式开启 allow_overwrite。")

        temporary = plugins_dir / f".{requested_id}.mfp.download"
        shutil.copyfile(archive_path, temporary)
        try:
            for existing in existing_archives:
                if existing != destination and existing.exists():
                    existing.unlink()
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

        return {
            "plugin_name": requested_id,
            "version": package.version,
            "install_path": str(destination),
            "loaded": False,
            "load_error": None,
        }

    @staticmethod
    def _validate_zip(archive: zipfile.ZipFile, max_uncompressed_bytes: int) -> None:
        entries = archive.infolist()
        if not entries:
            raise MarketError("插件压缩包为空")
        total_uncompressed = 0
        for entry in entries:
            path = Path(entry.filename.replace("\\", "/"))
            if path.is_absolute() or ".." in path.parts:
                raise MarketError("插件压缩包包含非法路径")
            if entry.is_dir():
                continue
            total_uncompressed += entry.file_size
            if total_uncompressed > max_uncompressed_bytes:
                raise MarketError("插件压缩包解压后的内容超过配置的大小限制")
            mode = entry.external_attr >> 16
            if mode and (mode & 0o170000) == 0o120000:
                raise MarketError("插件压缩包不能包含符号链接")

    @staticmethod
    def _read_archive_manifest(archive: zipfile.ZipFile) -> dict[str, Any]:
        manifest_paths = [
            entry.filename.replace("\\", "/").rstrip("/")
            for entry in archive.infolist()
            if not entry.is_dir()
            and entry.filename.replace("\\", "/").rstrip("/").endswith("manifest.json")
            and len(entry.filename.replace("\\", "/").rstrip("/").split("/")) <= 2
        ]
        if len(manifest_paths) != 1:
            raise MarketError("插件包必须包含唯一的根级或一级目录 manifest.json")
        try:
            manifest = json.loads(archive.read(manifest_paths[0]).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError) as error:
            raise MarketError(f"无法读取插件 manifest.json: {error}") from error
        if not isinstance(manifest, dict):
            raise MarketError("插件 manifest.json 必须是 JSON 对象")
        entry_point = str(manifest.get("entry_point") or "plugin.py")
        manifest_parent = manifest_paths[0].rsplit("/", 1)[0] if "/" in manifest_paths[0] else ""
        entry_path = f"{manifest_parent}/{entry_point}".lstrip("/")
        if entry_path not in archive.namelist():
            raise MarketError("插件入口文件不存在")
        return manifest

    def _request(self, url: str, max_bytes: int) -> bytes:
        self._validate_remote_url(url)
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Neo-MoFox-WebUI-Plugin-Market/1.0.17"},
        )
        timeout = max(1, self._config.market.request_timeout_seconds)
        try:
            opener = urllib.request.build_opener(_SafeRedirectHandler(self._validate_remote_url))
            with opener.open(request, timeout=timeout) as response:
                self._validate_remote_url(response.geturl())
                length = response.headers.get("Content-Length")
                if length and int(length) > max_bytes:
                    raise MarketError("下载文件超过配置的大小限制")
                chunks: list[bytes] = []
                total = 0
                while True:
                    chunk = response.read(1024 * 64)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise MarketError("下载文件超过配置的大小限制")
                    chunks.append(chunk)
                return b"".join(chunks)
        except urllib.error.URLError as error:
            raise MarketError(f"无法访问市场服务: {error.reason}") from error

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        return [str(item) for item in value] if isinstance(value, list) else []

    @staticmethod
    def _validate_plugin_id(plugin_id: str) -> None:
        if not _PLUGIN_ID_PATTERN.fullmatch(plugin_id):
            raise MarketError(f"插件 ID 格式无效: {plugin_id}")

    @staticmethod
    def _validate_remote_url(url: str) -> None:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            raise MarketError("市场只允许访问 HTTPS 公网地址")
        try:
            addresses = {
                item[4][0]
                for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
            }
        except OSError as error:
            raise MarketError(f"无法解析市场地址: {error}") from error
        if not addresses:
            raise MarketError("市场地址未解析到有效 IP")
        for address in addresses:
            try:
                if not ipaddress.ip_address(address).is_global:
                    raise MarketError("市场地址不能指向本机、局域网或保留网络")
            except ValueError as error:
                raise MarketError("市场地址解析结果无效") from error


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Validate every redirect target before urllib follows it."""

    def __init__(self, validator: Any) -> None:
        super().__init__()
        self._validator = validator

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        self._validator(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)
