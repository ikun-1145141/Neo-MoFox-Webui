"""系统控制管理器。

提供系统重启和关闭功能。
"""

from __future__ import annotations

import asyncio
import os
import sys

from src.app.plugin_system.api.log_api import get_logger

logger = get_logger("system_manager")

# 由 Neo-MoFox 启动器注入的监督标记环境变量：带该标记时主程序把"重启"委托给
# 启动器重新拉起，而不是自行 execv。Windows 上 os.execv 走 overlay 模式会更换
# PID 并结束旧进程，导致重启后的主程序脱离启动器管理而"不被识别"。
SUPERVISED_ENV_KEY = "NEO_MOFOX_LAUNCHER_SUPERVISED"
# 主程序请求外部重启时的退出码；启动器见到该退出码会重新拉起主程序进程。
RESTART_EXIT_CODE = 42


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

        启动器监督下（存在 ``NEO_MOFOX_LAUNCHER_SUPERVISED`` 环境变量且值为 ``"1"``）
        以约定退出码退出、由启动器重新拉起进程；否则沿用 execv 原地替换（独立运行）。

        Returns:
            bool: 总是返回 True（表示已发起重启）
        """
        logger.warning("收到重启信号，准备重启 Bot...")
        supervised = os.environ.get(SUPERVISED_ENV_KEY) == "1"

        # 延迟执行重启，避免阻塞响应
        async def _do_restart() -> None:
            await asyncio.sleep(1)  # 等待响应返回
            logger.info("正在重启系统...")
            if supervised:
                # 由启动器监督：委托外部重启，避免 execv 在 Windows 上更换 PID 后失管。
                os._exit(RESTART_EXIT_CODE)
            # 独立运行时使用 sys.executable 和原始命令行参数原地替换
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
