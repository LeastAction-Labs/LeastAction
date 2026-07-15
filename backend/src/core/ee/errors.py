from typing import Any

from src.common.exceptions import LAException


class LicenseError(LAException):
    """Raised when a feature is locked behind a license or user limits are reached"""

    def __init__(
        self,
        message: str | None = "This feature requires an Enterprise license.",
        detail: Any | None = None,
    ):
        super().__init__(402, message, detail)
