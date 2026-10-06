"""聊天消息文本解析。

核心把 @、引用预览和媒体占位符直接拼进消息纯文本，例如
``[回复<昵称(QQ号)>：内容]，说：@<昵称:QQ号> 你好[图片(hash):描述]``。
本模块把这类文本解析为结构化片段，供聊天监视器按昵称、引用卡片和图片渲染。

只依赖标准库。
"""

from __future__ import annotations

import ast
import json
import re
from typing import Any

# 适配器引用预览：[回复<昵称(QQ号)>：被引用内容]，说：
_REPLY_PREVIEW_RE = re.compile(r"^\s*\[回复<(?P<who>[^>]*)>：(?P<body>.*?)\]，说：", re.DOTALL)
# converter 旧格式：「回复：内容」/ [回复:消息ID] / [回复]
_LEGACY_REPLY_RE = re.compile(r"^\s*(?:「回复：(?P<body>[^」]*)」|\[回复(?::(?P<msg_id>[^\]]*))?\])")
_REPLY_WHO_RE = re.compile(r"^(?P<name>.*)\((?P<id>[^()]*)\)$", re.DOTALL)

# 正文中的 @、媒体与文件占位符
_TOKEN_RE = re.compile(
    r"@<(?P<at_name>[^:<>]*):(?P<at_id>[^<>]*)>\s?"
    r"|(?P<at_all>@全体成员)\s?"
    r"|\[(?P<media_label>图片|表情包|语音|视频)"
    r"(?:\((?P<media_id>[0-9a-fA-F]{64})\))?(?::(?P<media_desc>[^\]]*))?\]"
    r"|\[文件(?::(?P<file_desc>[^\]]*))?\]"
)

MEDIA_LABEL_TYPES: dict[str, str] = {"图片": "image", "表情包": "emoji", "语音": "voice", "视频": "video"}
MEDIA_TYPE_LABELS: dict[str, str] = {
    "image": "图片",
    "emoji": "表情包",
    "voice": "语音",
    "video": "视频",
    "file": "文件",
}
# 同一队列内的媒体项按出现顺序与占位符对应
_MEDIA_QUEUE_KEYS: dict[str, str] = {"image": "visual", "emoji": "visual", "voice": "voice", "video": "video"}
_MEDIA_ID_KEYS: tuple[str, ...] = ("image_id", "voice_id", "video_id")

# 片段内部字段：媒体原始数据，由调用方转换为 data URL 后移除
SEGMENT_DATA_KEY = "_data"


def parse_message_content(content: Any) -> tuple[str, list[dict[str, Any]]]:
    """拆出消息 content 中的文本与媒体项。

    运行时 content 是 ``{"text": ..., "media": [...]}`` 字典或纯文本；
    数据库中的含媒体消息以 ``str(dict)``（Python 字面量）保存。

    Args:
        content: 运行时或数据库中的消息 content。

    Returns:
        (文本, 媒体项列表)。
    """
    parsed = content
    if isinstance(content, str):
        stripped = content.strip()
        if not stripped.startswith("{"):
            return content, []
        parsed = _literal_dict(stripped)
        if parsed is None:
            return content, []

    if not isinstance(parsed, dict):
        return str(content or ""), []

    text = parsed.get("text")
    media = parsed.get("media")
    items = [item for item in media if isinstance(item, dict)] if isinstance(media, list) else []
    return (text if isinstance(text, str) else ""), items


def split_reply_preview(text: str) -> tuple[dict[str, str] | None, str]:
    """拆出文本开头的引用预览。

    Args:
        text: 消息纯文本。

    Returns:
        (引用预览, 剩余正文)。引用预览包含 ``sender_name``、``sender_id``、``text``，
        没有引用预览时为 None。
    """
    match = _REPLY_PREVIEW_RE.match(text)
    if match:
        who = match.group("who").strip()
        sender_name, sender_id = who, ""
        who_match = _REPLY_WHO_RE.match(who)
        if who_match:
            sender_name = who_match.group("name").strip()
            sender_id = who_match.group("id").strip()
        preview = {"sender_name": sender_name, "sender_id": sender_id, "text": match.group("body").strip()}
        return preview, text[match.end():].lstrip()

    legacy = _LEGACY_REPLY_RE.match(text)
    if legacy:
        preview = {"sender_name": "", "sender_id": "", "text": (legacy.group("body") or "").strip()}
        return preview, text[legacy.end():].lstrip()

    return None, text


def parse_segments(text: str, media_items: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """把消息正文解析为片段列表。

    片段类型为 text / at / image / emoji / voice / video / file。
    不带媒体 ID 的占位符按出现顺序认领 ``media_items`` 中同类媒体项；
    文本中没有占位符的剩余媒体项追加到末尾。

    Args:
        text: 已去掉引用预览的正文。
        media_items: content 中的媒体项。

    Returns:
        片段字典列表。媒体片段可能带内部字段 ``SEGMENT_DATA_KEY``。
    """
    queues: dict[str, list[dict[str, Any]]] = {"visual": [], "voice": [], "video": []}
    for item in media_items or []:
        queue_key = _MEDIA_QUEUE_KEYS.get(str(item.get("type") or ""))
        if queue_key:
            queues[queue_key].append(item)

    segments: list[dict[str, Any]] = []
    cursor = 0
    for match in _TOKEN_RE.finditer(text):
        _append_text(segments, text[cursor:match.start()])
        cursor = match.end()

        if match.group("at_name") is not None:
            user_id = match.group("at_id").strip()
            name = match.group("at_name").strip() or user_id
            segments.append({"type": "at", "text": name, "user_id": user_id or None})
        elif match.group("at_all"):
            segments.append({"type": "at", "text": "全体成员", "user_id": "all"})
        elif match.group("media_label"):
            segment_type = MEDIA_LABEL_TYPES[match.group("media_label")]
            item = _claim_media(queues[_MEDIA_QUEUE_KEYS[segment_type]], match.group("media_id"))
            segments.append(_media_segment(segment_type, match.group("media_desc"), match.group("media_id"), item))
        else:
            segments.append({"type": "file", "text": (match.group("file_desc") or "").strip()})

    _append_text(segments, text[cursor:])

    for queue in queues.values():
        for item in queue:
            segment_type = str(item.get("type") or "image")
            segments.append(_media_segment(segment_type, None, None, item))
    return segments


def segments_to_plain_text(segments: list[dict[str, Any]], limit: int = 80) -> str:
    """把片段转换为单行可读预览，如 ``@小明 你好[图片]``。"""
    parts: list[str] = []
    for segment in segments:
        segment_type = segment.get("type")
        if segment_type == "text":
            parts.append(str(segment.get("text") or ""))
        elif segment_type == "at":
            parts.append(f"@{segment.get('text') or ''} ")
        else:
            parts.append(f"[{MEDIA_TYPE_LABELS.get(str(segment_type), '消息')}]")
    preview = " ".join("".join(parts).split())
    return preview[:limit]


def _literal_dict(value: str) -> dict[str, Any] | None:
    """解析 ``str(dict)`` 或 JSON 形式的字典字符串。"""
    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _append_text(segments: list[dict[str, Any]], value: str) -> None:
    """追加文本片段，与前一个文本片段合并。"""
    if not value:
        return
    if segments and segments[-1]["type"] == "text":
        segments[-1]["text"] += value
        return
    segments.append({"type": "text", "text": value})


def _claim_media(queue: list[dict[str, Any]], media_id: str | None) -> dict[str, Any] | None:
    """为占位符认领媒体项：带 ID 时按 ID 匹配，否则取队首。"""
    if media_id:
        for index, item in enumerate(queue):
            if _media_item_id(item) == media_id:
                return queue.pop(index)
        return None
    return queue.pop(0) if queue else None


def _media_item_id(item: dict[str, Any]) -> str | None:
    """读取媒体项的哈希 ID。"""
    for key in _MEDIA_ID_KEYS:
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _media_segment(
    segment_type: str,
    description: str | None,
    media_id: str | None,
    item: dict[str, Any] | None,
) -> dict[str, Any]:
    """构建媒体片段。"""
    segment: dict[str, Any] = {
        "type": segment_type if segment_type in MEDIA_TYPE_LABELS else "image",
        "text": (description or "").strip(),
        "media_id": media_id or (_media_item_id(item) if item else None),
    }
    if item is not None and isinstance(item.get("data"), str):
        segment[SEGMENT_DATA_KEY] = item["data"]
    return segment
