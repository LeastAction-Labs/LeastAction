# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.

from src.common.exceptions import VersionCompatibilityError
from src.common.utils import load_system_config


class VersionManager:
    def __init__(self) -> None:
        self.core_version: str = load_system_config()["core_version"]

    @staticmethod
    def parse_version(pattern: str) -> tuple[str | None, int, int, int]:
        OPERATORS = (">=", "<=", "!=", ">", "<")
        operator: str | None = None
        for op in OPERATORS:
            if pattern.startswith(op):
                operator = op
                pattern = pattern[len(op) :]
                break
        if operator is None and pattern.endswith(".*"):
            prefix = pattern[:-2]
            parts = prefix.split(".")
            if len(parts) == 1 and parts[0].isdigit():
                return "major-only", int(parts[0]), 0, 0
            raise ValueError(
                f"Version pattern '{pattern}.*' is not valid. Only major-level wildcards are supported (e.g. '0.*')."
            )
        parts = pattern.split(".")
        if len(parts) != 3:
            raise ValueError(
                f"Version pattern '{pattern}' must have exactly 3 numeric components (e.g. '0.1.2')."
            )
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        return operator, major, minor, patch

    def _version_tuple(self) -> tuple[int, int, int]:
        parts = self.core_version.split(".")
        if len(parts) != 3:
            raise ValueError(f"core_version '{self.core_version}' in system.yml must be 'X.Y.Z'.")
        return (int(parts[0]), int(parts[1]), int(parts[2]))

    def _pattern_matches_core(self, pattern: str) -> bool:
        operator, p_major, p_minor, p_patch = self.parse_version(pattern)
        core_tuple = self._version_tuple()
        p_tuple = (p_major, p_minor, p_patch)
        if operator == "major-only":
            return core_tuple[0] == p_major
        if operator is None:
            return core_tuple == p_tuple
        if operator == ">=":
            return core_tuple >= p_tuple
        if operator == ">":
            return core_tuple > p_tuple
        if operator == "<=":
            return core_tuple <= p_tuple
        if operator == "<":
            return core_tuple < p_tuple
        if operator == "!=":
            return core_tuple != p_tuple
        raise ValueError(f"Unsupported operator: '{operator}'")

    def check_compatibility(self, version_compatibility_list: list[str]) -> None:
        if not version_compatibility_list:
            return
        failed = [p for p in version_compatibility_list if not self._pattern_matches_core(p)]
        if failed:
            required = ", ".join(version_compatibility_list)
            raise VersionCompatibilityError(
                message=f"Item is not compatible with core version {self.core_version}. Required: {required}.",
                detail={
                    "core_version": self.core_version,
                    "required_patterns": version_compatibility_list,
                },
            )
