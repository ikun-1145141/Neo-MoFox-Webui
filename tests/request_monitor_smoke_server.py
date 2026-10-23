"""Local-only smoke fixture: real native clients/collector and WebUI router, fake SDK endpoints.

Run with a development environment containing pytest, uvicorn and both projects' dependencies.
The fixture never reads real credentials or contacts an external model provider.
"""

from __future__ import annotations
import importlib.util
import os
from pathlib import Path
import sys
from contextlib import asynccontextmanager
import pytest
from fastapi import FastAPI
from pydantic import BaseModel, Field, JsonValue
from fastapi.responses import FileResponse
import uvicorn

ROOT = Path(__file__).resolve().parents[1]
HOST = Path(os.environ.get("NEO_MOFOX_ROOT", ROOT.parent / "Neo-MoFox")).expanduser().resolve()
sys.path.insert(0, str(HOST))


def load(name, path):
    """Load test fixtures without booting the application."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fakes = load(
    "_monitor_smoke_providers", HOST / "test/kernel/llm/test_request_monitor.py"
)
transport = load("_monitor_smoke_transport", ROOT / "tests/test_request_monitor.py")
from src.kernel.llm import get_inspector

inspector = get_inspector()
router, _, _ = transport.load_transport(inspector)


@asynccontextmanager
async def lifespan(app):
    """Seed all five APIs through the real native provider methods."""
    with pytest.MonkeyPatch.context() as patch:
        for protocol in ["openai", "anthropic", "responses"]:
            result = await fakes.invoke(
                patch,
                protocol,
                stream=True,
                sdk_stream=fakes.FakeStream(fakes.sdk_events(protocol)),
            )
            async for _ in result[2]:
                pass
        client = fakes.OpenAIChatClient()

        async def embedding(**kwargs):
            return fakes.JSON(
                data=[fakes.JSON(embedding=[i / 2048 for i in range(2048)]), fakes.JSON(embedding=[0.1, 0.2, 0.3])],
                usage=fakes.JSON(prompt_tokens=2, total_tokens=2),
            )

        async def rerank(**kwargs):
            return fakes.JSON(results=[fakes.JSON(index=0, relevance_score=0.98)])

        patch.setattr(
            client,
            "_get_client",
            lambda **_: fakes.JSON(
                embeddings=fakes.JSON(create=embedding),
                rerank=fakes.JSON(create=rerank),
            ),
        )
        model = {
            "api_key": "smoke-only",
            "api_provider": "local-demo",
            "extra_params": {},
        }
        await client.create_embedding(
            model_name="demo-embedding",
            inputs=["semantic query"],
            request_name="embedding",
            model_set=model,
        )
        await client.create_rerank(
            model_name="demo-rerank",
            query="query",
            documents=["document"],
            top_n=1,
            request_name="rerank",
            model_set=model,
        )
        try:
            await fakes.invoke(
                patch,
                "openai",
                error=RuntimeError(
                    "Controlled provider error: api_key=secret-is-redacted"
                ),
            )
        except RuntimeError:
            pass
        await fakes.invoke(patch, "openai")
    seed_display_samples()
    yield


def seed_display_samples():
    """Explicit UI fixtures via public collector APIs, not claimed as provider executions."""
    metadata = {"request_name": "UI fixture", "api_provider": "local-fixture"}
    for status in ("captured", "pending", "cancelled"):
        rid = inspector.capture("fixture.display", {"model": "ui-" + status},
                                {**metadata, "request_name": "UI fixture / " + status}, native=status != "captured")
        if status == "cancelled":
            inspector.start(rid)
            inspector.finish(rid, {"kind": "chat", "message": "Partial response retained on cancellation."}, cancelled=True)
    for attempt in (1, 2):
        rid = inspector.capture("fixture.display", {"model": "ui-retry-" + str(attempt)},
                                {**metadata, "request_name": "UI fixture / retry"}, native=True,
                                logical_request_id="fixture-retry", attempt=attempt)
        inspector.start(rid)
        inspector.finish(rid, {"kind": "chat", "message": "retry sample"},
                         error=RuntimeError("Controlled first-attempt failure") if attempt == 1 else None)
    rid = inspector.capture("fixture.display", {"model": "ui-truncated"},
                            {**metadata, "request_name": "UI fixture / truncated"}, native=True)
    inspector.start(rid)
    inspector.raw(rid, {"large_field": "x" * (2 * 1024 * 1024 + 100)})
    inspector.finish(rid, {"kind": "chat", "message": "Normalized response remains available after raw truncation."})
    rid = inspector.capture("fixture.display", {"model": "ui-unavailable", "unsupported": object()},
                            {**metadata, "request_name": "UI fixture / unavailable", "unsupported": object()}, native=True)
    inspector.start(rid)
    inspector.raw(rid, object())
    inspector.finish(rid)
    params = {
        "model": "ui-structured", "stream": True, "temperature": 0.4,
        "messages": [
            {"role": "system", "content": "Offline structure inspector fixture."},
            {"role": "user", "content": [{"type": "text", "text": "Show request structure; <img src=x onerror=alert(1)> must remain text."},
                                          {"type": "image_url", "image_url": {"url": "https://media.invalid/never-fetch.png"}}]},
            {"role": "assistant", "content": None, "tool_calls": [{"id": "call-1", "type": "function", "function": {"name": "lookup", "arguments": '{"query":"fixture"}'}}]},
            {"role": "tool", "tool_call_id": "call-1", "content": '{"ok":true,"items":[1,2]}'},
        ],
        "tools": [{"type": "function", "function": {"name": "lookup", "description": "Offline tool definition, no execution",
                  "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "options": {"type": "object", "properties": {"limit": {"type": "integer"}}}}, "required": ["query"]}}}],
        "extra_headers": {"Authorization": "Bearer fixture-redaction-value", "X-Debug": "offline"},
        "extra_query": {"vendor_mode": "fixture"},
        "extra_body": {"a/b~": {"": [None, False, 0, "", {}, []]}, "items": list(range(250)), "vendor_unknown": {"nested": {"enabled": True}}},
    }
    rid = inspector.capture("fixture.display", params, {**metadata, "request_name": "UI fixture / structured tools"}, native=True, stream=True)
    inspector.start(rid, params)
    inspector.raw(rid, {"type": "vendor.unknown", "payload": [1, None]}, event=True)
    inspector.finish(rid, {"kind": "chat", "message": "Offline LLM response.\n" * 400,
                          "reasoning_content": "Existing reasoning content only.",
                          "tool_calls": [{"id": "call-2", "name": "lookup", "args": {"query": "fixture"}},
                                         {"id": "call-3", "name": "lookup", "args": '{"query":', "vendor_extra": True}],
                          "stop_reason": "tool_calls"})


    # Deterministic mobile stress fixtures. No robot, real credentials or provider I/O.
    for index in range(30):
        params = {
            "model": "ui-mobile-model-" + "long-name-" * 8,
            "messages": [{"role": "user", "content": "离线手机适配测试。\n" * 1800}],
            "tools": [{"type": "function", "function": {
                "name": "offline_tool_" + str(i) + ("_long_name" * 8 if i % 2 else ""),
                "description": "仅用于离线布局测试，不执行工具。",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
            }} for i in range(29)],
            "extra_body": {"deep": {"nested": {"values": list(range(250))}}, "long_value": "offline-value" * 3000},
        }
        rid = inspector.capture("chat.completions.create", params,
                                {**metadata, "request_name": "UI fixture / mobile " + str(index) + "_long_request_name" * 5},
                                native=True, stream=True, logical_request_id="mobile-long-logical-id-" * 8)
        inspector.start(rid, params)
        inspector.raw(rid, {"type": "offline.unknown", "text": "离线原始事件" * 100}, event=True)
        inspector.finish(rid, {"kind": "chat", "message": "手机端长文本返回。\n" * 1600,
                              "reasoning_content": "仅展示已有推理。\n" * 100,
                              "tool_calls": [{"id": "offline-call", "name": "offline_tool_0", "args": '{"query":"offline"}'}]},
                         error=RuntimeError("离线错误详情。" * 300) if index == 28 else None)


app = FastAPI(lifespan=lifespan)
app.mount("/webui/api/request-inspector", router.app)


def ok(data):
    return {"code": 200, "data": data, "message": "fixture"}


@app.post("/webui/api/auth/login")
async def login():
    return ok({"token": "monitor-test-token"})


fixture_settings = {
            "theme": {
                "mode": "light",
                "primary_color": "#53634d",
                "has_wallpaper": False,
                "wallpaper_blur": 0,
                "wallpaper_opacity": 0.5,
            },
            "ui": {"language": "zh-CN", "font_size": "medium"},
            "system": {"auto_update": False, "check_update_on_startup": False},
            "config": {"auto_reload_after_save": False},
            "plugin_market": {"base_url": ""},
        }


class FixtureSettingsUpdate(BaseModel):
    updates: dict[str, JsonValue] = Field(default_factory=dict)


@app.get("/webui/api/webui/settings")
async def settings():
    return ok(fixture_settings)


@app.post("/webui/api/webui/settings")
async def update_settings(body: FixtureSettingsUpdate):
    """In-memory appearance settings only; never persist user settings in a test."""
    for key in ("theme", "ui"):
        changes = body.updates.get(key)
        if isinstance(changes, dict):
            fixture_settings[key].update(changes)
    return ok(fixture_settings)


@app.get("/webui/api/plugin-ui/list")
async def plugin_pages():
    return ok([])


@app.get("/webui/api/wallpaper/status")
async def wallpaper():
    return ok(
        {
            "has_wallpaper": False,
            "wallpaper_type": "none",
            "wallpaper_blur": 0,
            "wallpaper_opacity": 0.5,
        }
    )


@app.get("/webui/frontend/{path:path}")
async def frontend(path: str):
    """Serve only production-built frontend files within dist, with SPA fallback."""
    dist = (ROOT / "frontend/dist").resolve()
    target = (dist / path).resolve()
    if not target.is_relative_to(dist):
        return FileResponse(dist / "index.html")
    return FileResponse(target if target.is_file() else dist / "index.html")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9188)
