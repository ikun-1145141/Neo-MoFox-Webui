"""供应商模型枚举：只读取远程列表，不改动核心配置或密钥轮询状态。"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import aiohttp
from yarl import URL

from ...utils.config_types import RemoteModelListRequest, RemoteModelOption

REMOTE_MODEL_TIMEOUT = 15
MAX_MODEL_LIST_PAGES = 100
MAX_MODEL_LIST_PAGE_BYTES = 4 * 1024 * 1024


class RemoteModelListError(Exception):
    """可安全返回前端的错误；不携带上游正文、URL 或凭据。"""

    def __init__(self, message: str, code: int = 502) -> None:
        super().__init__(message)
        self.code = code


def _models_url(base_url: str, client_type: str) -> URL:
    """保留代理路径和已有版本段，仅补全模型枚举端点。"""
    try:
        parts = urlsplit(base_url.strip())
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or parts.fragment
        ):
            raise ValueError
        # 访问 port 属性同时校验端口是否合法。
        _ = parts.port
        path = parts.path.rstrip("/")
        if not path.endswith("/models"):
            if client_type == "anthropic" and not path.endswith("/v1"):
                path += "/v1"
            elif client_type == "gemini" and not re.search(
                r"/v[0-9]+(?:(?:beta|alpha)[0-9]*)?$", path
            ):
                path += "/v1beta"
            path += "/models"
        return URL(urlunsplit((parts.scheme, parts.netloc, path, parts.query, "")))
    except (ValueError, TypeError):
        raise RemoteModelListError(
            "供应商地址无效，请填写不含用户名、密码或片段的 HTTP/HTTPS 基础地址。", 400
        ) from None


def _request_headers(request: RemoteModelListRequest) -> dict[str, str]:
    """仅取首个非空密钥；不调用核心的轮询取钥函数。"""
    keys = [request.api_key] if isinstance(request.api_key, str) else request.api_key
    key = next((value.strip() for value in keys if value.strip()), "")
    if not key or any(ord(char) < 32 or ord(char) == 127 for char in key):
        raise RemoteModelListError("请先为供应商填写有效的 API 密钥。", 400)

    headers = {"Accept": "application/json"}
    if request.client_type == "openai":
        headers["Authorization"] = f"Bearer {key}"
    elif request.client_type == "anthropic":
        headers["x-api-key"] = key
        headers["anthropic-version"] = "2023-06-01"
    else:
        headers["x-goog-api-key"] = key
    return headers


def _check_status(status: int) -> None:
    """仅使用状态码生成错误，不透传可能含密钥的供应商响应正文。"""
    if 200 <= status < 300:
        return
    if status in {401, 403}:
        message = "供应商认证失败，请检查 API 密钥和模型列表访问权限。"
    elif status == 404:
        message = "供应商未提供此模型列表接口，请检查基础地址或手动输入模型 ID。"
    elif status == 429:
        message = "供应商请求过于频繁，请稍后重试或手动输入模型 ID。"
    elif 300 <= status < 400:
        message = "模型列表接口返回重定向，请直接配置最终供应商地址后重试。"
    else:
        message = f"获取模型列表失败，供应商返回 HTTP {status}。"
    raise RemoteModelListError(message)


async def _read_page(response: aiohttp.ClientResponse) -> dict[str, Any]:
    """限量读取 JSON 页面，也兼容未正确设置 Content-Type 的中转服务。"""
    _check_status(response.status)
    body = bytearray()
    async for chunk in response.content.iter_chunked(64 * 1024):
        body.extend(chunk)
        if len(body) > MAX_MODEL_LIST_PAGE_BYTES:
            raise RemoteModelListError("供应商返回的模型列表过大，请手动输入模型 ID。")
    try:
        data = json.loads(body)
    except (ValueError, UnicodeError):
        raise RemoteModelListError("供应商返回的模型列表不是有效的 JSON。") from None
    if not isinstance(data, dict) or "error" in data:
        raise RemoteModelListError("供应商返回了无法识别的模型列表。")
    return data


def _collect_options(
    items: list[Any], client_type: str, options: dict[str, RemoteModelOption]
) -> None:
    """忽略无效项、按实际 ID 去重；不根据名称推断价格或模型能力。"""
    for item in items:
        if not isinstance(item, dict):
            continue
        identifier = item.get("name" if client_type == "gemini" else "id")
        if not isinstance(identifier, str):
            continue
        identifier = identifier.strip()
        if client_type == "gemini":
            identifier = identifier.removeprefix("models/")
        if not identifier or identifier in options:
            continue
        label = item.get("displayName") if client_type == "gemini" else item.get("display_name")
        if not isinstance(label, str) or not label.strip():
            label = None
        else:
            label = label.strip()
        options[identifier] = RemoteModelOption(id=identifier, display_name=label)


async def fetch_remote_models(request: RemoteModelListRequest) -> list[RemoteModelOption]:
    """枚举当前供应商模型，完整分页共享 15 秒总时限。

    Args:
        request: 前端当前供应商配置快照，不要求已保存到 model.toml。
    Returns:
        去重、按 ID 排序的模型选项。
    Raises:
        RemoteModelListError: 参数、连接、上游协议或超时错误（文案已脱敏）。
    """
    url = _models_url(request.base_url, request.client_type)
    headers = _request_headers(request)
    params: dict[str, str | int] = {}
    if request.client_type == "anthropic":
        params["limit"] = 100
    elif request.client_type == "gemini":
        params["pageSize"] = 1000
    options: dict[str, RemoteModelOption] = {}
    seen_cursors: set[str] = set()

    try:
        async with asyncio.timeout(REMOTE_MODEL_TIMEOUT):
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=REMOTE_MODEL_TIMEOUT)
            ) as session:
                for _ in range(MAX_MODEL_LIST_PAGES):
                    # 分页只更新同一个地址的游标，绝不采用上游返回的 next URL。
                    async with session.get(
                        url.update_query(params), headers=headers, allow_redirects=False
                    ) as response:
                        data = await _read_page(response)

                    if request.client_type == "gemini":
                        items = data.get("models", [])
                    else:
                        items = data.get("data")
                    if not isinstance(items, list):
                        raise RemoteModelListError("供应商返回的模型列表格式不正确。")
                    _collect_options(items, request.client_type, options)

                    if request.client_type == "gemini":
                        cursor = data.get("nextPageToken")
                        cursor_key = "pageToken"
                    else:
                        has_more = data.get("has_more", False)
                        if not isinstance(has_more, bool):
                            raise RemoteModelListError("供应商返回的分页标记无效。")
                        if not has_more:
                            break
                        cursor = data.get("last_id")
                        if not cursor and items and isinstance(items[-1], dict):
                            cursor = items[-1].get("id")
                        if not cursor:
                            raise RemoteModelListError("供应商返回的模型列表缺少下一页游标。")
                        cursor_key = "after_id"
                    if cursor is None or cursor == "":
                        break
                    if not isinstance(cursor, str) or cursor in seen_cursors:
                        raise RemoteModelListError("供应商返回的模型列表分页无效或重复。")
                    seen_cursors.add(cursor)
                    params[cursor_key] = cursor
                else:
                    raise RemoteModelListError("供应商模型列表分页过多，请手动输入模型 ID。")
    except TimeoutError:
        raise RemoteModelListError("获取模型列表超时，请重试或手动输入模型 ID。", 504) from None
    except aiohttp.ClientError:
        raise RemoteModelListError("无法连接供应商，请检查地址、网络或证书后重试。") from None
    return sorted(options.values(), key=lambda option: (option.id.casefold(), option.id))
