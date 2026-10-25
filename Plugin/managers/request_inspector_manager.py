"""请求监视器管理器。

    校验主程序提供的原生请求快照，并通过 WebUI 公共接口返回数据。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    from src.kernel.llm import get_inspector as _host_get_inspector
except ImportError:
    _host_get_inspector = None

if TYPE_CHECKING:
    from src.kernel.llm.request_inspector import RequestInspector
from ..utils.request_inspector_types import (
    InspectorClearResult,
    InspectorRecordDetail,
    InspectorRecordsSnapshot,
)


class InspectorUnavailableError(RuntimeError):
    """主程序未提供请求监视器所需公共接口时抛出的异常。"""


def _get_inspector() -> RequestInspector:
    """获取主程序的原生请求检查器，并确认其公开接口完整。

        返回：
            RequestInspector：主程序提供的原生请求检查器。

        异常：
            InspectorUnavailableError：主程序未提供检查器或缺少所需公共方法。
    """
    try:
        if _host_get_inspector is None:
            raise InspectorUnavailableError("Native request inspector unavailable")
        inspector = _host_get_inspector()
    except (ImportError, AttributeError) as exc:
        raise InspectorUnavailableError("Native request inspector unavailable") from exc
    if not all(
        callable(getattr(inspector, method, None))
        for method in ("snapshot", "get_record", "clear_snapshot")
    ):
        raise InspectorUnavailableError("Native request inspector unavailable")
    return inspector


class RequestInspectorManager:
    """请求监视器数据管理器。

        只通过主程序公开接口读取快照，不访问内部缓冲区，也不重复采集请求。
    """

    def list_records(self) -> InspectorRecordsSnapshot:
        """读取当前缓冲区的记录摘要和统计快照。

            返回：
                InspectorRecordsSnapshot：经过接口模型校验的当前缓冲区快照。
        """
        return InspectorRecordsSnapshot.model_validate(_get_inspector().snapshot())

    def get_record(self, record_id: int) -> InspectorRecordDetail | None:
        """按编号读取单条请求记录详情。

            参数：
                record_id：请求记录编号。

            返回：
                InspectorRecordDetail | None：经过校验的记录详情；记录已清空或淘汰时返回 None。
        """
        record = _get_inspector().get_record(record_id)
        return (
            InspectorRecordDetail.model_validate(record) if record is not None else None
        )

    def clear_records(self) -> InspectorClearResult:
        """清除当前请求快照，但不取消正在执行的模型调用。

            返回：
                InspectorClearResult：清理数量及更新后的缓冲区版本。
        """
        return InspectorClearResult.model_validate(_get_inspector().clear_snapshot())


_request_inspector_manager: RequestInspectorManager | None = None


def get_request_inspector_manager() -> RequestInspectorManager:
    """获取无状态的请求监视器管理器单例。

        返回：
            RequestInspectorManager：请求监视器数据管理器。
    """
    global _request_inspector_manager
    if _request_inspector_manager is None:
        _request_inspector_manager = RequestInspectorManager()
    return _request_inspector_manager
