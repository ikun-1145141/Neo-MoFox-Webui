"""存储基类。

基于 Neo-MoFox 的 json_storage 封装统一的数据持久化接口。
所有 Storage 类必须继承此类。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.app.plugin_system.api.storage_api import save_json, load_json, delete_json, exists_json


class BaseStorage:
    """存储基类。

    提供统一的 JSON 数据持久化接口。
    所有数据存储在 data/json_storage/WebUI_data/ 目录下。

    Attributes:
        store_name: 存储命名空间，固定为 "WebUI_data"
        data_key: 数据键名，对应文件名（不含 .json 后缀）

    Examples:
        >>> class MyStorage(BaseStorage):
        ...     def __init__(self):
        ...         super().__init__(data_key="my_data")
        ...
        ...     async def get_value(self) -> dict:
        ...         return await self.load() or {}
    """

    # 所有 WebUI 数据使用统一的命名空间
    store_name: str = "WebUI_data"

    def __init__(self, data_key: str) -> None:
        """初始化存储。

        Args:
            data_key: 数据键名，对应文件名（不含 .json 后缀）
        """
        self.data_key = data_key

    async def save(self, data: dict[str, Any]) -> None:
        """保存数据。

        Args:
            data: 要保存的数据字典

        Examples:
            >>> await storage.save({"key": "value"})
        """
        await save_json(self.store_name, self.data_key, data)

    async def load(self) -> dict[str, Any] | None:
        """加载数据。

        Returns:
            数据字典；键不存在时返回 None

        Examples:
            >>> data = await storage.load()
            >>> if data is None:
            ...     # 数据不存在，使用默认值
            ...     data = {}
        """
        return await load_json(self.store_name, self.data_key)

    async def delete(self) -> bool:
        """删除数据。

        Returns:
            是否成功删除（键不存在时返回 False）

        Examples:
            >>> success = await storage.delete()
        """
        return await delete_json(self.store_name, self.data_key)

    async def exists(self) -> bool:
        """检查数据是否存在。

        Returns:
            是否存在

        Examples:
            >>> if await storage.exists():
            ...     # 数据存在
            ...     pass
        """
        return await exists_json(self.store_name, self.data_key)
