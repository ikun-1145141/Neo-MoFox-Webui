"""插件配置管理器。

提供插件配置专属操作（如枚举可配置插件、获取 Schema）。
"""

from __future__ import annotations

from pathlib import Path

from src.app.plugin_system.api.config_api import get_loaded_plugins, get_config
from src.app.plugin_system.api.log_api import get_logger

from ...utils.config_parser import ConfigParser
from ...utils.config_types import PluginConfigEntry, SectionSchema

logger = get_logger("plugin_config_manager")


class PluginConfigManager:
    """插件配置管理器。

    提供插件配置的专属操作，如列表枚举和 Schema 查询。
    读写操作委托给 MainConfigManager。
    """

    async def list_plugin_configs(self) -> list[PluginConfigEntry]:
        """获取可配置插件列表。

        Returns:
            插件配置条目列表

        Raises:
            RuntimeError: 获取插件列表失败
        """
        try:
            # 从 config_api 获取已加载的插件名称列表
            plugin_names = get_loaded_plugins()

            entries: list[PluginConfigEntry] = []

            for plugin_name in plugin_names:
                # 获取配置实例
                config_instance = get_config(plugin_name)
                if config_instance is None:
                    logger.warning(f"插件 '{plugin_name}' 配置为空，跳过")
                    continue

                config_class = type(config_instance)

                # 获取配置描述
                config_description = getattr(
                    config_class, "config_description", ""
                ) or getattr(config_class, "__doc__", "") or ""

                # 构建配置文件路径
                config_path = f"config/plugins/{plugin_name}/config.toml"

                # 检查文件是否存在
                is_loaded = Path(config_path).exists()

                entries.append(
                    PluginConfigEntry(
                        plugin_name=plugin_name,
                        config_name=plugin_name,
                        config_path=config_path,
                        config_description=config_description.strip(),
                        is_loaded=is_loaded,
                    )
                )

            return entries

        except Exception as e:
            logger.error(f"获取插件配置列表失败: {e}")
            raise RuntimeError(f"获取插件配置列表失败: {e}")

    async def get_plugin_config_schema(self, plugin_name: str) -> list[SectionSchema]:
        """获取插件配置 Schema。

        Args:
            plugin_name: 插件名

        Returns:
            配置节 Schema 列表

        Raises:
            ValueError: 插件配置未找到
        """
        try:
            # 获取配置实例
            config_instance = get_config(plugin_name)
            if config_instance is None:
                raise ValueError(f"插件配置未找到: {plugin_name}")

            config_class = type(config_instance)

            # 提取 Schema
            sections = ConfigParser.extract_schema(config_class)

            return sections

        except Exception as e:
            logger.error(f"获取插件配置 Schema 失败: {e}")
            raise ValueError(f"获取插件配置 Schema 失败: {e}")


# ===== 单例模式 =====

_plugin_config_manager: PluginConfigManager | None = None


def get_plugin_config_manager() -> PluginConfigManager:
    """
    获取插件配置管理器单例。

    Returns:
        插件配置管理器实例
    """
    global _plugin_config_manager
    if _plugin_config_manager is None:
        _plugin_config_manager = PluginConfigManager()
    return _plugin_config_manager
