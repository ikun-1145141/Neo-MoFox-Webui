"""模型测试实际执行函数。

将各类模型连通性测试（chat / stream / tool_call / vlm / embedding / rerank）
从 ModelConfigManager 中拆出，统一放在本文件内，便于复用与维护。
"""

from __future__ import annotations

import base64
import struct
import time
import zlib

import aiohttp
import openai

from src.app.plugin_system.api.log_api import get_logger

from .config_types import (
    ModelTestProvider, ModelTestModel, ModelTestRequest, ModelTestResult, RerankResultItem,
)

logger = get_logger("model_test")


# ===== VLM 测试图片 =====

def _png_chunk(tag: bytes, data: bytes) -> bytes:
    """构造一个 PNG chunk（长度 / 类型 / 数据 / CRC）。"""
    body = struct.pack(">I", len(data)) + tag + data
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return body + struct.pack(">I", crc)


def make_red_square_png(size: int = 64) -> bytes:
    """生成一张纯红色正方形 PNG 图片（RGB，8-bit，无透明通道）。

    Args:
        size: 图片边长（像素）

    Returns:
        PNG 文件字节
    """
    # 每一行先写入滤波器字节 0，再写 size 个红色（255, 0, 0）像素
    scanline = b"\x00" + bytes((255, 0, 0)) * size
    raw = scanline * size

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)  # 8-bit RGB
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", ihdr)
    png += _png_chunk(b"IDAT", zlib.compress(raw, 9))
    png += _png_chunk(b"IEND", b"")
    return png


def red_square_data_url(size: int = 64) -> str:
    """返回红色正方形图片的 Data URL，用于 VLM 测试的 image_url。"""
    return "data:image/png;base64," + base64.b64encode(make_red_square_png(size)).decode()


# ===== 基础工具 =====

def _new_client(base_url: str, api_key: str, timeout: int) -> openai.AsyncOpenAI:
    """构造临时 openai 客户端；调用方负责关闭。

    Args:
        base_url: 供应商 API 地址
        api_key: API 密钥
        timeout: 请求超时（秒）

    Returns:
        已配置好的 AsyncOpenAI 客户端
    """
    return openai.AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
        max_retries=0,
    )


def _latency(start: float) -> float:
    """计算自 start 起经过的毫秒数。

    Args:
        start: time.perf_counter() 记录的起始时刻

    Returns:
        经过的毫秒数
    """
    return (time.perf_counter() - start) * 1000


def _contains_red_square_keyword(text: str) -> bool:
    """判断 VLM 返回文本是否提及红色/方形等关键特征。

    用于检验模型是否真正“看到”了测试图片，而不仅仅是返回了任意文本。

    Args:
        text: 模型返回的文本

    Returns:
        是否命中任一关键词（英文大小写不敏感）
    """
    lowered = text.lower()
    return any(k in lowered for k in VLM_RED_SQUARE_KEYWORDS)


# ===== 测试项实现 =====

# VLM 测试图片的关键特征关键词，用于校验模型是否真正识别出红色正方形
VLM_RED_SQUARE_KEYWORDS = ("红", "red", "方形", "正方形", "square")

async def test_chat(
    request: ModelTestRequest,
    provider: ModelTestProvider,
    model: ModelTestModel,
    api_key: str,
) -> ModelTestResult:
    """标准 chat 连通性测试。

    发送一条普通文本消息，验证模型能否正常返回对话内容。

    Args:
        request: 模型测试请求（含测试提示词与超时等）
        provider: 供应商快照（含 base_url）
        model: 模型快照（含 model_identifier）
        api_key: 实际使用的 API 密钥

    Returns:
        测试结果：响应文本 + 单次耗时
    """
    start = time.perf_counter()
    async with _new_client(provider.base_url, api_key, request.timeout) as client:
        response = await client.chat.completions.create(
            model=model.model_identifier,
            messages=[{"role": "user", "content": request.test_prompt}],
            max_tokens=50,
        )
    response_text = response.choices[0].message.content or ""
    latency_ms = _latency(start)
    logger.info(f"模型测试成功: {model.name} ({latency_ms:.2f}ms) [chat]")
    return ModelTestResult(
        success=True,
        response_text=response_text,
        latency_ms=latency_ms,
        error_message=None,
        model_identifier=model.model_identifier,
        provider_base_url=provider.base_url,
        test_type="chat",
    )


async def test_stream(
    request: ModelTestRequest,
    provider: ModelTestProvider,
    model: ModelTestModel,
    api_key: str,
) -> ModelTestResult:
    """流式输出测试。

    以 stream 模式请求对话，逐块累积内容，验证流式输出链路是否正常。

    Args:
        request: 模型测试请求（含测试提示词与超时等）
        provider: 供应商快照（含 base_url）
        model: 模型快照（含 model_identifier）
        api_key: 实际使用的 API 密钥

    Returns:
        测试结果：累积的流式响应文本 + 耗时；空流视为失败
    """
    start = time.perf_counter()
    collected: list[str] = []
    async with _new_client(provider.base_url, api_key, request.timeout) as client:
        stream = await client.chat.completions.create(
            model=model.model_identifier,
            messages=[{"role": "user", "content": request.test_prompt}],
            max_tokens=50,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                collected.append(chunk.choices[0].delta.content)
    response_text = "".join(collected)
    latency_ms = _latency(start)
    success = bool(response_text.strip())
    logger.info(f"模型测试{'成功' if success else '失败'}: {model.name} ({latency_ms:.2f}ms) [stream]")
    return ModelTestResult(
        success=success,
        response_text=response_text or None,
        latency_ms=latency_ms,
        error_message=None if success else "流式响应为空（可能是模型不支持流式）",
        model_identifier=model.model_identifier,
        provider_base_url=provider.base_url,
        test_type="stream",
    )


async def test_tool_call(
    request: ModelTestRequest,
    provider: ModelTestProvider,
    model: ModelTestModel,
    api_key: str,
) -> ModelTestResult:
    """工具调用测试。

    提供 `get_current_time` 工具并让模型返回工具调用，验证函数调用能力。

    Args:
        request: 模型测试请求（含超时等）
        provider: 供应商快照（含 base_url）
        model: 模型快照（含 model_identifier）
        api_key: 实际使用的 API 密钥

    Returns:
        测试结果：调用的工具名列表 + 响应文本；未返回工具调用视为失败
    """
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_time",
                "description": "获取指定城市的当前时间",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "城市名称，例如：北京/上海"}
                    },
                    "required": ["city"],
                },
            },
        }
    ]
    start = time.perf_counter()
    async with _new_client(provider.base_url, api_key, request.timeout) as client:
        response = await client.chat.completions.create(
            model=model.model_identifier,
            messages=[
                {"role": "user", "content": "请查询北京市的当前时间"},
            ],
            tools=tools,
            tool_choice="auto",
            max_tokens=100,
        )
    tool_message = response.choices[0].message
    tool_calls = [tc.function.name for tc in (tool_message.tool_calls or [])]
    latency_ms = _latency(start)
    success = bool(tool_calls)
    logger.info(
        f"模型测试{'成功' if success else '失败'}: {model.name} ({latency_ms:.2f}ms) "
        f"[tool_call: {tool_calls or 'none'}]"
    )
    return ModelTestResult(
        success=success,
        response_text=tool_message.content or None,
        latency_ms=latency_ms,
        error_message=None if success else "模型未返回工具调用（可能不支持函数调用）",
        model_identifier=model.model_identifier,
        provider_base_url=provider.base_url,
        test_type="tool_call",
        tool_calls=tool_calls or None,
    )


async def test_vlm(
    request: ModelTestRequest,
    provider: ModelTestProvider,
    model: ModelTestModel,
    api_key: str,
) -> ModelTestResult:
    """视觉（多模态）测试，附带一张红色正方形测试图片，并校验关键描述词。

    该测试会生成一张纯红色（RGB 255,0,0）正方形图片并通过 data URL 发送给模型，
    要求模型描述图片的颜色与形状；后端检查返回文本是否命中
    :data:`VLM_RED_SQUARE_KEYWORDS` 中的关键词，以判断模型是否具备图像识别能力。

    Args:
        request: 模型测试请求（含超时、模型标识等）
        provider: 供应商快照（含 base_url）
        model: 模型快照（含 model_identifier）
        api_key: 实际使用的 API 密钥

    Returns:
        测试结果：响应文本 + 是否识别出红色正方形
    """
    image_url = red_square_data_url()
    start = time.perf_counter()
    async with _new_client(provider.base_url, api_key, request.timeout) as client:
        response = await client.chat.completions.create(
            model=model.model_identifier,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "这有一张图片，请用一句话回答：图片的颜色和形状分别是什么？"},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            max_tokens=80,
        )
    response_text = response.choices[0].message.content or ""
    latency_ms = _latency(start)
    has_keyword = _contains_red_square_keyword(response_text)
    success = bool(response_text.strip()) and has_keyword
    logger.info(f"模型测试{'成功' if success else '失败'}: {model.name} ({latency_ms:.2f}ms) [vlm]")
    return ModelTestResult(
        success=success,
        response_text=response_text or None,
        latency_ms=latency_ms,
        error_message=(
            None if success
            else ("视觉模型未返回响应（可能不支持图像输入）" if not response_text.strip()
                  else f"模型未能识别红色正方形（未命中关键词: {response_text[:60]}…）")
        ),
        model_identifier=model.model_identifier,
        provider_base_url=provider.base_url,
        test_type="vlm",
    )


async def test_embedding(
    request: ModelTestRequest,
    provider: ModelTestProvider,
    model: ModelTestModel,
    api_key: str,
) -> ModelTestResult:
    """嵌入向量测试，可指定输出维度。

    对测试提示词做嵌入，返回实际输出的向量维度与前 8 个分量预览。
    指定 dimensions 时会在请求中携带该参数（部分供应商不支持）。

    Args:
        request: 模型测试请求（含测试提示词、可选 dimensions）
        provider: 供应商快照（含 base_url）
        model: 模型快照（含 model_identifier）
        api_key: 实际使用的 API 密钥

    Returns:
        测试结果：实际输出维度 + 向量前 8 个分量预览
    """
    start = time.perf_counter()
    async with _new_client(provider.base_url, api_key, request.timeout) as client:
        if request.dimensions:
            response = await client.embeddings.create(
                model=model.model_identifier,
                input=request.test_prompt,
                dimensions=request.dimensions,
            )
        else:
            response = await client.embeddings.create(
                model=model.model_identifier,
                input=request.test_prompt,
            )
    vector = response.data[0].embedding
    latency_ms = _latency(start)
    logger.info(f"嵌入测试成功: {model.name} ({latency_ms:.2f}ms) 维度={len(vector)}")
    return ModelTestResult(
        success=True,
        response_text=None,
        latency_ms=latency_ms,
        error_message=None,
        model_identifier=model.model_identifier,
        provider_base_url=provider.base_url,
        test_type="embedding",
        dimensions=len(vector),
        embedding_preview=vector[:8],
    )


# 重排序内置文档（固定使用，不接收用户自定义文档）
RERANK_BUILTIN_DOCUMENTS = [
    "北京是中国的首都，拥有故宫和长城等著名景点。",
    "Python 是一种广泛使用的高级编程语言。",
    "深度神经网络是机器学习的重要分支。",
    "杭州以西湖和龙井茶闻名于世。",
]


async def test_rerank(
    request: ModelTestRequest,
    provider: ModelTestProvider,
    model: ModelTestModel,
    api_key: str,
) -> ModelTestResult:
    """重排序测试，使用内置文档调用 /rerank 端点。

    使用固定的 :data:`RERANK_BUILTIN_DOCUMENTS` 作为待排序文档集，
    以请求中的查询文本调用供应商的 /rerank 接口，验证重排序能力。

    Args:
        request: 模型测试请求（查询文本取自 test_prompt，返回条数取自 top_n）
        provider: 供应商快照（含 base_url）
        model: 模型快照（含 model_identifier）
        api_key: 实际使用的 API 密钥

    Returns:
        测试结果：重排序条目列表（索引/文档/得分）+ 最相关文档文本
    """
    url = provider.base_url.rstrip("/") + "/rerank"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model.model_identifier,
        "query": request.test_prompt or "中国最好的城市",
        "input": RERANK_BUILTIN_DOCUMENTS,
        "top_n": request.top_n or 2,
    }
    start = time.perf_counter()
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                url, headers=headers, json=payload,
                timeout=aiohttp.ClientTimeout(total=request.timeout),
            ) as response:
                if response.status >= 400:
                    body = (await response.text())[:500]
                    raise ValueError(f"重排序接口返回 {response.status}: {body}")
                data = await response.json(content_type=None)
        except aiohttp.ClientError as e:
            error_message = f"重排序接口请求失败: {e}"
            logger.error(f"模型测试失败: {error_message}")
            return ModelTestResult(
                success=False,
                response_text=None,
                latency_ms=None,
                error_message=error_message,
                model_identifier=model.model_identifier,
                provider_base_url=provider.base_url,
                test_type="rerank",
            )

    results_raw = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results_raw, list):
        error_message = "重排序接口响应缺少 results 字段"
        logger.error(f"模型测试失败: {error_message}")
        return ModelTestResult(
            success=False,
            response_text=None,
            latency_ms=None,
            error_message=error_message,
            model_identifier=model.model_identifier,
            provider_base_url=provider.base_url,
            test_type="rerank",
        )

    rerank_results = [
        RerankResultItem(
            index=int(item.get("index", 0)),
            document=str(item.get("document", "")),
            score=float(item.get("relevance_score", item.get("score", 0.0))),
        )
        for item in results_raw
    ]
    latency_ms = _latency(start)
    logger.info(f"重排序测试成功: {model.name} ({latency_ms:.2f}ms) 结果数={len(rerank_results)}")
    top_doc = rerank_results[0].document if rerank_results else ""
    return ModelTestResult(
        success=True,
        response_text=f"最相关文档: {top_doc}",
        latency_ms=latency_ms,
        error_message=None,
        model_identifier=model.model_identifier,
        provider_base_url=provider.base_url,
        test_type="rerank",
        rerank_results=rerank_results,
    )


# ===== 分发入口 =====

async def run_model_test(
    request: ModelTestRequest,
    provider: ModelTestProvider,
    model: ModelTestModel,
    api_key: str,
) -> ModelTestResult:
    """按 test_type 分发到对应的测试实现。

    Args:
        request: 测试请求
        provider: 供应商快照
        model: 模型快照
        api_key: 实际使用的 API 密钥

    Returns:
        对应类型的测试结果

    Raises:
        ValueError: 未识别的 test_type
    """
    if request.test_type == "rerank":
        return await test_rerank(request, provider, model, api_key)
    if request.test_type == "embedding":
        return await test_embedding(request, provider, model, api_key)
    if request.test_type == "vlm":
        return await test_vlm(request, provider, model, api_key)
    if request.test_type == "tool_call":
        return await test_tool_call(request, provider, model, api_key)
    if request.test_type == "stream":
        return await test_stream(request, provider, model, api_key)
    if request.test_type == "chat":
        return await test_chat(request, provider, model, api_key)
    raise ValueError(f"不支持的测试类型: {request.test_type}")