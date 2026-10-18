"""Validate the host's native inspection snapshots at the WebUI API boundary."""

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
    """The host lacks the public native snapshot contract; never fall back."""


def _get_inspector() -> RequestInspector:
    """Resolve lazily so an older host can still serve an authenticated upgrade error."""
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
    """Expose native public APIs; no private buffer access or duplicate collection."""

    def list_records(self) -> InspectorRecordsSnapshot:
        """Return an atomic metadata-only snapshot of the retained buffer."""
        return InspectorRecordsSnapshot.model_validate(_get_inspector().snapshot())

    def get_record(self, record_id: int) -> InspectorRecordDetail | None:
        """Return validated detail, or None if cleared or evicted."""
        record = _get_inspector().get_record(record_id)
        return (
            InspectorRecordDetail.model_validate(record) if record is not None else None
        )

    def clear_records(self) -> InspectorClearResult:
        """Forget snapshots without cancelling the underlying model requests."""
        return InspectorClearResult.model_validate(_get_inspector().clear_snapshot())


_request_inspector_manager: RequestInspectorManager | None = None


def get_request_inspector_manager() -> RequestInspectorManager:
    """Return the stateless WebUI transport manager."""
    global _request_inspector_manager
    if _request_inspector_manager is None:
        _request_inspector_manager = RequestInspectorManager()
    return _request_inspector_manager
