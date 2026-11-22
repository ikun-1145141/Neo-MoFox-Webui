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

WEBUI_FRONTEND_PATH = "/webui/frontend"


class WebuiStartupPanelHandler(BaseEventHandler):
    """在全部插件加载完成后打印 WebUI 访问地址面板。"""

    name: str = "webui_startup_panel"
    description: str = "所有插件启动完毕后打印 WebUI 内外部访问地址"
    weight: int = 0
    intercept_message: bool = False
    init_subscribe: list[EventType | str] = [EventType.ON_START]

    async def execute(
        self,
        event_name: str,
        params: dict[str, Any],
    ) -> tuple[EventDecision, dict[str, Any]]:
        """处理 WebUI 启动地址面板输出事件。

        Args:
            event_name: 当前触发的事件名称。
            params: 事件参数字典。

        Returns:
            事件处理决策和原始事件参数。
        """

        server = get_http_server()
        if not server.is_running():
            logger.warning("HTTP 服务器尚未运行，跳过 WebUI 访问地址面板输出")
            return EventDecision.PASS, params

        internal_urls = self._build_internal_urls(server.host, server.port)
        external_urls = self._build_external_urls(server.host, server.port)
        self._print_access_panel(internal_urls=internal_urls, external_urls=external_urls)
        return EventDecision.SUCCESS, params

    @staticmethod
    def _build_internal_urls(host: str, port: int) -> list[str]:
        """构建本机内部访问地址列表。

        Args:
            host: HTTP 服务监听地址。
            port: HTTP 服务监听端口。

        Returns:
            指向 WebUI 前端入口的内部访问地址列表。
        """

        internal_hosts = ["127.0.0.1", "localhost"] if host in {"0.0.0.0", "::"} else [host]
        return WebuiStartupPanelHandler._build_urls(internal_hosts, port)

    @classmethod
    def _build_external_urls(cls, host: str, port: int) -> list[str]:
        """构建局域网外部访问地址列表。

        Args:
            host: HTTP 服务监听地址。
            port: HTTP 服务监听端口。

        Returns:
            指向 WebUI 前端入口的外部访问地址列表。
        """

        if host in {"0.0.0.0", "::", "127.0.0.1", "localhost"}:
            external_hosts = cls._get_lan_ips()
        else:
            external_hosts = [host]
        return cls._build_urls(external_hosts, port)

    @staticmethod
    def _build_urls(hosts: list[str], port: int) -> list[str]:
        """根据主机列表构建去重后的 WebUI 访问地址列表。

        Args:
            hosts: 可访问 WebUI 的主机名或 IP 地址列表。
            port: HTTP 服务监听端口。

        Returns:
            去重后的 WebUI 前端访问地址列表。
        """

        urls: list[str] = []
        seen_hosts: set[str] = set()
        for host in hosts:
            normalized_host = host.strip()
            if not normalized_host or normalized_host in seen_hosts:
                continue
            seen_hosts.add(normalized_host)
            url_host = f"[{normalized_host}]" if ":" in normalized_host and not normalized_host.startswith("[") else normalized_host
            urls.append(f"http://{url_host}:{port}{WEBUI_FRONTEND_PATH}")
        return urls

    @staticmethod
    def _get_lan_ips() -> list[str]:
        """获取当前机器可用于局域网访问的 IP 地址列表。

        Returns:
            当前机器可用于外部访问的 IPv4 地址列表。
        """

        lan_ips: list[str] = []
        seen_ips: set[str] = set()

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                primary_ip = sock.getsockname()[0]
                if primary_ip and not primary_ip.startswith("127."):
                    lan_ips.append(primary_ip)
                    seen_ips.add(primary_ip)
        except OSError as exc:
            logger.debug(f"通过 UDP 探测局域网 IP 失败: {exc}")

        try:
            for addr_info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
                ip_address = str(addr_info[4][0])
                if ip_address.startswith("127.") or ip_address in seen_ips:
                    continue
                lan_ips.append(ip_address)
                seen_ips.add(ip_address)
        except OSError as exc:
            logger.debug(f"通过主机名解析局域网 IP 失败: {exc}")

        return lan_ips

    @staticmethod
    def _format_link_list(urls: list[str], empty_message: str) -> str:
        """格式化 Rich 可点击链接列表。

        Args:
            urls: 需要展示的 URL 列表。
            empty_message: URL 列表为空时展示的提示信息。

        Returns:
            Rich markup 格式的链接列表文本。
        """

        if not urls:
            return f"[dim]{empty_message}[/dim]"
        return "\n".join(f"[link={url}]{url}[/link]" for url in urls)

    @staticmethod
    def _print_access_panel(internal_urls: list[str], external_urls: list[str]) -> None:
        """打印 WebUI 访问地址 Rich Panel。

        Args:
            internal_urls: 本机内部访问地址列表。
            external_urls: 局域网外部访问地址列表。
        """

        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold cyan", justify="right")
        table.add_column(style="bold white")
        table.add_row("内部访问", WebuiStartupPanelHandler._format_link_list(internal_urls, "未发现本机访问地址"))
        table.add_row("外部访问", WebuiStartupPanelHandler._format_link_list(external_urls, "未发现局域网访问地址"))
        table.add_row(
            "打开提示",
            "[dim]本机可使用内部访问链接；同一局域网内的其他设备可使用外部访问链接打开 WebUI。[/dim]",
        )

        panel = Panel(
            table,
            title="[bold cyan]Neo-MoFox WebUI 已就绪[/bold cyan]",
            subtitle="[dim]所有插件已启动完毕[/dim]",
            border_style="cyan",
            expand=False,
        )
        logger.print_rich(panel)
