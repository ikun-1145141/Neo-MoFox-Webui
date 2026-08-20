"""系统控制管理器。

提供系统重启和关闭功能。
"""

from __future__ import annotations

import asyncio
import sys

from src.app.plugin_system.api.log_api import get_logger

logger = get_logger("system_manager")


class SystemManager:
    """系统控制管理器。

    负责执行系统重启和关闭操作。
    """

    _instance: SystemManager | None = None

    def __new__(cls) -> SystemManager:
        """单例模式。"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def restart_bot(self) -> bool:
        """重启 Bot 系统。

        Returns:
            bool: 总是返回 True（表示已发起重启）
        """
        logger.warning("收到重启信号，准备重启 Bot...")

        # 延迟执行重启，避免阻塞响应
        async def _do_restart() -> None:
            await asyncio.sleep(1)  # 等待响应返回
            logger.info("正在重启系统...")
            # 使用 sys.executable 和原始命令行参数重启
            import os
            python = sys.executable
            os.execv(python, [python] + sys.argv)

        asyncio.create_task(_do_restart())
        return True

    async def shutdown_bot(self) -> bool:
        """关闭 Bot 系统。

        Returns:
            bool: 总是返回 True（表示已发起关闭）
        """
        logger.warning("收到关闭信号，准备关闭 Bot...")

        # 延迟执行关闭，避免阻塞响应
        async def _do_shutdown() -> None:
            await asyncio.sleep(1)  # 等待响应返回
            logger.info("正在关闭系统...")
            sys.exit(0)

        asyncio.create_task(_do_shutdown())
        return True


_system_manager_instance: SystemManager | None = None


def get_system_manager() -> SystemManager:
    """获取系统管理器单例。

    Returns:
        SystemManager: 系统管理器实例
    """
    global _system_manager_instance
    if _system_manager_instance is None:
        _system_manager_instance = SystemManager()
    return _system_manager_instance
