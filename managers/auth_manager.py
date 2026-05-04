"""认证管理器。

负责 WebUI 登录密码校验与会话令牌发放。
"""

from __future__ import annotations

import secrets

from src.core.config.core_config import get_core_config


class AuthManager:
    """认证管理器。

    登录口令来源于 Neo-MoFox `core.toml` 的 `[http_router].api_keys`。
    当前阶段采用“口令即令牌”的策略，便于与全局 `X-API-Key` 校验机制对齐。
    """

    async def login(self, password: str) -> str:
        """校验密码并返回令牌。

        Args:
            password: 前端提交的登录密码。

        Returns:
            str: 可用于后续请求认证的令牌。

        Raises:
            RuntimeError: 核心配置未初始化。
            ValueError: 未配置可用口令或密码错误。
        """
        config = get_core_config()
        valid_keys = config.http_router.api_keys

        if not valid_keys:
            raise ValueError("服务未配置登录口令，请在 config/core.toml 中设置 [http_router].api_keys")

        for key in valid_keys:
            if secrets.compare_digest(password, key):
                return key

        raise ValueError("密码错误")


_auth_manager: AuthManager | None = None


def get_auth_manager() -> AuthManager:
    """获取认证管理器单例。"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager
