"""留言板示例 Router。

为 ui_demo_plugin 的前端页面提供后端 API：
- GET  /webui/api/ui-demo/list   返回留言列表
- POST /webui/api/ui-demo/greet  追加一条留言

数据仅存于内存（进程级），重启清空，仅用于演示链路。
响应格式遵循 WebUI 约定 ``{"code": 200, "data": ..., "message": ...}``，
前端 axios 拦截器会自动解包 ``data`` 字段。

权限控制（设计文档 8.2）：
端点通过依赖 ``_require_self_plugin`` 校验请求头 ``X-Plugin-Name``，
确保只有本插件注册的前端页面能调用这些 API，防止跨插件访问。
（本示例采用自包含的内联校验，便于作为独立插件部署；
WebUI 另在 Plugin/utils/api_permission.py 提供了可复用的通用版本。）
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel, Field

from src.app.plugin_system.api.log_api import get_logger  # type: ignore
from src.core.components.base.router import BaseRouter  # type: ignore
from src.core.utils.security import VerifiedDep  # type: ignore

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin  # type: ignore

logger = get_logger("ui_demo_router")

# 进程级内存存储（演示用，重启清空）
_messages: list[dict[str, Any]] = []


class GreetRequest(BaseModel):
    """提交留言请求体。"""

    name: str = Field(min_length=2, max_length=20, description="昵称")
    message: str = Field(min_length=1, max_length=200, description="留言内容")


class UiDemoRouter(BaseRouter):
    """留言板示例 Router 组件。"""

    router_name: str = "ui-demo"
    router_description: str = "WebUI 扩展示例的后端 API"
    custom_route_path: str = "/webui/api/ui-demo"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化 Router。

        Args:
            plugin: 所属插件实例
        """
        super().__init__(plugin)

    def _require_self_plugin(
        self,
        x_plugin_name: str | None = Header(default=None, alias="X-Plugin-Name"),
    ) -> None:
        """校验请求来自本插件注册的页面（设计文档 8.2）。

        Raises:
            HTTPException(403): X-Plugin-Name 头缺失或与本插件名不匹配。
        """
        expected = self.plugin.plugin_name  # "ui_demo_plugin"
        if not x_plugin_name:
            raise HTTPException(status_code=403, detail="缺少 X-Plugin-Name 头")
        if x_plugin_name != expected:
            raise HTTPException(
                status_code=403,
                detail=f"插件 {x_plugin_name} 无权调用此端点（需 {expected}）",
            )

    def register_endpoints(self) -> None:
        """注册 API 端点。"""

        @self.app.get(
            "/list",
            dependencies=[VerifiedDep, Depends(self._require_self_plugin)],
        )
        async def list_messages() -> dict[str, Any]:
            """返回全部留言（最新的在前）。"""
            return {
                "code": 200,
                "data": list(reversed(_messages)),
                "message": "ok",
            }

        @self.app.post(
            "/greet",
            dependencies=[VerifiedDep, Depends(self._require_self_plugin)],
        )
        async def add_message(payload: GreetRequest) -> dict[str, Any]:
            """追加一条留言。"""
            try:
                record = {
                    "name": payload.name,
                    "message": payload.message,
                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                _messages.append(record)
                logger.info(f"收到留言: {payload.name} -> {payload.message}")
                return {"code": 200, "data": record, "message": "留言成功"}
            except Exception as exc:
                logger.error(f"保存留言失败: {exc}")
                raise HTTPException(status_code=500, detail="保存留言失败")
