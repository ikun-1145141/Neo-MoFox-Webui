"""日志 Router 组件。

提供 WebSocket 实时日志推送和 HTTP 历史日志查询接口。
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from fastapi import Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from src.core.components.base.router import BaseRouter
from src.app.plugin_system.api.log_api import get_logger
from src.core.utils.security import VerifiedDep, verify_websocket_token

from ...managers.log_manager import get_log_manager
from ...utils.response import BaseResponse

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin

logger = get_logger("webui.log_router", display="WebUI.LogRouter")


# ========== Pydantic 模型 ==========


class LogFileInfo(BaseModel):
    """日志文件信息模型。

    Attributes:
        filename: 文件名
        size: 文件大小（字节）
        modified_time: 最后修改时间（ISO 格式）
        path: 日志文件相对路径
    """

    filename: str = Field(description="日志文件名")
    size: int = Field(description="文件大小（字节）")
    modified_time: str = Field(description="最后修改时间（ISO 格式）")
    path: str = Field(description="日志文件相对路径")


class LogFileListResponse(BaseModel):
    """日志文件列表响应。

    Attributes:
        files: 日志文件列表
        log_dir: 日志目录路径
    """

    files: list[LogFileInfo] = Field(description="日志文件列表")
    log_dir: str = Field(description="日志目录路径")


class LogSearchMatch(BaseModel):
    """日志搜索命中区间。"""

    start: int = Field(description="命中起始位置")
    end: int = Field(description="命中结束位置")


class StructuredLogLine(BaseModel):
    """结构化日志行。"""

    raw: str = Field(description="原始日志文本")
    timestamp: str = Field(default="", description="日志时间")
    level: str = Field(default="INFO", description="日志级别")
    level_label: str = Field(default="信息", description="日志级别中文标签")
    tone: str = Field(default="info", description="前端渲染色调")
    color: str = Field(default="#0075de", description="前端强调色")
    source: str = Field(default="", description="日志来源")
    message: str = Field(description="日志正文")
    badges: list[str] = Field(default_factory=list, description="日志标签")
    search_matches: list[LogSearchMatch] = Field(default_factory=list, description="搜索命中")


class LogContentResponse(BaseModel):
    """日志内容响应模型。

    Attributes:
        content: 日志内容文本行
        entries: 结构化日志行
        offset: 当前偏移量
        size: 本次返回的字节数
        total_size: 日志文件总大小
        has_prev: 是否可向前加载更多
        has_next: 是否可向后加载更多
        next_offset: 下次向后请求的偏移量
        prev_offset: 下次向前请求的偏移量
        total_matches: 当前分块内搜索命中行数
        query: 搜索关键词
    """

    content: list[str] = Field(description="日志内容文本行")
    entries: list[StructuredLogLine] = Field(default_factory=list, description="结构化日志行")
    offset: int = Field(description="当前偏移量")
    size: int = Field(description="本次返回的字节数")
    total_size: int = Field(description="日志文件总大小")
    has_prev: bool = Field(description="是否可向前加载更多")
    has_next: bool = Field(description="是否可向后加载更多")
    next_offset: int = Field(description="下次向后请求的偏移量")
    prev_offset: int = Field(description="下次向前请求的偏移量")
    total_matches: int = Field(default=0, description="当前分块内搜索命中行数")
    query: str = Field(default="", description="搜索关键词")


# ========== Router ==========


class LogRouter(BaseRouter):
    """日志 Router 组件。

    提供以下接口：
    - WS  /ws          - WebSocket 实时日志推送
    - GET /files       - 获取日志文件列表
    - GET /content     - 获取日志文件内容（支持偏移量分块）
    """

    name: str = "log"
    description: str = "日志查看 API（WebSocket + HTTP）"
    custom_route_path: str = "/webui/api/log"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化日志 Router。

        Args:
            plugin: 所属插件实例
        """
        super().__init__(plugin)

    def register_endpoints(self) -> None:
        """注册日志相关的 API 端点。"""

        @self.app.websocket("/ws")
        async def websocket_log_endpoint(websocket: WebSocket) -> None:
            """WebSocket 实时日志推送端点。

            客户端连接后将持续接收实时日志推送。
            支持的客户端消息：
            - {"type": "ping"} : 心跳
            - {"type": "set_level_filter", "levels": ["INFO", "ERROR"]} : 设置级别过滤
            """
            if not await verify_websocket_token(websocket):
                return

            await websocket.accept()

            log_mgr = get_log_manager()
            level_filter: set[str] | None = None

            # 注册客户端队列（async，返回新队列）
            queue = await log_mgr.register_client()

            try:
                # 发送缓冲区中的历史日志（最近的）
                recent_logs = log_mgr.get_buffer()
                if recent_logs:
                    await websocket.send_json({
                        "type": "history_batch",
                        "data": recent_logs,
                    })

                # 并发处理：接收客户端消息 + 推送日志
                async def _send_logs() -> None:
                    """持续从队列中取出日志并推送给客户端。"""
                    while True:
                        log_entry = await queue.get()
                        # 应用级别过滤
                        if level_filter and log_entry.get("level") not in level_filter:
                            continue
                        try:
                            await websocket.send_json({
                                "type": "realtime_log",
                                "data": log_entry,
                            })
                        except Exception:
                            break

                async def _receive_messages() -> None:
                    """持续接收客户端消息（心跳、过滤设置等）。"""
                    nonlocal level_filter
                    while True:
                        try:
                            raw = await websocket.receive_text()
                            msg = json.loads(raw)
                        except WebSocketDisconnect:
                            break
                        except (json.JSONDecodeError, TypeError):
                            continue

                        msg_type = msg.get("type", "")
                        if msg_type == "ping":
                            await websocket.send_json({"type": "pong"})
                        elif msg_type == "set_level_filter":
                            levels = msg.get("levels")
                            if isinstance(levels, list) and levels:
                                level_filter = {lv.upper() for lv in levels}
                            else:
                                level_filter = None

                send_task = asyncio.create_task(_send_logs())
                recv_task = asyncio.create_task(_receive_messages())

                done, pending = await asyncio.wait(
                    [send_task, recv_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()

                await asyncio.gather(*done, return_exceptions=True)
                await asyncio.gather(*pending, return_exceptions=True)

            except WebSocketDisconnect:
                pass
            except Exception as e:
                logger.debug(f"WebSocket 日志连接异常: {e}")
            finally:
                await log_mgr.unregister_client(queue)

        @self.app.get("/files", response_model=BaseResponse[LogFileListResponse], dependencies=[VerifiedDep])
        async def get_log_files() -> BaseResponse[LogFileListResponse]:
            """获取可用的历史日志文件列表。

            Returns:
                包含日志文件列表的响应
            """
            try:
                log_mgr = get_log_manager()
                files = log_mgr.get_log_files()
                result = LogFileListResponse(
                    files=[
                        LogFileInfo.model_validate(
                            file.model_dump() if isinstance(file, BaseModel) else file
                        )
                        for file in files
                    ],
                    log_dir=str(log_mgr._log_dir),
                )
                return BaseResponse.ok(data=result, message="获取日志文件列表成功")
            except Exception as e:
                logger.error(f"获取日志文件列表失败: {e}")
                return BaseResponse.error(code=500, message=f"获取日志文件列表失败: {e}")

        @self.app.get("/content", response_model=BaseResponse[LogContentResponse], dependencies=[VerifiedDep])
        async def get_log_content(
            filename: str = Query(description="日志文件名"),
            offset: int = Query(default=0, ge=0, description="偏移量（字节）"),
            limit: int = Query(default=65536, ge=1024, le=1048576, description="返回大小限制（字节）"),
            query: str = Query(default="", max_length=128, description="日志内容搜索关键词"),
            levels: list[str] | None = Query(default=None, description="日志级别过滤"),
        ) -> BaseResponse[LogContentResponse]:
            """获取日志文件内容（基于字节偏移量的分块获取）。

            Args:
                filename: 日志文件名
                offset: 偏移量（字节），0 表示从头开始
                limit: 本次返回的内容大小限制（字节），默认 64KB
                query: 日志内容搜索关键词
                levels: 日志级别过滤

            Returns:
                包含日志内容和分页信息的响应
            """
            try:
                log_mgr = get_log_manager()
                result = log_mgr.get_log_content(
                    filename=filename,
                    offset=offset,
                    limit=limit,
                    query=query,
                    levels=levels,
                )
                return BaseResponse.ok(data=result, message="获取日志内容成功")
            except FileNotFoundError:
                return BaseResponse.error(code=404, message="日志文件不存在")
            except ValueError as e:
                return BaseResponse.error(code=400, message=str(e))
            except Exception as e:
                logger.error(f"获取日志内容失败: {e}")
                return BaseResponse.error(code=500, message=f"获取日志内容失败: {e}")
