"""Typed transport contract for native in-memory request inspection."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, JsonValue

InspectorStatus = Literal[
    "captured", "pending", "running", "streaming", "succeeded", "failed", "cancelled"
]


class InspectorOverviewItem(BaseModel):
    label: str
    value: str


class InspectorMessageBlock(BaseModel):
    type: str
    label: str | None = None
    text: str | None = None
    media_type: str | None = None
    title: str | None = None
    meta: str | None = None
    call_id: str | None = None
    name: str | None = None
    arguments_text: str | None = None


class InspectorMessageView(BaseModel):
    index: int
    role: str
    label: str
    meta: str
    blocks: list[InspectorMessageBlock]


class InspectorToolProperty(BaseModel):
    name: str
    type: str
    description: str
    required: bool


class InspectorToolView(BaseModel):
    index: int
    name: str
    kind: str
    description: str
    required: list[str]
    properties: list[InspectorToolProperty]
    raw_json: str


class InspectorRenderedView(BaseModel):
    overview: list[InspectorOverviewItem]
    tools: list[InspectorToolView]
    messages: list[InspectorMessageView]


class InspectorRecordSummary(BaseModel):
    id: int
    version: int
    ts: float
    ts_str: str
    api_name: str
    model: str
    api_provider: str
    request_name: str
    estimated_input_tokens: int | None = None
    msg_count: int
    tool_count: int
    status: InspectorStatus
    logical_request_id: str
    attempt: int
    stream: bool
    started_at: float | None = None
    finished_at: float | None = None
    duration_ms: float | None = None
    first_token_ms: float | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None


class InspectorResponse(BaseModel):
    kind: Literal["chat", "embedding", "rerank"] | None = None
    message: str | None = None
    reasoning_content: str | None = None
    reasoning_parts: list[JsonValue] = Field(default_factory=list)
    tool_calls: list[JsonValue] = Field(default_factory=list)
    usage: dict[str, JsonValue] | None = None
    stop_reason: str | None = None
    embeddings: list[list[float]] = Field(default_factory=list)
    results: list[JsonValue] = Field(default_factory=list)


class InspectorError(BaseModel):
    type: str
    message: str
    status_code: int | None = None


class InspectorCaptureInfo(BaseModel):
    redacted: bool
    raw_bytes: int
    raw_limit_bytes: int
    raw_truncated: bool
    raw_unavailable: bool
    request_unavailable: bool
    metadata_unavailable: bool


class InspectorRecordDetail(InspectorRecordSummary):
    instance_id: str
    params: dict[str, JsonValue]
    metadata: dict[str, JsonValue]
    rendered: InspectorRenderedView
    response: InspectorResponse
    raw_response: JsonValue = None
    raw_events: list[JsonValue]
    error: InspectorError | None = None
    capture_info: InspectorCaptureInfo


class InspectorBufferStats(BaseModel):
    total: int
    by_status: dict[InspectorStatus, int]
    tokens_in: int
    tokens_out: int


class InspectorRecordsSnapshot(BaseModel):
    instance_id: str
    revision: int
    capacity: int
    records: list[InspectorRecordSummary]
    stats: InspectorBufferStats


class InspectorClearResult(BaseModel):
    instance_id: str
    revision: int
    cleared_count: int
