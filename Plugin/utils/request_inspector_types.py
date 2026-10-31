"""原生内存请求监视器的数据传输模型。

    定义路由响应使用的记录摘要、详情、状态及缓冲区结构。
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, JsonValue

InspectorStatus = Literal[
    "captured", "pending", "running", "streaming", "succeeded", "failed", "cancelled"
]


class InspectorOverviewItem(BaseModel):
    """请求概览中的单项展示信息。

    Attributes:
        label: 概览项的显示名称。
        value: 供界面直接展示的文本值。
    """

    label: str
    value: str


class InspectorMessageBlock(BaseModel):
    """请求消息中可独立展示的内容块。

    Attributes:
        type: 内容块类型，例如文本、媒体、工具调用或工具结果。
        label: 内容块的显示标签。
        text: 已采集的文本内容。
        media_type: 媒体内容的类型。
        title: 媒体或内容块的标题。
        meta: 内容块的补充说明。
        call_id: 关联的工具调用标识。
        name: 关联的工具名称。
        arguments_text: 工具调用参数的原始文本。
    """

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
    """用于消息卡片展示的单条请求消息。

    Attributes:
        index: 消息在请求中的序号。
        role: 消息角色。
        label: 角色的显示名称。
        meta: 消息的补充说明。
        blocks: 按原顺序排列的消息内容块。
    """

    index: int
    role: str
    label: str
    meta: str
    blocks: list[InspectorMessageBlock]


class InspectorToolProperty(BaseModel):
    """工具定义中单个参数字段的展示信息。

    Attributes:
        name: 参数字段名称。
        type: 参数字段的数据类型。
        description: 参数字段的说明。
        required: 该字段是否为必填参数。
    """

    name: str
    type: str
    description: str
    required: bool


class InspectorToolView(BaseModel):
    """用于界面展示的工具定义。

    Attributes:
        index: 工具在请求中的序号。
        name: 工具名称。
        kind: 工具类型。
        description: 工具的功能说明。
        required: 必填参数名称列表。
        properties: 工具参数字段的展示信息。
        raw_json: 已脱敏工具定义的完整 JSON 文本。
    """

    index: int
    name: str
    kind: str
    description: str
    required: list[str]
    properties: list[InspectorToolProperty]
    raw_json: str


class InspectorRenderedView(BaseModel):
    """主程序生成的请求结构化展示数据。

    Attributes:
        overview: 请求参数的概览信息。
        tools: 请求中的工具定义。
        messages: 请求消息及其内容块。
    """

    overview: list[InspectorOverviewItem]
    tools: list[InspectorToolView]
    messages: list[InspectorMessageView]


class InspectorRecordSummary(BaseModel):
    """请求记录摘要，用于列表展示和生命周期状态同步。

    Attributes:
        id: 缓冲区内单调递增的记录编号。
        version: 当前记录的更新版本。
        ts: 记录创建时的时间戳，单位为秒。
        ts_str: 记录创建时间的文本表示。
        api_name: 模型调用使用的接口名称。
        model: 请求使用的模型标识。
        api_provider: 模型供应商信息。
        request_name: 业务侧提供的请求名称。
        estimated_input_tokens: 估算的输入令牌数，缺失时为 None。
        msg_count: 请求消息数量。
        tool_count: 请求工具定义数量。
        status: 当前请求的生命周期状态。
        logical_request_id: 用于关联同一逻辑请求不同尝试的标识。
        attempt: 当前请求的尝试序号。
        stream: 是否为流式调用。
        started_at: 调用开始时间戳，单位为秒。
        finished_at: 调用结束时间戳，单位为秒。
        duration_ms: 调用耗时，单位为毫秒。
        first_token_ms: 接收首个内容的耗时，单位为毫秒。
        tokens_in: 实际输入令牌数，供应商未提供时为 None。
        tokens_out: 实际输出令牌数，供应商未提供时为 None。
    """

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
    """主程序采集的标准化模型响应，支持保留流式部分结果。

    Attributes:
        kind: 响应类型，可为对话、向量或重排序。
        message: 对话响应的文本正文。
        reasoning_content: 已返回的推理文本。
        reasoning_parts: 已返回的结构化推理内容块。
        tool_calls: 模型返回的工具调用，不代表工具已实际执行。
        usage: 供应商提供的实际用量信息。
        stop_reason: 供应商返回的结束原因。
        embeddings: 向量接口返回的向量列表。
        results: 重排序接口返回的结果列表。
    """

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
    """请求执行失败时采集的错误信息。

    Attributes:
        type: 错误类型。
        message: 进入缓冲区前已脱敏的错误说明。
        status_code: 可获取的 HTTP 状态码，缺失时为 None。
    """

    type: str
    message: str
    status_code: int | None = None


class InspectorCaptureInfo(BaseModel):
    """请求采集数据的脱敏、可用性及原始数据预算标记。

    Attributes:
        redacted: 是否发生过敏感内容替换。
        raw_bytes: 已保存原始 SDK 数据的字节数。
        raw_limit_bytes: 原始 SDK 响应和流事件共用的字节预算。
        raw_truncated: 原始 SDK 数据是否因预算限制而截断。
        raw_unavailable: 是否存在无法安全序列化的原始 SDK 数据。
        request_unavailable: 是否存在无法安全序列化的请求参数。
        metadata_unavailable: 是否存在无法安全序列化的请求元数据。
    """

    redacted: bool
    raw_bytes: int
    raw_limit_bytes: int
    raw_truncated: bool
    raw_unavailable: bool
    request_unavailable: bool
    metadata_unavailable: bool


class InspectorRecordDetail(InspectorRecordSummary):
    """完整请求记录，继承摘要中的标识、状态和时间信息。

    Attributes:
        instance_id: 主程序当前请求缓冲区的实例标识。
        params: 保留最终 SDK 调用层级的已脱敏请求参数。
        metadata: 独立于请求参数保存的元数据。
        rendered: 请求概览、工具定义和消息的结构化展示数据。
        response: 已采集的标准化模型响应。
        raw_response: 已保存的原始 SDK 响应，不是网络抓包。
        raw_events: 按顺序保存的原始 SDK 流事件。
        error: 执行错误信息，无错误时为 None。
        capture_info: 采集完整性和原始数据预算信息。
    """

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
    """当前内存缓冲区中保留记录的统计摘要。

    Attributes:
        total: 当前保留的记录总数。
        by_status: 按生命周期状态分组的记录数量。
        tokens_in: 当前保留记录中已知实际输入令牌数的合计。
        tokens_out: 当前保留记录中已知实际输出令牌数的合计。
    """

    total: int
    by_status: dict[InspectorStatus, int]
    tokens_in: int
    tokens_out: int


class InspectorRecordsSnapshot(BaseModel):
    """请求缓冲区的列表快照，不包含请求或响应正文。

    Attributes:
        instance_id: 当前请求缓冲区的实例标识。
        revision: 缓冲区快照版本，用于识别更新和清空。
        capacity: 缓冲区最多保留的记录数量。
        records: 当前保留的请求记录摘要。
        stats: 仅针对当前缓冲区保留记录的统计信息。
    """

    instance_id: str
    revision: int
    capacity: int
    records: list[InspectorRecordSummary]
    stats: InspectorBufferStats


class InspectorClearResult(BaseModel):
    """清空请求快照后的结果，不影响正在执行的模型调用。

    Attributes:
        instance_id: 清理后的请求缓冲区实例标识。
        revision: 清理后的缓冲区版本。
        cleared_count: 本次清理移除的记录数量。
    """

    instance_id: str
    revision: int
    cleared_count: int
