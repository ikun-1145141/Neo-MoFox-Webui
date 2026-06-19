"""Demo UI Router - 为 XML 前端提供自定义 API 端点。

注册 /webui/api/demo-ui/ 下的路由，供 XML 页面的 <api> 模板调用。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field
from src.core.components.base.router import BaseRouter  # type: ignore

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin  # type: ignore


# === Pydantic 模型 ===


class ItemCreate(BaseModel):
    """创建条目的请求体。"""

    name: str = Field(..., description="条目名称", min_length=1, max_length=100)


class ItemResponse(BaseModel):
    """条目响应。"""

    id: int
    name: str
    created_at: str


class BaseResponse(BaseModel):
    """统一响应结构。"""

    code: int = 200
    data: Any = None
    message: str = "success"


# === 内存数据存储 ===

_items: list[dict[str, Any]] = []
_next_id: int = 1


# === Router 组件 ===


class DemoUIRouter(BaseRouter):
    """Demo UI 自定义路由。

    提供条目的增删查改接口，供 XML 前端的 API 模板调用。
    """

    router_name: str = "demo_ui_router"
    router_description: str = "Demo UI 前端交互 API"

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化路由。"""
        super().__init__(plugin)

    def register_endpoints(self) -> None:
        """注册 FastAPI 端点。"""

        @self.app.get("/webui/api/demo-ui/items")
        async def list_items() -> BaseResponse:
            """获取所有条目列表。"""
            return BaseResponse(data=_items)

        @self.app.post("/webui/api/demo-ui/items")
        async def add_item(body: ItemCreate) -> BaseResponse:
            """添加一个新条目。"""
            global _next_id
            from datetime import datetime

            item = {
                "id": _next_id,
                "name": body.name,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            _items.append(item)
            _next_id += 1
            return BaseResponse(data=_items, message="添加成功")

        @self.app.delete("/webui/api/demo-ui/items/{item_id}")
        async def delete_item(item_id: int) -> BaseResponse:
            """删除指定条目。"""
            global _items
            before = len(_items)
            _items = [i for i in _items if i["id"] != item_id]
            if len(_items) == before:
                return BaseResponse(code=404, message=f"条目 {item_id} 不存在")
            return BaseResponse(data=_items, message="删除成功")

        @self.app.get("/webui/api/demo-ui/stats")
        async def get_stats() -> BaseResponse:
            """获取统计信息。"""
            return BaseResponse(
                data={
                    "total_items": len(_items),
                    "latest_item": _items[-1]["name"] if _items else None,
                }
            )
