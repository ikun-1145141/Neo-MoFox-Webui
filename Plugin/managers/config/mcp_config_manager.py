"""MCP 配置管理器。"""

from __future__ import annotations

import asyncio
import shutil
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.app.plugin_system.api.log_api import get_logger
from src.core.config.mcp_config import init_mcp_config

from ...utils.config_types import McpTestRequest, McpTestResult

logger = get_logger("mcp_config_manager")


class McpConfigManager:
    """MCP 配置管理器。"""

    def __init__(self) -> None:
        """初始化管理器。"""
        self.mcp_config_path = Path("config/mcp.toml")

    async def reload_config(self) -> None:
        """热重载 MCP 配置。

        通过重新调用 ``init_mcp_config`` 触发 MCPConfig 重新从文件加载，
        同时更新全局单例。
        """
        try:
            # init_mcp_config 会覆盖 _global_mcp_config 单例
            # 放到线程中执行避免阻塞事件循环（其内部为同步文件 I/O）
            await asyncio.to_thread(init_mcp_config, str(self.mcp_config_path))
            logger.info("MCP 配置已热重载")
        except Exception as e:
            logger.error(f"热重载 MCP 配置失败: {e}")
            raise ValueError(f"热重载 MCP 配置失败: {e}")

    async def test_server(self, request: McpTestRequest) -> McpTestResult:
        """测试 MCP 服务连通性。"""
        start_time = time.time()
        try:
            if request.server_type == "stdio":
                result = await self._test_stdio(request.config, request.timeout)
            else:
                result = await self._test_http(request.config, request.timeout)
            result.latency_ms = (time.time() - start_time) * 1000
            return result
        except Exception as e:
            logger.error(f"MCP 服务测试失败: {e}")
            return McpTestResult(
                success=False,
                message="连接失败",
                detail=str(e),
                latency_ms=(time.time() - start_time) * 1000,
            )

    async def _test_stdio(self, config: dict[str, Any] | str, timeout: int) -> McpTestResult:
        if not isinstance(config, dict):
            return McpTestResult(success=False, message="配置错误", detail="Stdio 服务配置必须是对象")

        command = str(config.get("command") or "").strip()
        if not command:
            return McpTestResult(success=False, message="配置错误", detail="缺少 command")

        executable = shutil.which(command)
        if executable is None:
            return McpTestResult(
                success=False,
                message="命令不存在",
                detail=f"找不到 {command}，请确认 Node.js/npm/npx/uvx 已安装并在 PATH 中",
            )

        args = config.get("args") or []
        if not isinstance(args, list):
            return McpTestResult(success=False, message="配置错误", detail="args 必须是数组")

        env = config.get("env") if isinstance(config.get("env"), dict) else None
        process_env = None
        if env:
            import os
            process_env = {**os.environ, **{str(key): str(value) for key, value in env.items()}}

        process = await asyncio.create_subprocess_exec(
            executable,
            *[str(arg) for arg in args],
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=process_env,
        )

        initialize_request = (
            '{"jsonrpc":"2.0","id":1,"method":"initialize",'
            '"params":{"protocolVersion":"2024-11-05","capabilities":{},'
            '"clientInfo":{"name":"neo-mofox-webui","version":"1.0.0"}}}\n'
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(initialize_request.encode("utf-8")),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return McpTestResult(success=True, message="进程可启动", detail="测试超时前进程保持运行，可能为长连接 MCP 服务")

        stderr_text = stderr.decode("utf-8", errors="replace").strip()
        stdout_text = stdout.decode("utf-8", errors="replace").strip()
        if process.returncode not in (0, None) and not stdout_text:
            return McpTestResult(
                success=False,
                message="启动失败",
                detail=stderr_text or f"进程退出码: {process.returncode}",
            )

        if "\"result\"" in stdout_text or "\"method\"" in stdout_text:
            return McpTestResult(success=True, message="连接成功", detail=stdout_text[-500:])

        return McpTestResult(
            success=process.returncode == 0,
            message="进程可启动" if process.returncode == 0 else "连接失败",
            detail=stdout_text or stderr_text or f"进程退出码: {process.returncode}",
        )

    async def _test_http(self, config: dict[str, Any] | str, timeout: int) -> McpTestResult:
        url = config if isinstance(config, str) else config.get("url")
        if not url:
            return McpTestResult(success=False, message="配置错误", detail="缺少 URL")

        return await asyncio.to_thread(self._request_http, str(url), timeout)

    def _request_http(self, url: str, timeout: int) -> McpTestResult:
        request = Request(url, method="GET", headers={"Accept": "application/json, text/event-stream, */*"})
        try:
            with urlopen(request, timeout=timeout) as response:
                status = response.status
                body = response.read(500).decode("utf-8", errors="replace")
                if 200 <= status < 300:
                    return McpTestResult(success=True, message="连接成功", detail=f"HTTP {status}\n{body}".strip())
                return McpTestResult(success=False, message=f"HTTP {status}", detail=body)
        except HTTPError as e:
            body = e.read(500).decode("utf-8", errors="replace")
            return McpTestResult(success=False, message=f"HTTP {e.code}", detail=body or e.reason)
        except URLError as e:
            return McpTestResult(success=False, message="连接失败", detail=str(e.reason))
        except TimeoutError:
            return McpTestResult(success=False, message="连接超时", detail=f"超过 {timeout} 秒未响应")


_mcp_config_manager: McpConfigManager | None = None


def get_mcp_config_manager() -> McpConfigManager:
    """获取 MCP 配置管理器单例。"""
    global _mcp_config_manager
    if _mcp_config_manager is None:
        _mcp_config_manager = McpConfigManager()
    return _mcp_config_manager
