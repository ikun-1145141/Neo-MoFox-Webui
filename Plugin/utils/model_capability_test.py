"""模型能力探测；只使用本次配置快照，不保存配置或执行真实工具。"""
from __future__ import annotations

import asyncio
import base64
from copy import deepcopy
from dataclasses import dataclass, field
import json
import math
import re
import struct
import time
from typing import Any, AsyncIterator
from urllib.parse import quote
import zlib

import aiohttp
from yarl import URL

from .config_types import ModelTestRequest, ModelTestResult

_MAX_BYTES = 2 * 1024 * 1024
_MAX_TEXT = 16384
_TOOL_NAME = "webui_capability_probe"
_TOOL_VALUE = "webui-test"
_SCHEMA = {"type": "object", "properties": {"value": {"type": "string", "enum": [_TOOL_VALUE]}}, "required": ["value"], "additionalProperties": False}
_PROTECTED = {
    "model", "messages", "input", "contents", "tools", "tool_choice", "toolConfig", "tool_config",
    "stream", "stream_options", "n", "candidateCount", "max_tokens", "max_completion_tokens",
    "max_output_tokens", "maxOutputTokens", "system", "instructions", "input_image", "input_text",
}


class _ProbeError(Exception):
    pass


@dataclass
class _Output:
    text: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    embeddings: list[Any] = field(default_factory=list)
    first_token_ms: float | None = None
    chunks: int = 0
    complete: bool = False
    truncated: bool = False

    def append(self, value: Any, start: float) -> None:
        if not isinstance(value, str) or not value:
            return
        if self.first_token_ms is None:
            self.first_token_ms = (time.perf_counter() - start) * 1000
        self.chunks += 1
        self.truncated |= len(self.text) + len(value) > _MAX_TEXT
        self.text = (self.text + value)[:_MAX_TEXT]


def _image() -> str:
    # 用标准库生成白底红色方块，不读取用户文件或请求外部图片。
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    size = 96
    rows = b"".join(b"\x00" + b"".join(b"\xef\x22\x22" if 16 <= x < 80 and 16 <= y < 80 else b"\xff\xff\xff" for x in range(size)) for y in range(size))
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")
    return base64.b64encode(png).decode("ascii")


def _prompt(request: ModelTestRequest) -> str:
    if request.test_type == "vlm":
        return "图片中心的方块是什么颜色？请只回答颜色名称。"
    if request.test_type == "tools":
        return f"请调用 {_TOOL_NAME} 工具，参数 value 必须为 {_TOOL_VALUE}。不要执行其他任务。"
    return request.test_prompt.strip() or "请简短回复：连接成功。"


def _url(base: str, protocol: str, endpoint: str, model: str) -> URL:
    try:
        url = URL(base.strip())
        if url.scheme not in {"http", "https"} or not url.host or url.user or url.password:
            raise ValueError
        path = url.path.rstrip("/")
        for suffix in ("/chat/completions", "/responses", "/embeddings", "/messages"):
            if path.endswith(suffix):
                path = path[:-len(suffix)]
                break
        if protocol in {"gemini", "aiohttp_gemini"}:
            if path.endswith("/models"):
                path = path[:-7]
            if not re.search(r"/v1(?:beta|alpha)?$", path):
                path += "/v1beta"
            model = model.removeprefix("models/")
            path += "/models/" + quote(model, safe="") + ":" + endpoint
            return url.with_path(path, encoded=True).with_fragment(None)
        if protocol == "anthropic" and not path.endswith("/v1"):
            path += "/v1"
        return url.with_path(path + "/" + endpoint).with_fragment(None)
    except (ValueError, TypeError):
        raise ValueError("供应商 API 地址无效，请使用不含用户名和密码的 HTTP 地址") from None


def _split_params(model: Any) -> tuple[dict[str, Any], dict[str, str], dict[str, Any]]:
    extra = deepcopy(getattr(model, "extra_params", {}) or {})
    if not isinstance(extra, dict):
        raise ValueError("模型额外参数必须为对象")
    headers: dict[str, str] = {}
    query: dict[str, Any] = {}
    body: dict[str, Any] = {}
    for name, target in (("headers", headers), ("extra_headers", headers), ("query", query), ("extra_query", query), ("body", body), ("extra_body", body)):
        value = extra.pop(name, {})
        if value is not None and not isinstance(value, dict):
            raise ValueError("模型的请求头、查询参数和额外请求体必须为对象")
        target.update(value or {})
    body = {**extra, **body}
    for name in _PROTECTED:
        body.pop(name, None)
    # 测试的输入、工具和流式开关不能被额外参数覆盖。
    clean_headers = {key: value for key, value in headers.items() if key.lower() not in {"authorization", "x-api-key", "x-goog-api-key", "content-type", "accept"}}
    if any(not isinstance(value, str) for value in clean_headers.values()):
        raise ValueError("额外请求头的值必须为字符串")
    for key, value in list(query.items()):
        if isinstance(value, bool):
            query[key] = str(value).lower()
        elif value is None:
            del query[key]
        elif not isinstance(value, (str, int, float, list, tuple)):
            raise ValueError("额外查询参数包含不支持的值")
    return body, clean_headers, query


def _payload(request: ModelTestRequest, protocol: str, model: str, extra: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    kind = request.test_type
    text = _prompt(request)
    tools = kind == "tools"
    image = _image() if kind == "vlm" else ""
    if kind == "embedding":
        if protocol in {"gemini", "aiohttp_gemini"}:
            body = {**extra, "model": "models/" + model.removeprefix("models/"), "content": {"parts": [{"text": "用于验证嵌入能力的固定短文本。"}]}}
            return "embedContent", body
        return "embeddings", {**extra, "model": model, "input": ["用于验证嵌入能力的固定短文本。"], "encoding_format": "float"}
    if protocol in {"gemini", "aiohttp_gemini"}:
        params = dict(extra)
        generation = params.pop("generationConfig", params.pop("generation_config", {}))
        if not isinstance(generation, dict):
            raise ValueError("Gemini 的生成配置必须为对象")
        generation = dict(generation)
        for original, native in (("temperature", "temperature"), ("top_p", "topP"), ("top_k", "topK"), ("stop", "stopSequences")):
            if original in params:
                generation[native] = params.pop(original)
        generation.update(maxOutputTokens=1024, candidateCount=1)
        parts: list[dict[str, Any]] = [{"text": text}]
        if image:
            parts.append({"inlineData": {"mimeType": "image/png", "data": image}})
        body = {**params, "contents": [{"role": "user", "parts": parts}], "generationConfig": generation}
        if tools:
            schema = {key: value for key, value in _SCHEMA.items() if key != "additionalProperties"}
            body["tools"] = [{"functionDeclarations": [{"name": _TOOL_NAME, "description": "验证工具调用格式，不执行任何操作。", "parameters": schema}]}]
            body["toolConfig"] = {"functionCallingConfig": {"mode": "ANY", "allowedFunctionNames": [_TOOL_NAME]}}
        return "streamGenerateContent" if kind == "stream" else "generateContent", body
    if protocol == "anthropic":
        content: list[dict[str, Any]] = [{"type": "text", "text": text}]
        if image:
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image}})
        body = {**extra, "model": model, "messages": [{"role": "user", "content": content}], "max_tokens": 1024, "stream": kind == "stream"}
        if tools:
            body["tools"] = [{"name": _TOOL_NAME, "description": "验证工具调用格式，不执行任何操作。", "input_schema": _SCHEMA}]
            body["tool_choice"] = {"type": "tool", "name": _TOOL_NAME}
        return "messages", body
    if protocol == "openai_response":
        content = [{"type": "input_text", "text": text}]
        if image:
            content.append({"type": "input_image", "image_url": "data:image/png;base64," + image})
        body = {**extra, "model": model, "input": [{"role": "user", "content": content}], "max_output_tokens": 1024, "stream": kind == "stream"}
        if tools:
            body["tools"] = [{"type": "function", "name": _TOOL_NAME, "description": "验证工具调用格式，不执行任何操作。", "parameters": _SCHEMA}]
            body["tool_choice"] = {"type": "function", "name": _TOOL_NAME}
        return "responses", body
    content = [{"type": "text", "text": text}]
    if image:
        content.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + image}})
    body = {**extra, "model": model, "messages": [{"role": "user", "content": content}], "max_tokens": 1024, "stream": kind == "stream"}
    if tools:
        body["tools"] = [{"type": "function", "function": {"name": _TOOL_NAME, "description": "验证工具调用格式，不执行任何操作。", "parameters": _SCHEMA}}]
        body["tool_choice"] = {"type": "function", "function": {"name": _TOOL_NAME}}
    return "chat/completions", body


async def _read_json(response: aiohttp.ClientResponse) -> dict[str, Any]:
    raw = bytearray()
    async for chunk in response.content.iter_chunked(32768):
        raw.extend(chunk)
        if len(raw) > _MAX_BYTES:
            raise _ProbeError("供应商响应超过测试允许的大小")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError):
        raise _ProbeError("供应商没有返回有效的 JSON 响应") from None
    if not isinstance(data, dict):
        raise _ProbeError("供应商响应结构无效")
    return data


def _decode_event(lines: list[bytes]) -> dict[str, Any]:
    payload = b"\n".join(lines).strip()
    if payload == b"[DONE]":
        return {"_done": True}
    try:
        event = json.loads(payload)
    except (ValueError, UnicodeError):
        raise _ProbeError("供应商返回了无效的流事件") from None
    if not isinstance(event, dict):
        raise _ProbeError("供应商流事件结构无效")
    return event


async def _events(response: aiohttp.ClientResponse) -> AsyncIterator[dict[str, Any]]:
    if "text/event-stream" not in response.headers.get("Content-Type", "").lower():
        raise _ProbeError("供应商未返回事件流，不能判定流式输出成功")
    buffer = b""
    lines: list[bytes] = []
    total = 0
    async for chunk in response.content.iter_any():
        total += len(chunk)
        if total > _MAX_BYTES:
            raise _ProbeError("供应商流响应超过测试允许的大小")
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            line = line.rstrip(b"\r")
            if not line and lines:
                event = _decode_event(lines)
                lines = []
                yield event
                if event.get("_done"):
                    return
            elif line.startswith(b"data:"):
                lines.append(line[5:].lstrip(b" "))
    if buffer.rstrip(b"\r").startswith(b"data:"):
        lines.append(buffer.rstrip(b"\r")[5:].lstrip(b" "))
    if lines:
        yield _decode_event(lines)


def _json_output(data: dict[str, Any], protocol: str, kind: str, output: _Output) -> None:
    if data.get("error"):
        raise _ProbeError("供应商返回了错误响应")
    if kind == "embedding":
        if protocol in {"gemini", "aiohttp_gemini"}:
            output.embeddings = [data.get("embedding", {}).get("values", [])]
        else:
            output.embeddings = [item.get("embedding", []) for item in data.get("data", [])]
        output.complete = True
        return
    texts: list[str] = []
    if protocol in {"gemini", "aiohttp_gemini"}:
        candidates = data.get("candidates", [])
        if not candidates:
            raise _ProbeError("供应商未返回候选内容，可能触发了内容限制")
        candidate = candidates[0]
        for part in candidate.get("content", {}).get("parts", []):
            if isinstance(part.get("text"), str) and not part.get("thought"):
                texts.append(part["text"])
            call = part.get("functionCall")
            if isinstance(call, dict):
                output.tool_calls.append({"name": call.get("name"), "arguments": call.get("args")})
        output.complete = candidate.get("finishReason") == "STOP"
    elif protocol == "anthropic":
        for part in data.get("content", []):
            if part.get("type") == "text" and isinstance(part.get("text"), str):
                texts.append(part["text"])
            elif part.get("type") == "tool_use":
                output.tool_calls.append({"name": part.get("name"), "arguments": part.get("input")})
        output.complete = data.get("stop_reason") in {"end_turn", "stop_sequence", "tool_use"}
    elif protocol == "openai_response":
        for item in data.get("output", []):
            if item.get("type") == "message":
                texts.extend(part["text"] for part in item.get("content", []) if part.get("type") == "output_text" and isinstance(part.get("text"), str))
            elif item.get("type") == "function_call":
                output.tool_calls.append({"name": item.get("name"), "arguments": item.get("arguments")})
        output.complete = data.get("status") == "completed"
    else:
        choices = data.get("choices", [])
        if not choices:
            raise _ProbeError("供应商没有返回模型输出")
        choice = choices[0]
        message = choice.get("message", {})
        if isinstance(message.get("content"), str):
            texts.append(message["content"])
        for call in message.get("tool_calls") or []:
            function = call.get("function", {})
            output.tool_calls.append({"name": function.get("name"), "arguments": function.get("arguments")})
        output.complete = choice.get("finish_reason") in {"stop", "tool_calls"}
    text = "".join(texts)
    output.truncated = len(text) > _MAX_TEXT
    output.text = text[:_MAX_TEXT]


def _stream_output(event: dict[str, Any], protocol: str, output: _Output, start: float) -> None:
    if event.get("error") or event.get("type") in {"error", "response.failed", "response.incomplete"}:
        raise _ProbeError("供应商在流式输出期间返回错误或未完成响应")
    if protocol in {"gemini", "aiohttp_gemini"}:
        for candidate in event.get("candidates", [])[:1]:
            for part in candidate.get("content", {}).get("parts", []):
                if not part.get("thought"):
                    output.append(part.get("text"), start)
            if candidate.get("finishReason"):
                if candidate["finishReason"] != "STOP":
                    raise _ProbeError("供应商未正常完成流式输出")
                output.complete = True
    elif protocol == "anthropic":
        if event.get("type") == "content_block_delta" and event.get("delta", {}).get("type") == "text_delta":
            output.append(event["delta"].get("text"), start)
        if event.get("type") == "message_delta" and event.get("delta", {}).get("stop_reason") not in (None, "end_turn", "stop_sequence"):
            raise _ProbeError("供应商未正常完成流式输出")
        if event.get("type") == "message_stop":
            output.complete = True
    elif protocol == "openai_response":
        if event.get("type") == "response.output_text.delta":
            output.append(event.get("delta"), start)
        if event.get("type") == "response.completed":
            output.complete = event.get("response", {}).get("status") == "completed"
    else:
        for choice in event.get("choices", [])[:1]:
            output.append(choice.get("delta", {}).get("content"), start)
            if choice.get("finish_reason"):
                if choice["finish_reason"] != "stop":
                    raise _ProbeError("供应商未正常完成流式输出")
                output.complete = True


def _validate(kind: str, output: _Output) -> tuple[str, dict[str, Any]]:
    if not output.complete:
        raise _ProbeError("供应商响应未正常结束，不能判定测试成功")
    if kind == "embedding":
        vectors = output.embeddings
        if not vectors or any(not isinstance(vector, list) or not vector for vector in vectors):
            raise _ProbeError("供应商没有返回有效的嵌入向量")
        size = len(vectors[0])
        if any(len(vector) != size or any(type(value) not in (float, int) or not math.isfinite(value) for value in vector) for vector in vectors):
            raise _ProbeError("嵌入向量包含无效数值或不一致的维度")
        return f"返回 {len(vectors)} 个向量，维度为 {size}", {"count": len(vectors), "dimensions": size, "preview": vectors[0][:8]}
    if kind == "tools":
        for call in output.tool_calls:
            args = call.get("arguments")
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    continue
            if call.get("name") == _TOOL_NAME and isinstance(args, dict) and args == {"value": _TOOL_VALUE}:
                return "已返回正确的工具名称和参数，未执行工具", {"tool_calls": output.tool_calls, "executed": False}
        raise _ProbeError("模型未返回符合要求的工具调用名称和参数")
    if not output.text.strip():
        raise _ProbeError("模型没有返回非空文本，不能判定测试成功")
    if kind == "vlm" and not re.search(r"红|\bred\b", output.text, re.I):
        raise _ProbeError("模型返回了文本，但未识别出内置图片中的红色方块")
    summary = "已识别内置图片中的红色方块" if kind == "vlm" else "已正常接收流式文本并完成输出" if kind == "stream" else "已收到非空文本回复"
    return summary, {"text_chunks": output.chunks, "text_truncated": output.truncated} if kind == "stream" else {"text_truncated": output.truncated}


def _secrets(provider: Any, model: Any) -> set[str]:
    keys = provider.api_key if isinstance(provider.api_key, list) else [provider.api_key]
    found = {key.strip() for key in keys if isinstance(key, str) and key.strip()}
    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if re.search(r"key|token|secret|password|authorization|credential", str(key), re.I) and isinstance(item, str) and item:
                    found.add(item)
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    visit(getattr(model, "extra_params", {}))
    return found


def _safe(value: Any, secrets: set[str]) -> Any:
    if isinstance(value, str):
        for secret in sorted(secrets, key=len, reverse=True):
            value = value.replace(secret, "[已隐藏]")
        return value[:_MAX_TEXT]
    if isinstance(value, list):
        return [_safe(item, secrets) for item in value[:100]]
    if isinstance(value, dict):
        return {key: _safe(item, secrets) for key, item in value.items()}
    return value


async def run_model_capability_test(request: ModelTestRequest, provider: Any, model: Any) -> ModelTestResult:
    protocol = getattr(provider, "client_type", "openai")
    if protocol in {"responses", "openai.responses"}:
        protocol = "openai_response"
    output = _Output()
    start = time.perf_counter()
    secrets = _secrets(provider, model)
    try:
        safe_url = str(URL(provider.base_url).with_user(None).with_query(None).with_fragment(None))
    except (ValueError, TypeError):
        safe_url = ""
    def result(status: str, summary: str, details: dict[str, Any] | None = None) -> ModelTestResult:
        return ModelTestResult(
            success=status == "succeeded", status=status, test_type=request.test_type,
            response_text=_safe(output.text, secrets) or None,
            latency_ms=(time.perf_counter() - start) * 1000,
            first_token_ms=output.first_token_ms if request.test_type == "stream" else None,
            error_message=None if status == "succeeded" else summary,
            summary=summary, details=_safe(details or {}, secrets),
            model_identifier=_safe(model.model_identifier, secrets), provider_base_url=_safe(safe_url, secrets),
        )
    if protocol not in {"openai", "openai_response", "anthropic", "gemini", "aiohttp_gemini"}:
        return result("unsupported", "当前配置的供应商协议暂不支持能力测试，不会回退到其他协议")
    if protocol == "anthropic" and request.test_type == "embedding":
        return result("unsupported", "Anthropic Messages 协议不提供嵌入接口")
    if not provider.base_url.strip():
        raise ValueError("供应商 API 地址不能为空")
    if not model.model_identifier.strip():
        raise ValueError("模型标识符不能为空")
    keys = provider.api_key if isinstance(provider.api_key, list) else [provider.api_key]
    api_key = next((key.strip() for key in keys if isinstance(key, str) and key.strip()), "")
    if not api_key:
        raise ValueError("供应商 API 密钥不能为空")
    try:
        extra, headers, query = _split_params(model)
        endpoint, body = _payload(request, protocol, model.model_identifier, extra)
        url = _url(provider.base_url, protocol, endpoint, model.model_identifier)
        query = {**url.query, **query}
        if protocol in {"gemini", "aiohttp_gemini"}:
            headers["x-goog-api-key"] = api_key
            if request.test_type == "stream":
                query["alt"] = "sse"
        elif protocol == "anthropic":
            headers.update({"x-api-key": api_key, "anthropic-version": "2023-06-01"})
        else:
            headers["Authorization"] = "Bearer " + api_key
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "text/event-stream" if request.test_type == "stream" else "application/json"
        # 每个测试仅发起一次请求；超时、取消和结束都会释放连接与客户端。
        async with asyncio.timeout(request.timeout):
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=request.timeout)) as session:
                async with session.post(url.with_query(query), headers=headers, json=body, allow_redirects=False) as response:
                    if not 200 <= response.status < 300:
                        message = {400: "供应商拒绝了测试参数", 401: "供应商鉴权失败，请检查密钥", 403: "供应商拒绝访问，请检查权限", 404: "供应商接口或模型不存在", 429: "供应商请求受限，请稍后重试"}.get(response.status, "供应商请求失败")
                        raise _ProbeError(f"{message}（HTTP {response.status}）")
                    if request.test_type == "stream":
                        async for event in _events(response):
                            _stream_output(event, protocol, output, start)
                    else:
                        _json_output(await _read_json(response), protocol, request.test_type, output)
        summary, details = _validate(request.test_type, output)
        return result("succeeded", summary, details)
    except asyncio.CancelledError:
        raise
    except TimeoutError:
        return result("failed", f"模型测试超时（{request.timeout} 秒）")
    except _ProbeError as exc:
        return result("failed", str(exc), {"tool_calls": output.tool_calls} if output.tool_calls else {})
    except aiohttp.ClientError:
        return result("failed", "无法连接供应商，或连接在响应完成前中断")
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        return result("failed", "测试参数或供应商响应结构无效，请检查当前模型配置")
    except Exception:
        return result("failed", "模型能力测试失败，请检查当前模型配置后重试")
