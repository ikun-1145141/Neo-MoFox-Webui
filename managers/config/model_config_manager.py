"""模型配置管理器。

提供模型配置专属操作（如模型测试、提供商/模型枚举）。
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import openai

from src.app.plugin_system.api.log_api import get_logger
from src.core.config.model_config import ModelConfig, init_model_config

from ...utils.config_types import ModelTestRequest, ModelTestResult

logger = get_logger("model_config_manager")


class ModelConfigManager:
    """模型配置管理器。

    提供模型配置的专属操作，如模型测试和枚举。
    读写操作委托给 MainConfigManager。
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
