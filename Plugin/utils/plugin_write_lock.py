"""Serialize WebUI plugin writes, including market installs and lifecycle actions."""
from __future__ import annotations

import asyncio
from functools import wraps
from threading import Lock
from typing import Any, Callable


class PluginWriteLock:
    """Cancellation-safe process lock usable across the host's event loops."""

    def __init__(self) -> None:
        self._lock = Lock()

    async def __aenter__(self) -> None:
        # Never acquire in a worker: cancellation could otherwise strand the lock.
        while not self._lock.acquire(blocking=False):
            await asyncio.sleep(0.05)

    async def __aexit__(self, *args: Any) -> None:
        self._lock.release()


plugin_write_lock = PluginWriteLock()


def serialized_plugin_write(method: Callable) -> Callable:
    """Serialize a public lifecycle method without nesting host API locks."""
    @wraps(method)
    async def wrapped(*args: Any, **kwargs: Any) -> Any:
        async with plugin_write_lock:
            return await method(*args, **kwargs)
    return wrapped
