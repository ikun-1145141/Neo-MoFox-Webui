"""Typed contracts for the authenticated local-package import workflow."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class PluginImportPreview(BaseModel):
    upload_id: str
    expires_at: str
    filename: str
    size_bytes: int
    plugin_name: str
    version: str
    description: str = ""
    installed_version: str | None = None
    overwrite_required: bool = False
    self_update: bool = False
    can_import: bool = True
    warnings: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)


class PluginImportCommit(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    upload_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    confirm_overwrite: bool = False


class PluginImportResult(BaseModel):
    plugin_name: str
    version: str
    written: bool = False
    loaded: bool = False
    restart_required: bool = False
    load_error: str | None = None


class PluginImportOperation(BaseModel):
    operation_id: str
    plugin_name: str
    status: Literal["queued", "running", "succeeded", "failed"] = "queued"
    stage: Literal["queued", "validating", "storing", "loading", "completed", "failed"] = "queued"
    progress: int = Field(default=0, ge=0, le=100)
    message: str = "等待导入"
    created_at: str
    updated_at: str
    error_message: str | None = None
    result: PluginImportResult | None = None


class PluginImportDeleteResult(BaseModel):
    deleted: bool = True
