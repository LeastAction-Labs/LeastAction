# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from __future__ import annotations

from typing import Any

import yaml
from pydantic import BaseModel, Field

from src.common.utils import get_config_path


class ValidationPresetChecks(BaseModel):
    async_blocked: bool = True
    dunder_blocked: bool = True
    cyclic_import_check: bool = True
    secret_leak_check: bool = True
    logger_check: bool = True


class ValidationPreset(BaseModel):
    label: str = "Standard"
    deny_imports: list[str] = Field(default_factory=list)
    block_rules: dict[str, list[str]] = Field(default_factory=dict)
    warning_rules: dict[str, list[str]] = Field(default_factory=dict)
    attr_call_rules: list[list[str]] = Field(default_factory=list)
    checks: ValidationPresetChecks = Field(default_factory=ValidationPresetChecks)


def load_validation_preset() -> ValidationPreset:
    presets_path = get_config_path("validation_presets.yml")

    if not presets_path.exists():
        raise FileNotFoundError(f"Validation presets file not found: {presets_path}")

    with presets_path.open("r", encoding="utf-8") as f:
        raw: dict[str, Any] | None = yaml.safe_load(f)

    if not raw or not isinstance(raw, dict):
        raise ValueError(f"Validation presets file is empty or malformed: {presets_path}")

    data = raw.get("default")
    if not isinstance(data, dict):
        raise ValueError("Validation presets file must contain a 'default' preset")

    return ValidationPreset(**data)
