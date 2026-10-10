"""Regression coverage for plugin package (.zip / .mfp) validation.

The validator is pure standard library, so it is loaded by file path without
stubbing any Neo-MoFox host modules.
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 50 * 1024 * 1024


def load_package_module():
    """Load Plugin/utils/plugin_package.py without importing the plugin package."""
    path = ROOT / "Plugin" / "utils" / "plugin_package.py"
    spec = importlib.util.spec_from_file_location("_webui_plugin_package", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


plugin_package = load_package_module()


def manifest(name: str = "demo_plugin", entry_point: str = "plugin.py") -> bytes:
    return json.dumps(
        {
            "name": name,
            "version": "1.0.0",
            "description": "demo",
            "author": "test",
            "dependencies": {"plugins": [], "components": []},
            "entry_point": entry_point,
        }
    ).encode("utf-8")


class PluginPackageValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def build(self, entries: dict[str, bytes], suffix: str = ".zip") -> Path:
        path = self.tmp / f"package{suffix}"
        with zipfile.ZipFile(path, "w") as archive:
            for name, data in entries.items():
                archive.writestr(name, data)
        return path

    def assert_rejected(self, path: Path, message: str) -> None:
        with self.assertRaises(plugin_package.PluginPackageError) as context:
            plugin_package.validate_plugin_package(path, MAX_BYTES)
        self.assertIn(message, str(context.exception))

    def test_accepts_root_level_zip(self) -> None:
        path = self.build({"manifest.json": manifest(), "plugin.py": b"x = 1\n"})
        result = plugin_package.validate_plugin_package(path, MAX_BYTES)
        self.assertEqual(result["name"], "demo_plugin")

    def test_accepts_mfp_suffix(self) -> None:
        path = self.build({"manifest.json": manifest(), "plugin.py": b""}, suffix=".mfp")
        result = plugin_package.validate_plugin_package(path, MAX_BYTES)
        self.assertEqual(result["version"], "1.0.0")

    def test_accepts_single_directory_prefix(self) -> None:
        path = self.build(
            {
                "demo_plugin/manifest.json": manifest(),
                "demo_plugin/plugin.py": b"",
            }
        )
        result = plugin_package.validate_plugin_package(path, MAX_BYTES)
        self.assertEqual(result["name"], "demo_plugin")

    def test_rejects_parent_traversal(self) -> None:
        path = self.build(
            {"manifest.json": manifest(), "plugin.py": b"", "../evil.py": b""}
        )
        self.assert_rejected(path, "非法路径")

    def test_rejects_absolute_path(self) -> None:
        path = self.build(
            {"manifest.json": manifest(), "plugin.py": b"", "/etc/evil": b""}
        )
        self.assert_rejected(path, "非法路径")

    def test_rejects_symlink(self) -> None:
        path = self.tmp / "symlink.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("manifest.json", manifest())
            archive.writestr("plugin.py", b"")
            link = zipfile.ZipInfo("link")
            link.external_attr = (0o120777 << 16)
            archive.writestr(link, "/etc/passwd")
        self.assert_rejected(path, "符号链接")

    def test_rejects_uncompressed_size_over_limit(self) -> None:
        path = self.build(
            {"manifest.json": manifest(), "plugin.py": b"", "big.bin": b"0" * 4096}
        )
        with self.assertRaises(plugin_package.PluginPackageError) as context:
            plugin_package.validate_plugin_package(path, 1024)
        self.assertIn("超过大小限制", str(context.exception))

    def test_rejects_missing_manifest(self) -> None:
        path = self.build({"plugin.py": b""})
        self.assert_rejected(path, "manifest.json")

    def test_rejects_multiple_manifests(self) -> None:
        path = self.build(
            {
                "a/manifest.json": manifest(),
                "a/plugin.py": b"",
                "b/manifest.json": manifest(),
                "b/plugin.py": b"",
            }
        )
        self.assert_rejected(path, "唯一")

    def test_rejects_missing_entry_point(self) -> None:
        path = self.build({"manifest.json": manifest(entry_point="main.py")})
        self.assert_rejected(path, "入口文件不存在")

    def test_rejects_non_object_manifest(self) -> None:
        path = self.build({"manifest.json": b"[]", "plugin.py": b""})
        self.assert_rejected(path, "JSON 对象")

    def test_rejects_non_zip_content(self) -> None:
        path = self.tmp / "fake.zip"
        path.write_bytes(b"not a zip archive")
        self.assert_rejected(path, "格式无效")

    def test_rejects_empty_archive(self) -> None:
        path = self.tmp / "empty.zip"
        with zipfile.ZipFile(path, "w"):
            pass
        self.assert_rejected(path, "为空")


class PluginIdValidationTest(unittest.TestCase):
    def test_accepts_regular_ids(self) -> None:
        for plugin_id in ("demo_plugin", "neo-mofox-webui", "a.b-c_1"):
            plugin_package.validate_plugin_id(plugin_id)

    def test_rejects_unsafe_ids(self) -> None:
        for plugin_id in ("", "../evil", "a/b", "a\\b", ".hidden", "-dash", "x" * 129):
            with self.assertRaises(plugin_package.PluginPackageError):
                plugin_package.validate_plugin_id(plugin_id)


if __name__ == "__main__":
    unittest.main()
