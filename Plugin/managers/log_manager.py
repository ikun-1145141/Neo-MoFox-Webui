"""日志管理器。

提供实时日志广播和历史日志读取的业务逻辑。
"""

from __future__ import annotations

import asyncio
import os
from collections import deque
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.kernel.logger import get_logger

logger = get_logger("webui.log_manager", display="WebUI.LogManager")

# 默认日志目录
DEFAULT_LOG_DIR = Path("logs")

# 实时日志缓冲区大小
LOG_BUFFER_SIZE = 200


class LogEntry(BaseModel):
    """单条日志条目。

    Attributes:
        timestamp: ISO 格式时间戳
        level: 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
        logger_name: 日志记录器名称
        display: 显示名称
        color: 日志颜色
        message: 日志消息内容
        metadata: 附加元数据
    """

    timestamp: str = Field(description="ISO 格式时间戳")
    level: str = Field(description="日志级别")
    logger_name: str = Field(default="", description="日志记录器名称")
    display: str = Field(default="", description="显示名称")
    color: str = Field(default="", description="日志颜色")
    message: str = Field(description="日志消息内容")
    metadata: dict[str, Any] = Field(default_factory=dict, description="附加元数据")


class LogFileInfo(BaseModel):
    """日志文件信息。

    Attributes:
        filename: 文件名
        size: 文件大小（字节）
        modified_time: 最后修改时间（ISO 格式）
        path: 相对路径
    """

    filename: str = Field(description="文件名")
    size: int = Field(description="文件大小（字节）")
    modified_time: str = Field(description="最后修改时间")
    path: str = Field(description="相对路径")


class LogContentResponse(BaseModel):
    """日志内容响应模型。

    Attributes:
        content: 日志内容（按行）
        offset: 当前偏移量（字节）
        size: 本次实际返回的大小（字节）
        total_size: 日志文件总大小（字节）
        has_prev: 是否可以向前（向上）加载更多
        has_next: 是否可以向后（向下）加载更多
        next_offset: 下次向下请求的偏移量
        prev_offset: 下次向上请求的偏移量
    """

    content: list[str] = Field(description="日志内容（按行）")
    offset: int = Field(description="当前偏移量（字节）")
    size: int = Field(description="本次实际返回的大小（字节）")
    total_size: int = Field(description="日志文件总大小（字节）")
    has_prev: bool = Field(description="是否可以向前加载更多")
    has_next: bool = Field(description="是否可以向后加载更多")
    next_offset: int = Field(description="下次向下请求的偏移量")
    prev_offset: int = Field(description="下次向上请求的偏移量")


class LogManager:
    """日志管理器。

    负责：
    - 维护实时日志缓冲区
    - 管理 WebSocket 客户端连接
    - 提供历史日志文件列表和内容读取

    Attributes:
        _buffer: 实时日志环形缓冲区
        _clients: 已连接的 WebSocket 客户端集合
        _lock: 异步锁
        _log_dir: 日志文件目录
    """

    def __init__(self, log_dir: str | Path = DEFAULT_LOG_DIR) -> None:
        """初始化日志管理器。

        Args:
            log_dir: 日志文件目录路径
        """
        self._buffer: deque[dict[str, Any]] = deque(maxlen=LOG_BUFFER_SIZE)
        self._clients: set[asyncio.Queue[dict[str, Any]]] = set()
        self._lock = asyncio.Lock()
        self._log_dir = Path(log_dir)

    async def push_log(self, log_data: dict[str, Any]) -> None:
        """推送一条日志到缓冲区并广播给所有客户端。

        Args:
            log_data: 日志数据字典，包含 timestamp/level/message 等字段
        """
        self._buffer.append(log_data)

        # 广播给所有已连接客户端
        disconnected: list[asyncio.Queue[dict[str, Any]]] = []
        async with self._lock:
            for queue in self._clients:
                try:
                    queue.put_nowait(log_data)
                except asyncio.QueueFull:
                    # 客户端消费太慢，丢弃旧消息
                    try:
                        queue.get_nowait()
                        queue.put_nowait(log_data)
                    except (asyncio.QueueEmpty, asyncio.QueueFull):
                        disconnected.append(queue)

            for q in disconnected:
                self._clients.discard(q)

    async def register_client(self) -> asyncio.Queue[dict[str, Any]]:
        """注册一个新的 WebSocket 客户端。

        Returns:
            客户端专用的消息队列
        """
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=500)
        async with self._lock:
            self._clients.add(queue)
        return queue

    async def unregister_client(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """注销一个 WebSocket 客户端。

        Args:
            queue: 客户端的消息队列
        """
        async with self._lock:
            self._clients.discard(queue)

    def get_buffer(self) -> list[dict[str, Any]]:
        """获取当前缓冲区中的所有日志。

        Returns:
            缓冲区中的日志列表（按时间顺序）
        """
        return list(self._buffer)

    def get_log_files(self) -> list[LogFileInfo]:
        """获取可用的历史日志文件列表。

        Returns:
            日志文件信息列表，按修改时间降序排列
        """
        if not self._log_dir.exists():
            return []

        files: list[LogFileInfo] = []
        for file_path in self._log_dir.glob("*.log"):
            if file_path.is_file():
                stat = file_path.stat()
                from datetime import datetime, timezone

                modified_time = datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat()
                files.append(
                    LogFileInfo(
                        filename=file_path.name,
                        size=stat.st_size,
                        modified_time=modified_time,
                        path=str(file_path.relative_to(self._log_dir)),
                    )
                )

        # 按修改时间降序排列
        files.sort(key=lambda f: f.modified_time, reverse=True)
        return files

    def get_log_content(
        self,
        filename: str,
        offset: int = 0,
        limit: int = 8192,
    ) -> LogContentResponse:
        """获取日志文件内容（基于字节偏移量）。

        Args:
            filename: 日志文件名
            offset: 起始偏移量（字节），0 表示从头开始
            limit: 本次返回的最大字节数

        Returns:
            日志内容响应

        Raises:
            FileNotFoundError: 日志文件不存在
            ValueError: 文件名包含非法路径
        """
        # 安全校验：防止路径遍历
        if ".." in filename or "/" in filename or "\\" in filename:
            raise ValueError(f"非法文件名: {filename}")

        file_path = self._log_dir / filename
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"日志文件不存在: {filename}")

        total_size = file_path.stat().st_size

        # 边界处理
        if offset < 0:
            offset = 0
        if offset >= total_size:
            return LogContentResponse(
                content=[],
                offset=offset,
                size=0,
                total_size=total_size,
                has_prev=offset > 0,
                has_next=False,
                next_offset=total_size,
                prev_offset=max(0, offset - limit),
            )

        # 读取内容
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(offset)
            raw = f.read(limit)

        actual_size = len(raw.encode("utf-8"))
        lines = raw.splitlines()

        # 如果不是从文件开头读取，第一行可能是不完整的，去掉它
        if offset > 0 and lines:
            # 检查文件在 offset 位置是否是行首
            with open(file_path, "rb") as fb:
                if offset > 0:
                    fb.seek(offset - 1)
                    prev_byte = fb.read(1)
                    if prev_byte != b"\n":
                        # 不是行首，丢弃第一个不完整行
                        if len(lines) > 1:
                            skipped = len(lines[0].encode("utf-8")) + 1  # +1 for newline
                            offset += skipped
                            actual_size -= skipped
                            lines = lines[1:]
                        else:
                            # 只有一行且不完整
                            lines = []

        next_offset = offset + actual_size
        prev_offset = max(0, offset - limit)

        return LogContentResponse(
            content=lines,
            offset=offset,
            size=actual_size,
            total_size=total_size,
            has_prev=offset > 0,
            has_next=next_offset < total_size,
            next_offset=next_offset,
            prev_offset=prev_offset,
        )


# 全局单例
_log_manager: LogManager | None = None


def get_log_manager() -> LogManager:
    """获取全局日志管理器实例。

    Returns:
        LogManager 单例实例
    """
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    return _log_manager
