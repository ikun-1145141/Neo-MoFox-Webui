"""Demo HTML UI Router - 为 HTML 前端提供自定义 API 端点。

注册 /demo-html/ 下的路由，供 HTML 页面的 sys.request() 调用。
所有响应遵循 BaseResponse 协议 { code, data, message }，
前端 sys.request() 会自动解包到 .data 字段。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from datetime import datetime
import random

from pydantic import BaseModel, Field
from src.core.components.base.router import BaseRouter  # type: ignore

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin  # type: ignore


# === Pydantic 模型 ===


class TaskCreate(BaseModel):
    """创建任务的请求体。"""

    title: str = Field(..., description="任务标题", min_length=1, max_length=100)
    priority: str = Field(default="medium", description="优先级: low/medium/high")


class BaseResponse(BaseModel):
    """统一响应结构。"""

    code: int = 200
    data: Any = None
    message: str = "success"


# === 内存数据存储 ===

_tasks: list[dict[str, Any]] = [
    {
        "id": 1,
        "title": "学习 sys.vars 读写",
        "priority": "high",
        "done": False,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    },
    {
        "id": 2,
        "title": "尝试 sys.ui.notify",
        "priority": "medium",
        "done": True,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    },
]
_next_id: int = 3


# === Router 组件 ===


class DemoHTMLRouter(BaseRouter):
    """Demo HTML 自定义路由。

    提供任务管理的 CRUD 接口 + 系统监控数据接口，
    供 HTML 前端通过 sys.request() 调用。
    """

    name: str = "demo_html_router"
    description: str = "Demo HTML 前端交互 API"

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        super().__init__(plugin)

    def register_endpoints(self) -> None:
        """注册 FastAPI 端点。"""

        @self.app.get("/demo-html/tasks")
        async def list_tasks() -> BaseResponse:
            """获取所有任务列表。"""
            return BaseResponse(data=_tasks)

        @self.app.post("/demo-html/tasks")
        async def create_task(body: TaskCreate) -> BaseResponse:
            """创建新任务。"""
            global _next_id
            task = {
                "id": _next_id,
                "title": body.title,
                "priority": body.priority,
                "done": False,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            _tasks.append(task)
            _next_id += 1
            return BaseResponse(data=_tasks, message="任务创建成功")

        @self.app.patch("/demo-html/tasks/{task_id}/toggle")
        async def toggle_task(task_id: int) -> BaseResponse:
            """切换任务完成状态。"""
            for t in _tasks:
                if t["id"] == task_id:
                    t["done"] = not t["done"]
                    return BaseResponse(data=_tasks, message="状态已切换")
            return BaseResponse(code=404, message=f"任务 {task_id} 不存在")

        @self.app.delete("/demo-html/tasks/{task_id}")
        async def delete_task(task_id: int) -> BaseResponse:
            """删除任务。"""
            global _tasks
            before = len(_tasks)
            _tasks = [t for t in _tasks if t["id"] != task_id]
            if len(_tasks) == before:
                return BaseResponse(code=404, message=f"任务 {task_id} 不存在")
            return BaseResponse(data=_tasks, message="任务已删除")

        @self.app.get("/demo-html/stats")
        async def get_stats() -> BaseResponse:
            """获取统计信息（供 sys-table 与 sys-chart 使用）。"""
            total = len(_tasks)
            done = sum(1 for t in _tasks if t["done"])
            pending = total - done
            return BaseResponse(
                data={
                    "total": total,
                    "done": done,
                    "pending": pending,
                    "by_priority": {
                        "high": sum(1 for t in _tasks if t["priority"] == "high"),
                        "medium": sum(1 for t in _tasks if t["priority"] == "medium"),
                        "low": sum(1 for t in _tasks if t["priority"] == "low"),
                    },
                }
            )

        @self.app.get("/demo-html/metrics")
        async def get_metrics() -> BaseResponse:
            """返回 7 天系统监控数据（供 sys-chart 渲染）。

            返回的数据结构直接可用作 sys-chart 的简化格式。
            """
            days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            return BaseResponse(
                data={
                    "xAxis": days,
                    "series": [
                        {"name": "CPU 使用率(%)", "data": [random.randint(20, 85) for _ in range(7)]},
                        {"name": "内存使用率(%)", "data": [random.randint(40, 90) for _ in range(7)]},
                        {"name": "磁盘 I/O(%)", "data": [random.randint(10, 60) for _ in range(7)]},
                    ],
                    "title": "系统资源监控（最近 7 天）",
                }
            )

        @self.app.get("/demo-html/echo")
        async def echo(message: str = "hello") -> BaseResponse:
            """简单回显接口（用于演示 sys.request 的 GET 调用）。"""
            return BaseResponse(
                data={
                    "echo": message,
                    "timestamp": datetime.now().isoformat(),
                    "plugin": "demo_html_plugin",
                }
            )
