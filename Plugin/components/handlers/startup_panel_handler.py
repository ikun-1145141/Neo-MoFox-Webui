"""WebUI 启动地址事件处理器。

在所有插件加载完成后输出 WebUI 的内部与外部访问地址。
"""

from __future__ import annotations

import socket
from typing import Any

from rich.panel import Panel
from rich.table import Table

from src.core.components import BaseEventHandler, EventType
from src.core.transport.router.http_server import get_http_server
from src.kernel.event import EventDecision
from src.kernel.logger import get_logger

logger = get_logger("webui.startup_panel", display="WebUI", color="cyan")


class WebuiStartupPanelHandler(BaseEventHandler):
    """在全部插件加载完成后打印 WebUI 访问地址面板。"""

    handler_name: str = "webui_startup_panel"
    handler_description: str = "所有插件启动完毕后打印 WebUI 内外部访问地址"
    weight: int = 0
    intercept_message: bool = False
    init_subscribe: list[EventType | str] = [EventType.ON_ALL_PLUGIN_LOADED]

    async def execute(
        self,
        event_name: str,
        params: dict[str, Any],
    ) -> tuple[EventDecision, dict[str, Any]]:
        """处理所有插件加载完成事件。

        Args:
            event_name: 当前触发的事件名称。
            params: 事件参数字典。

        Returns:
            事件处理决策和原始事件参数。
        """

        if event_name != EventType.ON_ALL_PLUGIN_LOADED.value:
            return EventDecision.PASS, params

        server = get_http_server()
        if not server.is_running():
            logger.warning("HTTP 服务器尚未运行，跳过 WebUI 访问地址面板输出")
            return EventDecision.PASS, params

        internal_url = self._build_internal_url(server.host, server.port)
        external_url = self._build_external_url(server.host, server.port)
        self._print_access_panel(internal_url=internal_url, external_url=external_url)
        return EventDecision.SUCCESS, params

    @staticmethod
    def _build_internal_url(host: str, port: int) -> str:
        """构建本机内部访问地址。

        Args:
            host: HTTP 服务监听地址。
            port: HTTP 服务监听端口。

        Returns:
            指向 WebUI 前端入口的内部访问地址。
        """

        internal_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
        return f"http://{internal_host}:{port}/webui/frontend"

    @classmethod
    def _build_external_url(cls, host: str, port: int) -> str:
        """构建局域网外部访问地址。

        Args:
            host: HTTP 服务监听地址。
            port: HTTP 服务监听端口。

        Returns:
            指向 WebUI 前端入口的外部访问地址。
        """

        external_host = cls._get_lan_ip() if host in {"0.0.0.0", "::", "127.0.0.1", "localhost"} else host
        return f"http://{external_host}:{port}/webui/frontend"

    @staticmethod
    def _get_lan_ip() -> str:
        """获取当前机器的局域网 IP 地址。

        Returns:
            当前机器优先用于外部访问的 IPv4 地址。
        """

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]

    @staticmethod
    def _print_access_panel(internal_url: str, external_url: str) -> None:
        """打印 WebUI 访问地址 Rich Panel。

        Args:
            internal_url: 本机内部访问地址。
            external_url: 局域网外部访问地址。
        """

        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold cyan", justify="right")
        table.add_column(style="bold white")
        table.add_row("内部访问", f"[link={internal_url}]{internal_url}[/link]")
        table.add_row("外部访问", f"[link={external_url}]{external_url}[/link]")

        panel = Panel(
            table,
            title="[bold cyan]Neo-MoFox WebUI 已就绪[/bold cyan]",
            subtitle="[dim]所有插件已启动完毕[/dim]",
            border_style="cyan",
            expand=False,
        )
        logger.print_rich(panel)
