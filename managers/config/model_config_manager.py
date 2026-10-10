"""模型配置管理器。

提供模型配置专属操作（如模型测试、提供商/模型枚举）。
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import aiohttp
import openai
from yarl import URL

from src.app.plugin_system.api.log_api import get_logger
from src.core.config.model_config import ModelConfig, init_model_config

from ...utils.config_types import (
    ModelTestRequest, ModelTestResult, RemoteModelListRequest, RemoteModelOption,
)
from ...utils.response import BaseResponse

logger = get_logger("model_config_manager")

REMOTE_MODEL_TIMEOUT = 15
MAX_MODEL_LIST_PAGES = 100
MAX_MODEL_LIST_PAGE_BYTES = 4 * 1024 * 1024


class ModelConfigManager:
    """模型配置管理器。

    提供模型配置的专属操作，如模型测试和枚举。
    读写操作委托给 MainConfigManager。
    """

    def __init__(self) -> None:
        """初始化管理器。"""
        self.model_config_path = Path("config/model.toml")

    async def list_remote_models(
        self, request: RemoteModelListRequest
    ) -> BaseResponse[list[RemoteModelOption]]:
        """根据页面配置快照枚举供应商模型，统一返回 BaseResponse。

        Args:
            request: 当前供应商配置，不要求已保存到 model.toml。
        Returns:
            成功时包含去重后的模型列表；失败时只包含本地生成的安全文案。
            不保存配置、不改变密钥轮询状态，所有分页共用 15 秒时限。
        """
        try:
            url = self._remote_models_url(request.base_url, request.client_type)
            headers = self._remote_model_headers(request)
        except ValueError as error:
            return BaseResponse.error(code=400, message=str(error))

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
                        # 分页只更新当前地址的游标，不采用上游返回的 next URL。
                        async with session.get(
                            url.update_query(params), headers=headers, allow_redirects=False
                        ) as response:
                            page = await self._read_remote_model_page(response)
                        if page.code != 200:
                            return BaseResponse.error(code=page.code, message=page.message)
                        data = page.data
                        if data is None:
                            return BaseResponse.error(code=502, message="供应商返回了无法识别的模型列表。")

                        items = data.get("models", []) if request.client_type == "gemini" else data.get("data")
                        if not isinstance(items, list):
                            return BaseResponse.error(code=502, message="供应商返回的模型列表格式不正确。")
                        self._collect_remote_model_options(items, request.client_type, options)

                        if request.client_type == "gemini":
                            cursor = data.get("nextPageToken")
                            cursor_key = "pageToken"
                        else:
                            has_more = data.get("has_more", False)
                            if not isinstance(has_more, bool):
                                return BaseResponse.error(code=502, message="供应商返回的分页标记无效。")
                            if not has_more:
                                break
                            cursor = data.get("last_id")
                            if not cursor and items and isinstance(items[-1], dict):
                                cursor = items[-1].get("id")
                            if not cursor:
                                return BaseResponse.error(code=502, message="供应商返回的模型列表缺少下一页游标。")
                            cursor_key = "after_id"
                        if cursor is None or cursor == "":
                            break
                        if not isinstance(cursor, str) or cursor in seen_cursors:
                            return BaseResponse.error(code=502, message="供应商返回的模型列表分页无效或重复。")
                        seen_cursors.add(cursor)
                        params[cursor_key] = cursor
                    else:
                        return BaseResponse.error(code=502, message="供应商模型列表分页过多，请手动输入模型 ID。")
        except TimeoutError:
            return BaseResponse.error(code=504, message="获取模型列表超时，请重试或手动输入模型 ID。")
        except aiohttp.ClientError:
            return BaseResponse.error(code=502, message="无法连接供应商，请检查地址、网络或证书后重试。")
        except Exception as error:
            logger.error(f"获取远程模型列表失败，异常类型: {type(error).__name__}")
            return BaseResponse.error(code=500, message="获取模型列表失败，请稍后重试或手动输入模型 ID。")

        return BaseResponse.ok(
            data=sorted(options.values(), key=lambda option: (option.id.casefold(), option.id)),
            message="获取远程模型列表成功",
        )

    @staticmethod
    def _remote_models_url(base_url: str, client_type: str) -> URL:
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
            raise ValueError(
                "供应商地址无效，请填写不含用户名、密码或片段的 HTTP/HTTPS 基础地址。"
            ) from None

    @staticmethod
    def _remote_model_headers(request: RemoteModelListRequest) -> dict[str, str]:
        """仅取首个非空密钥；不调用核心的轮询取钥函数。"""
        keys = [request.api_key] if isinstance(request.api_key, str) else request.api_key
        key = next((value.strip() for value in keys if value.strip()), "")
        if not key or any(ord(char) < 32 or ord(char) == 127 for char in key):
            raise ValueError("请先为供应商填写有效的 API 密钥。")

        headers = {"Accept": "application/json"}
        if request.client_type == "openai":
            headers["Authorization"] = f"Bearer {key}"
        elif request.client_type == "anthropic":
            headers["x-api-key"] = key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["x-goog-api-key"] = key
        return headers

    @staticmethod
    async def _read_remote_model_page(
        response: aiohttp.ClientResponse,
    ) -> BaseResponse[dict[str, Any]]:
        """限量读取 JSON；错误只返回安全文案，不透传上游正文。"""
        status = response.status
        if not 200 <= status < 300:
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
            return BaseResponse.error(code=502, message=message)

        body = bytearray()
        async for chunk in response.content.iter_chunked(64 * 1024):
            body.extend(chunk)
            if len(body) > MAX_MODEL_LIST_PAGE_BYTES:
                return BaseResponse.error(code=502, message="供应商返回的模型列表过大，请手动输入模型 ID。")
        try:
            data = json.loads(body)
        except (ValueError, UnicodeError):
            return BaseResponse.error(code=502, message="供应商返回的模型列表不是有效的 JSON。")
        if not isinstance(data, dict) or "error" in data:
            return BaseResponse.error(code=502, message="供应商返回了无法识别的模型列表。")
        return BaseResponse.ok(data=data)

    @staticmethod
    def _collect_remote_model_options(
        items: list[Any], client_type: str, options: dict[str, RemoteModelOption]
    ) -> None:
        """忽略无效项并按 ID 去重，不推断价格或模型能力。"""
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

    async def reload_config(self) -> None:
        """热重载模型配置。

        通过重新调用 ``init_model_config`` 触发 ModelConfig 重新从文件加载，
        同时更新全局单例。``ModelConfig.model_post_init`` 会自动重建内部缓存。
        """
        try:
            # init_model_config 会覆盖 _global_model_config 单例
            # 放到线程中执行避免阻塞事件循环（其内部为同步文件 I/O）
            await asyncio.to_thread(init_model_config, str(self.model_config_path))
            logger.info("模型配置已热重载")
        except Exception as e:
            logger.error(f"热重载模型配置失败: {e}")
            raise ValueError(f"热重载模型配置失败: {e}")

    async def test_model(self, request: ModelTestRequest) -> ModelTestResult:
        """使用页面快照测试连通性，不保存配置或热重载运行时。

        Args:
            request: 测试请求；provider/model 成对提供时优先使用页面值，
                均未提供时兼容旧客户端，按名称读取已保存配置。

        Returns:
            测试结果

        Raises:
            ValueError: 快照不完整、不一致，或已保存的配置不存在。
        """
        if request.provider is not None or request.model is not None:
            # 不把不完整的页面数据与磁盘配置混用，也不回退到同名旧配置。
            if request.provider is None or request.model is None:
                raise ValueError("测试时必须同时提供供应商和模型配置")
            provider = request.provider
            model = request.model
            if provider.name != request.provider_name:
                raise ValueError("供应商配置与测试的供应商名称不一致")
            if model.name != request.model_name:
                raise ValueError("模型配置与测试的模型名称不一致")
            if model.api_provider != provider.name:
                raise ValueError("模型所属供应商与测试的供应商不一致")
        else:
            # 旧请求仅包含名称，继续使用已保存的配置。
            model_config = ModelConfig.load(self.model_config_path)
            try:
                provider = model_config.get_provider(request.provider_name)
            except KeyError:
                raise ValueError(f"提供商不存在: {request.provider_name}")

            model = next(
                (m for m in model_config.models
                 if m.name == request.model_name and m.api_provider == request.provider_name),
                None,
            )
            if model is None:
                raise ValueError(
                    f"模型不存在: {request.model_name} (提供商: {request.provider_name})"
                )

        if not provider.base_url.strip():
            raise ValueError("供应商 API 地址不能为空")
        if not model.model_identifier.strip():
            raise ValueError("模型标识符不能为空")

        # 执行测试
        try:
            # 测试仅使用首个非空密钥，不改变运行时密钥轮询状态。
            api_keys = provider.api_key if isinstance(provider.api_key, list) else [provider.api_key]
            api_key = next((key.strip() for key in api_keys if key.strip()), "")
            if not api_key:
                raise ValueError("供应商 API 密钥不能为空")

            # 临时客户端必须关闭；整次测试受同一个超时时限约束。
            start_time = time.perf_counter()
            async with asyncio.timeout(request.timeout):
                async with openai.AsyncOpenAI(
                    base_url=provider.base_url,
                    api_key=api_key,
                    timeout=request.timeout,
                    max_retries=0,
                ) as client:
                    response = await client.chat.completions.create(
                        model=model.model_identifier,
                        messages=[{"role": "user", "content": request.test_prompt}],
                        max_tokens=50,
                    )
            end_time = time.perf_counter()

            # 提取响应
            response_text = response.choices[0].message.content or ""
            latency_ms = (end_time - start_time) * 1000

            logger.info(f"模型测试成功: {model.name} ({latency_ms:.2f}ms)")

            return ModelTestResult(
                success=True,
                response_text=response_text,
                latency_ms=latency_ms,
                error_message=None,
                model_identifier=model.model_identifier,
                provider_base_url=provider.base_url,
            )

        except Exception as e:
            error_message = (
                f"模型测试超时（{request.timeout} 秒）"
                if isinstance(e, (TimeoutError, openai.APITimeoutError))
                else str(e)
            )
            logger.error(f"模型测试失败: {error_message}")
            return ModelTestResult(
                success=False,
                response_text=None,
                latency_ms=None,
                error_message=error_message,
                model_identifier=model.model_identifier,
                provider_base_url=provider.base_url,
            )

    async def list_providers(self) -> list[str]:
        """获取所有提供商名称列表。

        Returns:
            提供商名称列表
        """
        model_config = ModelConfig.load(self.model_config_path)
        return [p.name for p in model_config.api_providers]

    async def list_models(self, provider_name: str | None = None) -> list[str]:
        """获取模型名称列表。

        Args:
            provider_name: 提供商名称（不指定则返回所有模型）

        Returns:
            模型名称列表
        """
        model_config = ModelConfig.load(self.model_config_path)

        if provider_name:
            return [
                m.name for m in model_config.models if m.api_provider == provider_name
            ]
        else:
            return [m.name for m in model_config.models]


# ===== 单例模式 =====

_model_config_manager: ModelConfigManager | None = None


def get_model_config_manager() -> ModelConfigManager:
    """获取模型配置管理器单例。

    Returns:
        模型配置管理器实例
    """
    global _model_config_manager
    if _model_config_manager is None:
        _model_config_manager = ModelConfigManager()
    return _model_config_manager
