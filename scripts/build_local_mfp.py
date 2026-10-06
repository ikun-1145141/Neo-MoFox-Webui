"""Package Plugin + an already-built frontend into a local, unpublished MFP.

No plugin imports, host startup, package installation, test execution or publishing.
Run from any directory: python scripts/build_local_mfp.py --output ../webui.mfp
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {"__pycache__", ".git", "node_modules", ".venv"}


def package(output: Path) -> None:
    """Write source and current dist assets with manifest.json at archive root."""
    source = ROOT / "Plugin"
    dist = ROOT / "frontend" / "dist"
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if not (dist / "index.html").is_file():
        raise SystemExit("frontend/dist/index.html missing: build the frontend first")
    if output.suffix.lower() != ".mfp":
        raise SystemExit("Output must end in .mfp")
    output = output.resolve()
    if output.is_relative_to(source) or output.is_relative_to(dist):
        raise SystemExit("Output must not be inside the packaged source or dist directories")
    if output.exists():
        raise SystemExit(f"Refusing to overwrite existing artifact: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    entries: list[tuple[Path, str]] = []
    for file in sorted(source.rglob("*")):
        relative = file.relative_to(source)
        if (file.is_file() and not file.is_symlink() and "static" not in relative.parts
                and not set(relative.parts) & EXCLUDED_PARTS and file.suffix not in {".pyc", ".pyo"}
                and not file.name.startswith(".env")):
            entries.append((file, relative.as_posix()))
    for file in sorted(dist.rglob("*")):
        if file.is_file() and not file.is_symlink():
            entries.append((file, "static/" + file.relative_to(dist).as_posix()))
    license_file = ROOT / "LICENSE"
    if license_file.is_file():
        entries.append((license_file, "LICENSE"))
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file, name in entries:
            archive.write(file, name)
    with output.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    checksum = output.with_suffix(output.suffix + ".sha256")
    checksum.write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    print(f"Package: {output}")
    print(f"Plugin: {manifest['name']} {manifest['version']}")
    print(f"Files: {len(entries)}; compressed: {output.stat().st_size}; uncompressed: {sum(file.stat().st_size for file, _ in entries)}")
    print(f"SHA-256: {digest}")
    print("NOT TESTED. No host was started and no plugin was installed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    package(parser.parse_args().output)
