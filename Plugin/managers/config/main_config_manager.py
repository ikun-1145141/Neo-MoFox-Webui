"""主配置管理器。

提供统一的配置读写接口，支持 bot、model、plugin 三类配置。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from src.app.plugin_system.api.config_api import get_config
from src.app.plugin_system.api.log_api import get_logger
from src.kernel.config import ConfigBase
from src.core.config.core_config import CoreConfig
from src.core.config.model_config import ModelConfig

from ...utils.config_parser import ConfigParser
from ...utils.config_types import EnhancedConfigResponse

logger = get_logger("main_config_manager")


class MainConfigManager:
    """主配置管理器。

    统一处理所有类型配置的读取、全量写入和增量写入。
    """

    def __init__(self) -> None:
        """初始化管理器。"""
        # 配置文件路径映射
        self.bot_config_path = Path("config/core.toml")
        self.model_config_path = Path("config/model.toml")

    async def get_config(
        self,
        config_type: Literal["bot", "model", "plugin"],
        plugin_name: str | None = None,
    ) -> EnhancedConfigResponse:
        """获取增强配置。

        Args:
            config_type: 配置类型（"bot"、"model"、"plugin"）
            plugin_name: 插件名（config_type="plugin" 时必填）

        Returns:
            增强配置响应（包含 Schema 和数据）

        Raises:
            ValueError: 参数错误
            FileNotFoundError: 配置文件不存在
        """
        if config_type == "bot":
            return await self._get_bot_config()
        elif config_type == "model":
            return await self._get_model_config()
        elif config_type == "plugin":
            if not plugin_name:
                raise ValueError("plugin_name 不能为空")
            return await self._get_plugin_config(plugin_name)
        else:
            raise ValueError(f"不支持的配置类型: {config_type}")

    async def full_write(
        self,
        config_type: Literal["bot", "model", "plugin"],
        data: dict[str, Any],
        plugin_name: str | None = None,
    ) -> EnhancedConfigResponse:
        """全量写入配置。

        Args:
            config_type: 配置类型
            data: 完整配置数据
            plugin_name: 插件名（plugin 类型时必填）

        Returns:
            写入后的增强配置响应

        Raises:
            ValueError: 参数错误或验证失败
        """
        if config_type == "bot":
            return await self._write_bot_config(data)
        elif config_type == "model":
            return await self._write_model_config(data)
        elif config_type == "plugin":
            if not plugin_name:
                raise ValueError("plugin_name 不能为空")
            return await self._write_plugin_config(plugin_name, data)
        else:
            raise ValueError(f"不支持的配置类型: {config_type}")

    async def patch_write(
        self,
        config_type: Literal["bot", "model", "plugin"],
        patch: dict[str, Any],
        plugin_name: str | None = None,
    ) -> EnhancedConfigResponse:
        """增量写入配置。

        Args:
            config_type: 配置类型
            patch: 要更新的部分数据
            plugin_name: 插件名（plugin 类型时必填）

        Returns:
            合并后的增强配置响应

        Raises:
            ValueError: 参数错误或验证失败
        """
        # 先读取当前配置
        current_response = await self.get_config(config_type, plugin_name)
        current_data = current_response.data

        # 深度合并
        merged_data = ConfigParser.deep_merge(current_data, patch)

        # 全量写入合并后的数据
        return await self.full_write(config_type, merged_data, plugin_name)

    # ===== 私有方法：bot 配置 =====

    async def _get_bot_config(self) -> EnhancedConfigResponse:
        """获取机器人配置。"""
        data = ConfigParser.read_toml(self.bot_config_path)
        return ConfigParser.build_enhanced_response(
            config_type="bot",
            config_class=CoreConfig,
            data=data,
        )

    async def _write_bot_config(self, data: dict[str, Any]) -> EnhancedConfigResponse:
        """写入机器人配置。"""
        ConfigParser.write_toml(self.bot_config_path, CoreConfig, data)
        logger.info("机器人配置已写入")
        return await self._get_bot_config()

    # ===== 私有方法：model 配置 =====

    async def _get_model_config(self) -> EnhancedConfigResponse:
        """获取模型配置。

        model.toml 使用 ModelConfig 类管理，包含 api_providers、models 和 model_tasks。
        """
        # 读取原始数据
        data = ConfigParser.read_toml(self.model_config_path)
        
        # 提取 Schema（仅针对 model_tasks 节）
        sections = ConfigParser.extract_schema(ModelConfig)
        
        return EnhancedConfigResponse(
            config_type="model",
            plugin_name=None,
            sections=sections,
            data=data,
        )

    async def _write_model_config(self, data: dict[str, Any]) -> EnhancedConfigResponse:
        """写入模型配置。"""
        # 使用 ModelConfig 进行验证
        ConfigParser.write_toml(self.model_config_path, ModelConfig, data)
        logger.info("模型配置已写入")

        return await self._get_model_config()

    # ===== 私有方法：plugin 配置 =====

    async def _get_plugin_config(self, plugin_name: str) -> EnhancedConfigResponse:
        """获取插件配置。

        Args:
            plugin_name: 插件名

        Raises:
            ValueError: 插件配置未找到
        """
        # 通过 config_api 获取插件配置类
        try:
            config_instance = get_config(plugin_name)
            config_class = type(config_instance)

            # 获取配置文件路径
            config_path = self._get_plugin_config_path(plugin_name)

            # 读取数据
            data = ConfigParser.read_toml(config_path)

            return ConfigParser.build_enhanced_response(
                config_type="plugin",
                config_class=config_class,
                data=data,
                plugin_name=plugin_name,
            )
        except Exception as e:
            raise ValueError(f"获取插件配置失败: {e}")

    async def _write_plugin_config(
        self, plugin_name: str, data: dict[str, Any]
    ) -> EnhancedConfigResponse:
        """写入插件配置。"""
        try:
            # 获取配置类
            config_instance = get_config(plugin_name)
            config_class = type(config_instance)

            # 获取配置文件路径
            config_path = self._get_plugin_config_path(plugin_name)

            # 写入
            ConfigParser.write_toml(config_path, config_class, data)
            logger.info(f"插件配置已写入: {plugin_name}")

            return await self._get_plugin_config(plugin_name)
        except Exception as e:
            raise ValueError(f"写入插件配置失败: {e}")

    def _get_plugin_config_path(self, plugin_name: str) -> Path:
        """获取插件配置文件路径。

        Args:
            plugin_name: 插件名

        Returns:
            配置文件路径
        """
        # 标准路径：config/plugins/{plugin_name}/config.toml
        return Path(f"config/plugins/{plugin_name}/config.toml")


# ===== 单例模式 =====

_main_config_manager: MainConfigManager | None = None


def get_main_config_manager() -> MainConfigManager:
    """获取主配置管理器单例。

    Returns:
        主配置管理器实例
    """
    global _main_config_manager
    if _main_config_manager is None:
        _main_config_manager = MainConfigManager()
    return _main_config_manager
