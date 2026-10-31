"""请求监视器管理器。

校验主程序提供的原生请求快照，并通过 WebUI 公共接口返回数据。
"""

from __future__ import annotations

from src.kernel.llm import get_inspector

from ..utils.request_inspector_types import (
    InspectorClearResult,
    InspectorRecordDetail,
    InspectorRecordsSnapshot,
)


class RequestInspectorManager:
    """请求监视器数据管理器。

    只通过主程序公开接口读取快照，不访问内部缓冲区，也不重复采集请求。
    """

    def list_records(self) -> InspectorRecordsSnapshot:
        """读取当前缓冲区的记录摘要和统计快照。

        Returns:
            经过接口模型校验的当前缓冲区快照。
        """
        return InspectorRecordsSnapshot.model_validate(get_inspector().snapshot())

    def get_record(self, record_id: int) -> InspectorRecordDetail | None:
        """按编号读取单条请求记录详情。

        Args:
            record_id: 请求记录编号。

        Returns:
            经过校验的记录详情；记录已清空或淘汰时返回 None。
        """
        record = get_inspector().get_record(record_id)
        return (
            InspectorRecordDetail.model_validate(record) if record is not None else None
        )

    def clear_records(self) -> InspectorClearResult:
        """清除当前请求快照，但不取消正在执行的模型调用。

        Returns:
            清理数量及更新后的缓冲区版本。
        """
        return InspectorClearResult.model_validate(get_inspector().clear_snapshot())


_request_inspector_manager: RequestInspectorManager | None = None


def get_request_inspector_manager() -> RequestInspectorManager:
    """获取无状态的请求监视器管理器单例。

    Returns:
        请求监视器数据管理器。
    """
    global _request_inspector_manager
    if _request_inspector_manager is None:
        _request_inspector_manager = RequestInspectorManager()
    return _request_inspector_manager
