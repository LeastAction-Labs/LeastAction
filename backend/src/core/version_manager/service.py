# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.

from src.common.exceptions import UnprocessableEntityError, VersionCompatibilityError
from src.common.utils import load_system_config


class VersionManager:
    def __init__(self) -> None:
        self.core_version: str = load_system_config()["core_version"]

    @staticmethod
    def parse_version(pattern: str) -> tuple[str | None, int, int, int]:
        OPERATORS = (">=", "<=", "!=", ">", "<")
        pattern = pattern.strip()
        operator: str | None = None
        for op in OPERATORS:
            if pattern.startswith(op):
                operator = op
                pattern = pattern[len(op) :].strip()
                break
        if operator is None and pattern.endswith(".*"):
            prefix = pattern[:-2].strip()
            # isdecimal() rejects negatives, signs, unicode digits and empty strings,
            # so only a plain non-negative major (e.g. "0") is accepted.
            if prefix.isdecimal():
                return "major-only", int(prefix), 0, 0
            raise ValueError(
                f"Version pattern '{pattern}' is not valid. Only major-level wildcards are supported (e.g. '0.*')."
            )
        parts = [p.strip() for p in pattern.split(".")]
        if len(parts) != 3 or not all(p.isdecimal() for p in parts):
            raise ValueError(
                f"Version pattern '{pattern}' must have exactly 3 non-negative numeric "
                "components (e.g. '0.1.2')."
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

    @staticmethod
    def parse_semver(version: object) -> tuple[int, int, int]:
        """
        Parse a plain 'X.Y.Z' semver into a tuple of non-negative ints.
        Rejects negatives, non-numeric, and malformed strings.
        """
        if not isinstance(version, str):
            raise UnprocessableEntityError(
                message="Invalid version",
                detail=f"version must be a string like '1.2.3'. Got: {version!r}.",
            )
        parts = version.strip().split(".")
        # isdecimal() is False for negatives ('-1'), signs ('+1'), empty parts, and
        # unicode digits ('²') that int() would then reject — so it rejects negative,
        # malformed, or non-ASCII-numeric segments outright without a later ValueError.
        if len(parts) != 3 or not all(p.isdecimal() for p in parts):
            raise UnprocessableEntityError(
                message="Invalid version",
                detail=(
                    f"version '{version}' must be 'X.Y.Z' with three non-negative "
                    "integer segments (e.g. '0.1.0'). Negative numbers are not allowed."
                ),
            )
        return (int(parts[0]), int(parts[1]), int(parts[2]))

    def validate_version_transition(
        self, new_version: object, old_version: object | None = None
    ) -> None:
        """
        Enforce a valid version on save for any item:
        - new_version must be a valid non-negative 'X.Y.Z' semver
        - it must not go backwards relative to the existing version
        """
        new = self.parse_semver(new_version)
        if old_version is None:
            return
        try:
            old = self.parse_semver(old_version)
        except UnprocessableEntityError:
            # Existing value is malformed (legacy data) — don't block the fix.
            return
        if new < old:
            old_s = ".".join(map(str, old))
            new_s = ".".join(map(str, new))
            raise UnprocessableEntityError(
                message="Version cannot be decreased",
                detail=(
                    f"New version {new_s} is lower than the current version {old_s}. "
                    "The version must stay the same or increase."
                ),
            )

    def check_compatibility(self, version_compatibility_list: list[str]) -> None:
        if not version_compatibility_list:
            return
        # A malformed pattern must surface as a clean 422, not a 500. parse_version
        # raises ValueError for garbage entries (e.g. 'abc', '>=x', '1.*'); collect
        # those separately so the caller learns the pattern is invalid rather than
        # incompatible.
        malformed: list[str] = []
        failed: list[str] = []
        for p in version_compatibility_list:
            try:
                matches = self._pattern_matches_core(p)
            except ValueError:
                malformed.append(p)
                continue
            if not matches:
                failed.append(p)
        if malformed:
            raise UnprocessableEntityError(
                message="Invalid core compatibility pattern(s): " + ", ".join(malformed),
                detail=(
                    "Each core compatibility entry must be an exact version ('0.4.0'), "
                    "an operator range ('>=0.4.0'), or a major wildcard ('0.*'). "
                    "Invalid: " + ", ".join(repr(p) for p in malformed) + "."
                ),
            )
        if failed:
            required = ", ".join(version_compatibility_list)
            raise VersionCompatibilityError(
                message=f"Item is not compatible with core version {self.core_version}. Required: {required}.",
                detail={
                    "core_version": self.core_version,
                    "required_patterns": version_compatibility_list,
                },
            )
