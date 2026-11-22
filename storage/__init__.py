"""存储层模块。

提供统一的数据持久化接口。
"""

from .base import BaseStorage
from .settings import SettingsStorage

__all__ = ["BaseStorage", "SettingsStorage"]
