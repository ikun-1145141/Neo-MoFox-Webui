"""UI Router 组件。

提供插件前端扩展页面的发现与 Schema 查询接口。

端点（挂载于 /webui/api/ui）：
- GET /discovery                       获取所有已注册页面的元数据列表
- GET /schema/{plugin_name}/{page_id}  获取指定页面的完整 XML 描述
- WS  /ws                              页面热更新通知推送（设计文档 3.2）
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from src.app.plugin_system.api.log_api import get_logger  # type: ignore
from src.core.components.base.router import BaseRouter  # type: ignore
from src.core.utils.security import VerifiedDep, get_api_key  # type: ignore

from ...managers.webui_service_manager import get_webui_service_manager
from ...utils.response import BaseResponse

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin  # type: ignore

logger = get_logger("ui_router")


class UiPageMeta(BaseModel):
    """已注册页面的元数据。"""

    plugin_name: str = Field(description="所属插件名称")
    page_id: str = Field(description="页面唯一标识符")
    title: str = Field(description="页面标题")
    description: str | None = Field(default=None, description="页面描述")
    icon: str | None = Field(default=None, description="Material Symbols 图标名")
    api_base: str | None = Field(default=None, description="API 端点前缀")
    order: int = Field(default=0, description="排序权重")
    registered_at: float = Field(description="注册时间戳")


class UiPageSchema(BaseModel):
    """页面 Schema 响应。"""

    plugin_name: str = Field(description="所属插件名称")
    page_id: str = Field(description="页面唯一标识符")
    page_xml: str = Field(description="完整 XML 页面描述")


class UiRouter(BaseRouter):
    """插件 UI 扩展 Router 组件。"""

    router_name: str = "ui"
    router_description: str = "插件前端扩展页面发现与 Schema 查询 API"
    custom_route_path: str = "/webui/api/ui"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化 UI Router。

        Args:
            plugin: 所属插件实例
        """
        super().__init__(plugin)
        self.service_manager = get_webui_service_manager()

    def register_endpoints(self) -> None:
        """注册 API 端点。"""

        @self.app.get(
            "/discovery",
            response_model=BaseResponse[list[UiPageMeta]],
            dependencies=[VerifiedDep],
        )
        async def discovery() -> BaseResponse[list[UiPageMeta]]:
            """获取所有已注册页面的元数据列表。"""
            try:
                pages = self.service_manager.get_all_pages()
                data = [UiPageMeta(**page) for page in pages]
                return BaseResponse.ok(data=data, message="success")
            except Exception as exc:
                logger.error(f"获取页面发现列表失败: {exc}")
                raise HTTPException(status_code=500, detail="获取页面列表失败")

        @self.app.get(
            "/schema/{plugin_name}/{page_id}",
            response_model=BaseResponse[UiPageSchema],
            dependencies=[VerifiedDep],
        )
        async def get_schema(plugin_name: str, page_id: str) -> BaseResponse[UiPageSchema]:
            """获取指定页面的完整 XML 描述。"""
            registration = self.service_manager.get_page(plugin_name, page_id)
            if registration is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"页面不存在: {plugin_name}/{page_id}",
                )
            data = UiPageSchema(
                plugin_name=registration.plugin_name,
                page_id=registration.page_id,
                page_xml=registration.page_xml,
            )
            return BaseResponse.ok(data=data, message="success")

        @self.app.websocket("/ws")
        async def websocket_ui_endpoint(websocket: WebSocket) -> None:
            """WebSocket 页面热更新通知端点。

            客户端连接后将接收页面更新推送：
            - {"type": "page_updated", "plugin_name": ..., "page_id": ...}

            支持的客户端消息：
            - {"type": "ping"} : 心跳，服务端回 {"type": "pong"}
            """
            # 1. 认证（token 在 query 参数，与日志 WS 端点一致）
            token = websocket.query_params.get("token")
            if token is None:
                await websocket.close(code=1008, reason="缺少认证令牌")
                return
            try:
                await get_api_key(token)
            except HTTPException as exc:
                await websocket.close(code=1008, reason=str(exc.detail))
                return

            # 2. Accept + 注册连接
            await websocket.accept()
            self.service_manager.add_ws_connection(websocket)
            logger.debug("WebSocket UI 连接已建立")

            # 3. 心跳循环（保持连接，直到断开）
            try:
                while True:
                    try:
                        raw = await websocket.receive_text()
                    except WebSocketDisconnect:
                        break
                    try:
                        msg = json.loads(raw) if raw else {}
                    except (json.JSONDecodeError, TypeError):
                        continue
                    if msg.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                pass
            except Exception as exc:
                logger.debug(f"WebSocket UI 连接异常: {exc}")
            finally:
                self.service_manager.remove_ws_connection(websocket)
                logger.debug("WebSocket UI 连接已关闭")

    async def startup(self) -> None:
        """Router 启动钩子。"""
        logger.info("UI Router 已启动")

    async def shutdown(self) -> None:
        """Router 关闭钩子。"""
        logger.info("UI Router 已关闭")
