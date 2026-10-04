"""Regression coverage for model tests; no Neo-MoFox process or real API key needed.

Run from the repository root: python -m unittest discover -s tests -v
Requires the plugin dependencies (aiohttp, openai, pydantic, fastapi) and httpx.
Only host-framework imports are stubbed; requests use the real router and SDK.
"""
from __future__ import annotations

import asyncio
import copy
import importlib.util
import json
import logging
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

import httpx
import openai
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
REAL_OPENAI_CLIENT = openai.AsyncOpenAI


def load_plugin_modules():
    """Load this plugin without starting the unrelated Neo-MoFox host services."""
    prefix = "_webui_model_test_plugin"
    packages = {}
    for suffix, directory in {
        "": "Plugin", ".utils": "Plugin/utils", ".managers": "Plugin/managers",
        ".managers.config": "Plugin/managers/config",
        ".components": "Plugin/components", ".components.router": "Plugin/components/router",
        ".components.router.config": "Plugin/components/router/config",
    }.items():
        name = prefix + suffix
        packages[name] = types.ModuleType(name)
        packages[name].__path__ = [str(ROOT / directory)]

    host_config = types.ModuleType("src.core.config.model_config")
    host_config.ModelConfig = Mock()
    host_config.init_model_config = Mock()
    log_api = types.ModuleType("src.app.plugin_system.api.log_api")
    log_api.get_logger = lambda name: logging.getLogger(name)
    host_router = types.ModuleType("src.core.components.base.router")
    host_router.BaseRouter = type("BaseRouter", (), {})
    security = types.ModuleType("src.core.utils.security")

    def verify(x_api_key: str | None = Header(default=None)):
        if x_api_key != "local-test-token":
            raise HTTPException(status_code=403, detail="test authentication required")

    security.VerifiedDep = Depends(verify)
    packages.update({
        host_config.__name__: host_config, log_api.__name__: log_api,
        host_router.__name__: host_router, security.__name__: security,
    })

    def load(name, path):
        spec = importlib.util.spec_from_file_location(prefix + name, ROOT / path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    with patch.dict(sys.modules, packages):
        config_types = load(".utils.config_types", "Plugin/utils/config_types.py")
        manager = load(".managers.config.model_config_manager", "Plugin/managers/config/model_config_manager.py")
        packages[prefix + ".managers.config"].get_model_config_manager = manager.get_model_config_manager
        router = load(".components.router.config.model_config_router", "Plugin/components/router/config/model_config_router.py")
    return config_types, manager, router


config_types, manager_module, router_module = load_plugin_modules()


def draft_request():
    return {
        "provider_name": "draft-provider", "model_name": "draft-model",
        "provider": {"name": "draft-provider", "base_url": "https://draft.invalid/v1", "api_key": "draft-test-key"},
        "model": {"name": "draft-model", "model_identifier": "draft-identifier", "api_provider": "draft-provider"},
        "test_prompt": "hello draft", "timeout": 30,
    }


class ModelTestRegression(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.manager = manager_module.ModelConfigManager()
        self.load = manager_module.ModelConfig.load = Mock(side_effect=AssertionError("Snapshot must not read disk"))
        self.reload = manager_module.init_model_config = Mock(side_effect=AssertionError("Test must not reload config"))
        self.upstream_requests = []
        self.http_clients = []
        self.upstream_status = 200
        self.upstream_delay = 0
        self.upstream_error = None
        self.content = "draft response"

        async def upstream(request):
            self.upstream_requests.append(request)
            if self.upstream_delay:
                await asyncio.sleep(self.upstream_delay)
            if self.upstream_error:
                raise self.upstream_error
            if self.upstream_status != 200:
                return httpx.Response(self.upstream_status, json={"error": {"message": "mock provider rejected test"}})
            return httpx.Response(200, json={
                "id": "local-test", "object": "chat.completion", "created": 0,
                "model": json.loads(request.content)["model"],
                "choices": [{"index": 0, "message": {"role": "assistant", "content": self.content}, "finish_reason": "stop"}],
            })

        def client_factory(**kwargs):
            http_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
            self.http_clients.append(http_client)
            return REAL_OPENAI_CLIENT(**kwargs, http_client=http_client)

        self.client_factory = self.enterContext(patch.object(manager_module.openai, "AsyncOpenAI", side_effect=client_factory))
        self.app = FastAPI()
        router = object.__new__(router_module.ModelConfigRouter)
        router.app = self.app
        router.manager = self.manager
        router.register_endpoints()
        self.api = httpx.AsyncClient(
            transport=httpx.ASGITransport(self.app), base_url="http://test.local",
            headers={"X-API-Key": "local-test-token"},
        )

    async def asyncTearDown(self):
        await self.api.aclose()
        self.reload.assert_not_called()
        for client in self.http_clients:
            self.assertTrue(client.is_closed, "Temporary SDK HTTP client leaked")

    async def post(self, payload):
        return await self.api.post("/test", json=payload)

    def saved_config(self, payload=None):
        payload = payload or draft_request()
        provider = config_types.ModelTestProvider(**payload["provider"])
        model = config_types.ModelTestModel(**payload["model"])
        config = types.SimpleNamespace(models=[model], get_provider=Mock(return_value=provider))
        self.load.side_effect = None
        self.load.return_value = config
        return config

    def assert_upstream(self, payload, index=0):
        request = self.upstream_requests[index]
        self.assertEqual(str(request.url), payload["provider"]["base_url"] + "/chat/completions")
        self.assertEqual(request.headers["authorization"], "Bearer " + payload["provider"]["api_key"])
        body = json.loads(request.content)
        self.assertEqual(body["model"], payload["model"]["model_identifier"])
        self.assertEqual(body["messages"], [{"role": "user", "content": payload["test_prompt"]}])

    async def test_new_unsaved_provider_and_model_work_without_config_file(self):
        self.manager.model_config_path = ROOT / "does-not-exist" / "model.toml"
        payload = draft_request()
        response = await self.post(payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], 200)
        result = response.json()["data"]
        self.assertTrue(result["success"])
        self.assertEqual(result["response_text"], "draft response")
        self.assertEqual(result["model_identifier"], "draft-identifier")
        self.assertEqual(result["provider_base_url"], "https://draft.invalid/v1")
        self.assertGreaterEqual(result["latency_ms"], 0)
        self.assert_upstream(payload)
        self.load.assert_not_called()

    async def test_unsaved_new_model_under_saved_provider(self):
        self.saved_config()
        payload = draft_request()
        payload["model_name"] = payload["model"]["name"] = "new-model"
        payload["model"]["model_identifier"] = "new-id"
        response = await self.post(payload)
        self.assertTrue(response.json()["data"]["success"])
        self.assert_upstream(payload)
        self.load.assert_not_called()

    async def test_unsaved_edits_override_same_named_saved_config(self):
        self.saved_config()
        payload = draft_request()
        payload["provider"].update(base_url="https://edited.invalid/v2", api_key="edited-test-key")
        payload["model"]["model_identifier"] = "edited-id"
        response = await self.post(payload)
        self.assertTrue(response.json()["data"]["success"])
        self.assert_upstream(payload)
        self.load.assert_not_called()

    async def test_unsaved_rename_does_not_require_old_names(self):
        self.saved_config()
        payload = draft_request()
        payload["provider_name"] = payload["provider"]["name"] = payload["model"]["api_provider"] = "renamed-provider"
        payload["model_name"] = payload["model"]["name"] = "renamed-model"
        response = await self.post(payload)
        self.assertTrue(response.json()["data"]["success"])
        self.load.assert_not_called()

    async def test_testing_does_not_modify_toml_or_request(self):
        payload = draft_request()
        before = copy.deepcopy(payload)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.toml"
            path.write_bytes(b"# original config must remain unchanged\n")
            content, mtime = path.read_bytes(), path.stat().st_mtime_ns
            self.manager.model_config_path = path
            response = await self.post(payload)
            self.assertTrue(response.json()["data"]["success"])
            self.assertEqual(path.read_bytes(), content)
            self.assertEqual(path.stat().st_mtime_ns, mtime)
        self.assertEqual(payload, before)
        self.load.assert_not_called()

    async def test_legacy_saved_model_request_remains_supported(self):
        payload = draft_request()
        self.saved_config(payload)
        legacy = {key: value for key, value in payload.items() if key not in ("provider", "model")}
        response = await self.post(legacy)
        self.assertTrue(response.json()["data"]["success"])
        self.load.assert_called_once_with(self.manager.model_config_path)
        self.assert_upstream(payload)

    async def test_original_name_only_unsaved_model_reproduces_400(self):
        config = self.saved_config()
        config.models = []
        response = await self.post({"provider_name": "draft-provider", "model_name": "draft-model"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("模型不存在", response.json()["detail"])
        self.client_factory.assert_not_called()

    async def test_legacy_missing_provider_returns_specific_error(self):
        config = self.saved_config()
        config.get_provider.side_effect = KeyError("missing")
        response = await self.post({"provider_name": "missing", "model_name": "draft-model"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("提供商不存在", response.json()["detail"])

    async def test_legacy_model_from_different_provider_is_rejected(self):
        config = self.saved_config()
        config.models[0].api_provider = "other-provider"
        response = await self.post({"provider_name": "draft-provider", "model_name": "draft-model"})
        self.assertEqual(response.status_code, 400)
        self.client_factory.assert_not_called()

    async def test_incomplete_snapshot_never_falls_back_to_disk(self):
        for field in ("provider", "model"):
            for missing_value in ("omit", None):
                with self.subTest(field=field, missing_value=missing_value):
                    payload = draft_request()
                    if missing_value == "omit":
                        del payload[field]
                    else:
                        payload[field] = None
                    response = await self.post(payload)
                    self.assertEqual(response.status_code, 400)
                    self.assertIn("必须同时提供", response.json()["detail"])
        self.load.assert_not_called()
        self.client_factory.assert_not_called()

    async def test_mismatched_snapshot_names_are_rejected(self):
        for section, field in (("provider", "name"), ("model", "name"), ("model", "api_provider")):
            with self.subTest(section=section, field=field):
                payload = draft_request()
                payload[section][field] = "mismatch"
                response = await self.post(payload)
                self.assertEqual(response.status_code, 400)
                self.assertIn("不一致", response.json()["detail"])
        self.load.assert_not_called()
        self.client_factory.assert_not_called()

    async def test_blank_address_and_identifier_are_rejected(self):
        for section, field in (("provider", "base_url"), ("model", "model_identifier")):
            with self.subTest(field=field):
                payload = draft_request()
                payload[section][field] = "  "
                response = await self.post(payload)
                self.assertEqual(response.status_code, 400)
                self.assertIn("不能为空", response.json()["detail"])
        self.load.assert_not_called()
        self.client_factory.assert_not_called()

    async def test_first_nonempty_api_key_is_used_without_mutating_list(self):
        payload = draft_request()
        payload["provider"]["api_key"] = ["", "  ", " draft-test-key ", "second-test-key"]
        before = copy.deepcopy(payload)
        response = await self.post(payload)
        self.assertTrue(response.json()["data"]["success"])
        self.assertEqual(self.upstream_requests[0].headers["authorization"], "Bearer draft-test-key")
        self.assertEqual(payload, before)

    async def test_empty_api_keys_fail_without_network(self):
        for keys in ("", "  ", [], ["", "  "]):
            with self.subTest(keys=keys):
                payload = draft_request()
                payload["provider"]["api_key"] = keys
                response = await self.post(payload)
                result = response.json()["data"]
                self.assertFalse(result["success"])
                self.assertIn("密钥不能为空", result["error_message"])
        self.client_factory.assert_not_called()

    async def test_upstream_failure_is_a_test_result_and_client_is_closed(self):
        self.upstream_status = 401
        response = await self.post(draft_request())
        self.assertEqual(response.status_code, 200)
        result = response.json()["data"]
        self.assertFalse(result["success"])
        self.assertIn("mock provider rejected test", result["error_message"])
        self.assertEqual(result["model_identifier"], "draft-identifier")
        self.assertEqual(len(self.upstream_requests), 1)

    async def test_sdk_timeout_has_readable_error_and_no_retries(self):
        self.upstream_error = httpx.ReadTimeout("mock timeout")
        response = await self.post(draft_request())
        result = response.json()["data"]
        self.assertFalse(result["success"])
        self.assertEqual(result["error_message"], "模型测试超时（30 秒）")
        self.assertEqual(len(self.upstream_requests), 1)

    async def test_whole_test_deadline_cancels_hanging_request(self):
        self.upstream_delay = 10
        payload = draft_request()
        payload["timeout"] = 1
        async with asyncio.timeout(3):
            response = await self.post(payload)
        self.assertEqual(response.json()["data"]["error_message"], "模型测试超时（1 秒）")
        self.assertEqual(len(self.upstream_requests), 1)

    async def test_parallel_drafts_do_not_share_configuration(self):
        first, second = draft_request(), draft_request()
        second["provider"].update(base_url="https://second.invalid/v1", api_key="second-test-key")
        second["model"]["model_identifier"] = "second-id"
        responses = await asyncio.gather(self.post(first), self.post(second))
        self.assertTrue(all(response.json()["data"]["success"] for response in responses))
        by_host = {request.url.host: request for request in self.upstream_requests}
        self.assertEqual(by_host["draft.invalid"].headers["authorization"], "Bearer draft-test-key")
        self.assertEqual(by_host["second.invalid"].headers["authorization"], "Bearer second-test-key")
        self.load.assert_not_called()

    async def test_test_route_still_uses_verified_dependency(self):
        response = await self.api.post("/test", json=draft_request(), headers={"X-API-Key": ""})
        self.assertEqual(response.status_code, 403)
        self.client_factory.assert_not_called()

    def test_snapshot_api_key_is_not_in_repr(self):
        request = config_types.ModelTestRequest(**draft_request())
        self.assertNotIn("draft-test-key", repr(request))
        self.assertNotIn("draft-test-key", repr(request.provider))

    def test_timeout_must_be_positive(self):
        for timeout in (0, -1):
            payload = draft_request()
            payload["timeout"] = timeout
            with self.assertRaises(ValidationError):
                config_types.ModelTestRequest(**payload)


if __name__ == "__main__":
    unittest.main()
