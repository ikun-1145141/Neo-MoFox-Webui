"""API 权限校验工具（设计文档 8.2 API 权限控制）。

供插件在自己的端点上使用，校验请求头 ``X-Plugin-Name`` 是否匹配期望的插件名，
防止某插件注册的前端页面跨插件调用其他插件的 API。

WebUI 前端在发起声明式 API 调用时，会自动注入 ``X-Plugin-Name`` 头
（值为注册该页面的插件名，见 frontend/src/utils/apiExecutor.ts）。
"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException


def verify_plugin_header(
    expected: str,
    x_plugin_name: str | None = Header(default=None, alias="X-Plugin-Name"),
) -> None:
    """校验 ``X-Plugin-Name`` 头匹配期望插件名。

    Args:
        expected: 期望的插件名（通常为端点所属插件自身的 plugin_name）。
        x_plugin_name: 请求头值，由 FastAPI 自动注入。

    Raises:
        HTTPException(403): 头缺失或与期望值不匹配。
    """
    if not x_plugin_name:
        raise HTTPException(status_code=403, detail="缺少 X-Plugin-Name 头")
    if x_plugin_name != expected:
        raise HTTPException(
            status_code=403,
            detail=f"插件 {x_plugin_name} 无权调用此端点（需 {expected}）",
        )


def require_plugin_header(expected: str):
    """构造一个校验 ``X-Plugin-Name`` 的 FastAPI 依赖。

    返回值可直接放入端点的 ``dependencies`` 列表。

    Args:
        expected: 期望的插件名。

    Returns:
        一个 ``Depends(...)`` 对象。

    用法::

        from .api_permission import require_plugin_header

        @router.post("/greet", dependencies=[VerifiedDep, require_plugin_header("my_plugin")])
        async def greet(...): ...
    """

    def _dep(
        x_plugin_name: str | None = Header(default=None, alias="X-Plugin-Name"),
    ) -> None:
        verify_plugin_header(expected, x_plugin_name)

    return Depends(_dep)
