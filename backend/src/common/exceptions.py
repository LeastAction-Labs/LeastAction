# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from typing import Any


class LAException(Exception):
    http_status_code: int
    message: str | None = None
    detail: Any | None = None

    def __init__(
        self, http_status_code: int, message: str | None = None, detail: Any | None = None
    ):
        self.http_status_code = http_status_code
        self.message = message
        self.detail = detail

    def __str__(self):
        return f"{self.http_status_code} {self.message}"


class NotFoundError(LAException):
    def __init__(self, message: str | None = None, detail: Any | None = None):
        super().__init__(404, message, detail)


class InvalidArgumentError(LAException):
    def __init__(self, message: str | None = None, detail: Any | None = None):
        super().__init__(400, message, detail)


class UnprocessableEntityError(LAException):
    def __init__(self, message: str | None = None, detail: Any | None = None):
        super().__init__(422, message, detail)


class SchemaError(LAException):
    def __init__(self, message: str | None = None, detail: Any | None = None):
        super().__init__(422, message, detail)


class ConflictError(LAException):
    def __init__(self, message: str | None = None, detail: Any | None = None):
        super().__init__(409, message, detail)


class AIError(LAException):
    def __init__(self, message: str | None = None, detail: Any | None = None):
        super().__init__(500, message, detail)


class PartialGenerationError(LAException):
    def __init__(self, message: str | None = None, detail: Any | None = None):
        super().__init__(206, message, detail)


class TaskValidationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class CeleryExecutionError(LAException):
    """Raised when Celery execution fails at the orchestration level"""

    def __init__(self, message: str | None = None, detail: Any | None = None):
        super().__init__(500, message, detail)


class InvalidOperatorError(LAException):
    """Raised when the operator attached to the task is invalid"""

    def __init__(self, message=None, detail=None):
        super().__init__(422, message, detail)


class AuthorizationError(LAException):
    def __init__(self, message: str | None = None, detail: Any | None = None):
        super().__init__(403, message, detail)


class VersionCompatibilityError(LAException):
    """Raised when an item's version_compatibility does not match the system core_version."""

    def __init__(self, message: str | None = None, detail: Any | None = None):
        super().__init__(422, message, detail)


class ResourceLockedError(LAException):
    """Raised when a resource is currently locked by another process or administrative action"""

    def __init__(
        self,
        message: str | None = "The requested resource is currently locked. Please try again later.",
        detail: Any | None = None,
    ):
        super().__init__(423, message, detail)


class UnsupportedMediaTypeError(LAException):
    """Raised when the file format requested is not supported for streaming operations"""

    def __init__(self, message: str | None = None, detail: Any | None = None):
        super().__init__(415, message, detail)


class AuthenticationError(LAException):
    """Raised when authentication credentials are missing or invalid"""

    def __init__(
        self, message: str | None = "Could not authenticate user.", detail: Any | None = None
    ):
        super().__init__(401, message, detail)
