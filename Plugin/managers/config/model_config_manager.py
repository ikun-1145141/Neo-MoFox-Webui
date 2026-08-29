"""模型配置管理器。

提供模型配置专属操作（如模型测试、提供商/模型枚举和远程模型发现）。
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

from src.app.plugin_system.api.log_api import get_logger
from src.core.config.model_config import ModelConfig, init_model_config

from ...utils.config_types import (
    ModelTestRequest,
    ModelTestResult,
    RemoteModelListRequest,
    RemoteModelProvider,
)

logger = get_logger("model_config_manager")


class ModelConfigManager:
    """模型配置管理器。

    提供模型配置的专属操作，如模型测试、模型枚举和远程模型发现。
    配置文件的通用读写仍然委托给 MainConfigManager。
    """

    def __init__(self) -> None:
        """初始化管理器。"""
        self.model_config_path = Path("config/model.toml")

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
        """测试模型连通性。

        Args:
            request: 测试请求

        Returns:
            测试结果

        Raises:
            ValueError: 配置不存在或测试失败
        """
        # 读取模型配置
        model_config = ModelConfig.load(self.model_config_path)

        # 查找提供商
        try:
            provider = model_config.get_provider(request.provider_name)
        except KeyError:
            raise ValueError(f"提供商不存在: {request.provider_name}")

        # 查找模型
        model = None
        for m in model_config.models:
            if m.name == request.model_name and m.api_provider == request.provider_name:
                model = m
                break

        if not model:
            raise ValueError(
                f"模型不存在: {request.model_name} (提供商: {request.provider_name})"
            )

        # 执行测试
        try:
            # 获取 API 密钥
            api_key = provider.api_key
            if isinstance(api_key, list):
                api_key = api_key[0] if api_key else ""

            # 创建客户端
            client = openai.AsyncOpenAI(
                base_url=provider.base_url,
                api_key=api_key,
                timeout=request.timeout,
            )

            # 发送测试请求
            start_time = time.time()
            response = await client.chat.completions.create(
                model=model.model_identifier,
                messages=[{"role": "user", "content": request.test_prompt}],
                max_tokens=50,
            )
            end_time = time.time()

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
            logger.error(f"模型测试失败: {e}")
            return ModelTestResult(
                success=False,
                response_text=None,
                latency_ms=None,
                error_message=str(e),
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
        """获取本地模型名称列表。

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
        return [m.name for m in model_config.models]

    async def list_remote_models(self, request: RemoteModelListRequest) -> list[str]:
        """从供应商远程接口获取可用模型标识符。

        Args:
            request: 远程模型列表请求。可以指定已保存的 ``provider_name``，
                也可以直接传入尚未保存的临时 ``provider``；临时配置不会写盘。

        Returns:
            去重后、保持远程返回顺序的模型标识符列表。

        Raises:
            ValueError: 请求参数无效、供应商不支持模型枚举、上游请求失败或响应无效。
        """
        provider = self._resolve_remote_provider(request)
        client_type = provider.client_type
        if client_type == "bedrock":
            raise ValueError(
                "当前配置暂不支持 Bedrock 远程模型列表；"
                "请先配置 AWS 区域和凭据后再接入 Bedrock 模型发现"
            )

        url = self._build_models_url(provider.base_url, client_type)
        headers = self._build_request_headers(provider, client_type)
        params = self._build_request_query(provider)
        api_key = self._get_api_key(provider.api_key)
        if client_type in {"gemini", "aiohttp_gemini"} and api_key:
            # Gemini REST API 同时兼容 key query；保留用户自定义 query，避免覆盖显式配置。
            params.setdefault("key", api_key)

        timeout = aiohttp.ClientTimeout(total=float(provider.timeout))
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers, params=params) as response:
                    body_text = await response.text()
                    if response.status >= 400:
                        detail = self._redact_secret(
                            self._extract_error_detail(body_text), provider
                        )
                        suffix = f": {detail}" if detail else ""
                        raise ValueError(
                            f"远程模型接口返回 HTTP {response.status}{suffix}"
                        )

                    try:
                        payload = await response.json(content_type=None)
                    except (TypeError, ValueError) as exc:
                        raise ValueError("远程模型接口返回的不是有效 JSON") from exc
        except asyncio.TimeoutError as exc:
            raise ValueError(f"远程模型列表请求超时（{provider.timeout:g} 秒）") from exc
        except aiohttp.ClientError as exc:
            raise ValueError(f"远程模型列表请求失败: {self._redact_secret(str(exc), provider)}") from exc

        models = self._extract_remote_model_ids(payload, client_type)
        if not models:
            raise ValueError("远程模型接口返回空列表或缺少可识别的模型标识符")

        logger.info(
            f"远程模型列表获取成功: provider={provider.name} "
            f"client_type={client_type} count={len(models)}"
        )
        return models

    def _resolve_remote_provider(
        self, request: RemoteModelListRequest
    ) -> RemoteModelProvider:
        """解析临时或已保存的供应商配置。"""
        if request.provider is not None:
            return request.provider

        provider_name = (request.provider_name or "").strip()
        if not provider_name:
            raise ValueError("必须提供 provider_name 或临时 provider 配置")

        try:
            model_config = ModelConfig.load(self.model_config_path)
            saved_provider = model_config.get_provider(provider_name)
        except KeyError as exc:
            raise ValueError(f"提供商不存在: {provider_name}") from exc
        except Exception as exc:
            raise ValueError(f"读取提供商配置失败: {self._redact_secret(str(exc), None)}") from exc

        try:
            provider_data = saved_provider.model_dump()
        except AttributeError:
            provider_data = {
                "name": saved_provider.name,
                "base_url": saved_provider.base_url,
                "api_key": saved_provider.api_key,
                "client_type": saved_provider.client_type,
                "timeout": saved_provider.timeout,
            }
        return RemoteModelProvider.model_validate(provider_data)

    @staticmethod
    def _get_api_key(api_key: str | list[str]) -> str:
        """获取远程请求使用的第一个非空 API Key。"""
        if isinstance(api_key, str):
            return api_key.strip()
        for key in api_key:
            if isinstance(key, str) and key.strip():
                return key.strip()
        return ""

    @staticmethod
    def _build_models_url(base_url: str, client_type: str) -> str:
        """根据客户端协议构造模型列表 URL，并校验基础 URL。"""
        raw_url = base_url.strip()
        try:
            parsed = urlsplit(raw_url)
        except ValueError as exc:
            raise ValueError("API 地址格式无效") from exc
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("API 地址必须是包含主机名的 http/https URL")
        if parsed.username or parsed.password:
            raise ValueError("API 地址不应在 URL 中嵌入用户名或密码")

        path = parsed.path.rstrip("/")
        if path.endswith("/models"):
            # 允许高级用户直接传入模型列表端点，避免重复拼接 /models。
            models_path = path
        elif client_type == "anthropic":
            models_path = f"{path}/models" if path.endswith("/v1") else f"{path}/v1/models"
        elif client_type in {"gemini", "aiohttp_gemini"}:
            if not path:
                models_path = "/v1beta/models"
            else:
                models_path = f"{path}/models"
        else:
            models_path = f"{path}/models"

        return urlunsplit((parsed.scheme, parsed.netloc, models_path, parsed.query, ""))

    @staticmethod
    def _build_request_headers(
        provider: RemoteModelProvider, client_type: str
    ) -> dict[str, str]:
        """构造远程模型列表请求头。"""
        headers: dict[str, str] = {"Accept": "application/json"}
        api_key = ModelConfigManager._get_api_key(provider.api_key)
        if client_type in {"openai", "openai_response"} and api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        elif client_type == "anthropic":
            if api_key:
                headers["x-api-key"] = api_key
            headers["anthropic-version"] = "2023-06-01"
        elif client_type in {"gemini", "aiohttp_gemini"} and api_key:
            headers["x-goog-api-key"] = api_key

        extra_headers = provider.extra_params.get("headers")
        if isinstance(extra_headers, dict):
            for key, value in extra_headers.items():
                if isinstance(key, str) and isinstance(value, str):
                    headers[key] = value
        return headers

    @staticmethod
    def _build_request_query(provider: RemoteModelProvider) -> dict[str, str]:
        """提取临时供应商配置中的 URL query 参数。"""
        query = provider.extra_params.get("query")
        if not isinstance(query, dict):
            query = {}
        return {
            str(key): str(value)
            for key, value in query.items()
            if isinstance(key, str) and value is not None
        }

    @staticmethod
    def _extract_remote_model_ids(payload: Any, client_type: str) -> list[str]:
        """解析 OpenAI、Anthropic 和 Gemini 模型列表响应。"""
        if isinstance(payload, dict):
            records = payload.get("data")
            if not isinstance(records, list):
                records = payload.get("models")
        elif isinstance(payload, list):
            records = payload
        else:
            records = None

        if not isinstance(records, list):
            return []

        result: list[str] = []
        seen: set[str] = set()
        for record in records:
            raw_identifier: Any = None
            if isinstance(record, str):
                raw_identifier = record
            elif isinstance(record, dict):
                if client_type in {"gemini", "aiohttp_gemini"}:
                    raw_identifier = record.get("name") or record.get("id")
                else:
                    raw_identifier = record.get("id") or record.get("name")

            if not isinstance(raw_identifier, str):
                continue
            identifier = raw_identifier.strip()
            if client_type in {"gemini", "aiohttp_gemini"}:
                identifier = re.sub(r"^models/", "", identifier)
            if identifier and identifier not in seen:
                seen.add(identifier)
                result.append(identifier)
        return result

    @staticmethod
    def _extract_error_detail(body_text: str) -> str:
        """从上游错误响应提取短描述，不回显完整响应。"""
        try:
            payload = json.loads(body_text)
        except (TypeError, ValueError):
            payload = None

        detail: Any = None
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                detail = error.get("message") or error.get("detail") or error.get("status")
            elif isinstance(error, str):
                detail = error
            detail = detail or payload.get("message") or payload.get("detail")
        if not isinstance(detail, str):
            detail = body_text.strip()
        return re.sub(r"\s+", " ", detail)[:300]

    @staticmethod
    def _redact_secret(message: str, provider: RemoteModelProvider | None) -> str:
        """从日志/异常文本中移除 API Key。"""
        redacted = message
        if provider is not None:
            keys = provider.api_key if isinstance(provider.api_key, list) else [provider.api_key]
            for key in keys:
                if isinstance(key, str) and key:
                    redacted = redacted.replace(key, "***")
        return redacted


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
