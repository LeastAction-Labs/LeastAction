# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.

from pydantic import BaseModel, Field


class CodeblockValidationEntry(BaseModel):
    code: str
    message: str
    file: str | None = None
    line: int | None = None


class ValidationResult(BaseModel):
    valid: bool
    errors: list[CodeblockValidationEntry] = Field(default_factory=list)
    warnings: list[CodeblockValidationEntry] = Field(default_factory=list)


class ValidateCodeblockRequest(BaseModel):
    codeblock: dict[str, str]
    item_type: str
