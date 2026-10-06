"""Bound and authenticate import bodies before FastAPI's multipart spooler runs."""
from __future__ import annotations

from fastapi import HTTPException
from starlette.datastructures import Headers
from starlette.formparsers import MultiPartException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.core.utils.security import get_api_key

from .plugin_package import MAX_PACKAGE_BYTES
from .response import BaseResponse


class PluginImportUploadGuard:
    """Apply only to the import upload, retaining VerifiedDep on all endpoints.

    Content-Length is merely an early rejection optimization; chunked bodies are
    counted as they arrive too. Raising MultiPartException makes Starlette close
    its partial spooled files. Its parser error response is mapped to our 413.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (scope["type"] != "http" or scope.get("method") != "POST"
                or not scope.get("path", "").rstrip("/").endswith("/import/prepare")):
            await self.app(scope, receive, send)
            return

        async def reject(code: int, message: str) -> None:
            response = JSONResponse(status_code=code, content=BaseResponse.error(code=code, message=message).model_dump())
            await response(scope, receive, send)

        headers = Headers(scope=scope)
        try:
            await get_api_key(headers.get("x-api-key", ""))
        except HTTPException as error:
            await reject(error.status_code, str(error.detail))
            return
        # One package plus a bounded allowance for multipart headers/boundaries.
        request_limit = MAX_PACKAGE_BYTES + 64 * 1024
        length = headers.get("content-length")
        if length is not None:
            try:
                size = int(length)
            except ValueError:
                await reject(400, "无效的 Content-Length")
                return
            if size < 0 or size > request_limit:
                await reject(413, "上传请求超过 50 MiB 插件包限制")
                return
        received = 0
        exceeded = False
        rejected = False

        async def limited_receive() -> Message:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > request_limit:
                    exceeded = True
                    raise MultiPartException("上传请求超过大小限制")
            return message

        async def limited_send(message: Message) -> None:
            nonlocal rejected
            if exceeded:
                if not rejected:
                    rejected = True
                    await reject(413, "上传请求超过 50 MiB 插件包限制")
            else:
                await send(message)

        await self.app(scope, limited_receive, limited_send)
