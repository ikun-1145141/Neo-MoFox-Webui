"""请求监视器接口测试。

    使用真实原生检查器校验需要身份认证的记录接口，不启动完整主程序。
"""

from __future__ import annotations
import importlib.util
import os
import logging
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
import httpx
from fastapi import Depends, FastAPI, Header, HTTPException

ROOT = Path(__file__).resolve().parents[1]
HOST = Path(os.environ.get("NEO_MOFOX_ROOT", ROOT.parent / "Neo-MoFox")).expanduser().resolve()


def load_file(name, path):
    """加载源码文件，但不启动主程序或插件入口。

        参数：
            name：加载后使用的模块名称。
            path：源码文件路径。

        返回：
            ModuleType：已加载的模块。
    """
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


native = load_file(
    "_webui_monitor_native", HOST / "src/kernel/llm/request_inspector.py"
)


def load_transport(inspector):
    """仅模拟框架路由注册和认证依赖，保留真实采集器及数据传输逻辑。

        参数：
            inspector：供接口使用的原生请求检查器。

        返回：
            tuple：已注册的路由实例、管理器模块和数据模型模块。
    """
    prefix = "_webui_monitor_plugin"
    modules = {}
    for suffix, directory in {
        "": "Plugin",
        ".utils": "Plugin/utils",
        ".managers": "Plugin/managers",
        ".components": "Plugin/components",
        ".components.router": "Plugin/components/router",
    }.items():
        module = types.ModuleType(prefix + suffix)
        module.__path__ = [str(ROOT / directory)]
        modules[module.__name__] = module
    host_llm = types.ModuleType("src.kernel.llm")
    host_llm.get_inspector = lambda: inspector
    logger = types.ModuleType("src.app.plugin_system.api.log_api")
    logger.get_logger = lambda name: logging.getLogger(name)
    base = types.ModuleType("src.core.components.base.router")

    class BaseRouter:
        def __init__(self, plugin):
            self.app = FastAPI()

    base.BaseRouter = BaseRouter
    security = types.ModuleType("src.core.utils.security")

    def verify(x_api_key: str | None = Header(default=None)):
        if x_api_key != "monitor-test-token":
            raise HTTPException(403, "authentication required")

    security.VerifiedDep = Depends(verify)
    for item in [host_llm, logger, base, security]:
        modules[item.__name__] = item
    with patch.dict(sys.modules, modules):
        load_file(prefix + ".utils.response", ROOT / "Plugin/utils/response.py")
        schema = load_file(
            prefix + ".utils.request_inspector_types",
            ROOT / "Plugin/utils/request_inspector_types.py",
        )
        manager = load_file(
            prefix + ".managers.request_inspector_manager",
            ROOT / "Plugin/managers/request_inspector_manager.py",
        )
        router = load_file(
            prefix + ".components.router.request_inspector_router",
            ROOT / "Plugin/components/router/request_inspector_router.py",
        )
        instance = router.RequestInspectorRouter(None)
        instance.register_endpoints()
    return instance, manager, schema


class RequestMonitorTransportTests(unittest.IsolatedAsyncioTestCase):
    """验证接口认证、响应封装、数据模型一致性及仅使用内存缓冲区的语义。"""

    async def asyncSetUp(self):
        self.inspector = native.RequestInspector()
        self.router, self.manager, self.schema = load_transport(self.inspector)
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.router.app),
            base_url="http://test",
            headers={"X-API-Key": "monitor-test-token"},
        )

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_authentication_for_every_new_endpoint(self):
        for method, path in [
            ("GET", "/records"),
            ("GET", "/records/1"),
            ("DELETE", "/records"),
        ]:
            response = await self.client.request(
                method, path, headers={"X-API-Key": "wrong"}
            )
            self.assertEqual(response.status_code, 403)

    async def test_list_is_metadata_only_and_stats_are_current_buffer_only(self):
        record_id = self.inspector.capture(
            "responses.create",
            {"model": "demo", "input": "private prompt", "Authorization": "secret"},
            native=True,
        )
        self.inspector.start(record_id, {"model": "demo", "input": "private prompt"})
        self.inspector.finish(
            record_id,
            {
                "kind": "chat",
                "message": "private response",
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
            },
        )
        response = await self.client.get("/records")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.schema.InspectorRecordsSnapshot.model_validate(data)
        self.assertEqual(data["stats"]["tokens_in"], 3)
        self.assertEqual(data["stats"]["by_status"], {"succeeded": 1})
        self.assertNotIn("private prompt", response.text)
        self.assertNotIn("private response", response.text)
        self.assertNotIn("params", data["records"][0])

    async def test_detail_is_typed_sanitized_and_missing_record_is_standard_404(self):
        record_id = self.inspector.capture(
            "chat.completions.create",
            {
                "model": "demo",
                "messages": [{"role": "user", "content": "hello"}],
                "extra_headers": {"Authorization": "Bearer secret"},
            },
        )
        response = await self.client.get(f"/records/{record_id}")
        data = response.json()["data"]
        self.schema.InspectorRecordDetail.model_validate(data)
        self.assertEqual(data["capture_info"]["redacted"], True)
        self.assertNotIn("Bearer secret", response.text)
        self.assertEqual(data["status"], "captured")
        missing = await self.client.get("/records/999")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["code"], 404)
        self.assertIsNone(missing.json()["data"])

    async def test_clear_reports_count_and_late_finish_cannot_reinsert(self):
        record_id = self.inspector.capture("test", {}, native=True)
        response = await self.client.delete("/records")
        self.assertEqual(response.json()["data"]["cleared_count"], 1)
        self.inspector.finish(record_id)
        self.assertEqual(
            (await self.client.get("/records")).json()["data"]["stats"]["total"], 0
        )

    async def test_no_old_paths_or_analytics_aliases_remain(self):
        for method, path in [
            ("GET", "/requests"),
            ("GET", "/requests/1"),
            ("DELETE", "/requests"),
            ("GET", "/analytics"),
        ]:
            self.assertEqual((await self.client.request(method, path)).status_code, 404)

    async def test_incompatible_host_fails_visibly_without_fallback(self):
        with patch.object(
            self.router.inspector_manager,
            "list_records",
            side_effect=AttributeError("old host"),
        ):
            response = await self.client.get("/records")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], 500)
        self.assertNotIn("old host", response.text)

    async def test_openapi_exposes_concrete_models_not_arbitrary_dict(self):
        schemas = self.router.app.openapi()["components"]["schemas"]
        for name in [
            "InspectorRecordDetail",
            "InspectorRecordsSnapshot",
            "InspectorClearResult",
            "InspectorCaptureInfo",
            "InspectorResponse",
        ]:
            self.assertIn(name, schemas)


    async def test_missing_public_capabilities_fail_safely_on_all_endpoints(self):
        for missing in ("snapshot", "get_record", "clear_snapshot"):
            methods = {name: getattr(self.inspector, name) for name in
                       ("snapshot", "get_record", "clear_snapshot") if name != missing}
            with patch.object(self.manager, "_host_get_inspector", return_value=types.SimpleNamespace(**methods)):
                for method, path in [("GET", "/records"), ("GET", "/records/1"), ("DELETE", "/records")]:
                    with self.assertLogs("request_inspector_router", level="ERROR") as logs:
                        response = await self.client.request(method, path)
                    self.assertEqual(response.status_code, 500)
                    self.assertEqual(response.json()["code"], 500)
                    self.assertIsNone(response.json()["data"])
                    self.assertIn("配套升级", response.json()["message"])
                    self.assertIn("incompatible_host", " ".join(logs.output))

    async def test_missing_host_factory_is_reported_without_import_time_failure(self):
        with patch.object(self.manager, "_host_get_inspector", None):
            with self.assertLogs("request_inspector_router", level="ERROR"):
                response = await self.client.get("/records")
        self.assertEqual(response.status_code, 500)
        self.assertIn("配套升级", response.json()["message"])

    async def test_exceptions_and_validation_inputs_never_reach_logs_or_http(self):
        secret = "fixture-sensitive-value-not-a-real-key"
        try:
            self.schema.InspectorClearResult.model_validate(
                {"instance_id": secret, "revision": secret, "cleared_count": 0})
        except Exception as error:
            validation_error = error
        for error in (validation_error, RuntimeError(secret), AttributeError(secret)):
            for name, method, path in [("list_records", "GET", "/records"),
                                       ("get_record", "GET", "/records/1"),
                                       ("clear_records", "DELETE", "/records")]:
                with patch.object(self.router.inspector_manager, name, side_effect=error):
                    with self.assertLogs("request_inspector_router", level="ERROR") as logs:
                        response = await self.client.request(method, path)
                self.assertEqual(response.status_code, 500)
                self.assertNotIn(secret, response.text)
                self.assertNotIn(secret, " ".join(logs.output))
                self.assertNotIn("input_value", " ".join(logs.output))
                self.assertTrue(all(record.exc_info is None for record in logs.records))

    async def test_unknown_hierarchy_and_raw_events_survive_typed_transport(self):
        params = {"model": "fixture", "messages": [], "extra_body": {"a/b~": [None, False, 0, "", {"unknown": [1, 2]}]},
                  "extra_query": {"vendor_mode": "test"}, "extra_headers": {"X-Debug": "fixture", "Authorization": "secret-header"}}
        rid = self.inspector.capture("messages.stream", params, native=True, stream=True)
        self.inspector.start(rid, params)
        self.inspector.raw(rid, {"vendor_event": {"unknown": [1, None]}}, event=True)
        self.inspector.update(rid, {"kind": "chat", "message": "partial", "tool_calls": [{"id": "t1", "args": "{\"partial\":"}]}, content=True)
        data = (await self.client.get(f"/records/{rid}")).json()["data"]
        self.assertEqual(data["params"]["extra_body"], params["extra_body"])
        self.assertEqual(data["params"]["extra_query"], params["extra_query"])
        self.assertEqual(data["raw_events"], [{"vendor_event": {"unknown": [1, None]}}])
        self.assertEqual(data["status"], "streaming")
        self.assertEqual(data["api_name"], "messages.stream")
        self.assertIsNone(data["tokens_in"])
        self.assertIsNone(data["tokens_out"])
        self.assertNotIn("secret-header", str(data))

    async def test_all_response_kinds_and_capture_flags_are_preserved(self):
        for kind, result in [("chat", {"message": "text", "reasoning_content": "reason"}),
                             ("embedding", {"embeddings": [[0.1, 0.2], [0.3]]}),
                             ("rerank", {"results": [{"index": 0, "score": 0.9, "vendor_extra": True}]})]:
            rid = self.inspector.capture("fixture", {}, native=True)
            self.inspector.start(rid)
            self.inspector.raw(rid, object())
            self.inspector.finish(rid, {"kind": kind, **result})
            data = (await self.client.get(f"/records/{rid}")).json()["data"]
            self.assertEqual(data["response"]["kind"], kind)
            for field, value in result.items():
                self.assertEqual(data["response"][field], value)
            self.assertTrue(data["capture_info"]["raw_unavailable"])
