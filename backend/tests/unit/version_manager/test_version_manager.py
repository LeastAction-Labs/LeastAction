# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from unittest.mock import patch

import pytest

from src.common.exceptions import VersionCompatibilityError
from src.core.version_manager.service import VersionManager


def make_vm(core_version: str) -> VersionManager:
    with patch(
        "src.core.version_manager.service.load_system_config",
        return_value={"core_version": core_version},
    ):
        return VersionManager()


class TestParseVersion:
    def test_exact_version(self):
        op, major, minor, patch = VersionManager.parse_version("1.2.3")
        assert (op, major, minor, patch) == (None, 1, 2, 3)

    def test_gte_operator(self):
        op, major, minor, patch = VersionManager.parse_version(">=1.0.0")
        assert (op, major, minor, patch) == (">=", 1, 0, 0)

    def test_gt_operator(self):
        op, major, minor, patch = VersionManager.parse_version(">2.5.1")
        assert (op, major, minor, patch) == (">", 2, 5, 1)

    def test_lte_operator(self):
        op, major, minor, patch = VersionManager.parse_version("<=3.0.0")
        assert (op, major, minor, patch) == ("<=", 3, 0, 0)

    def test_lt_operator(self):
        op, major, minor, patch = VersionManager.parse_version("<2.0.0")
        assert (op, major, minor, patch) == ("<", 2, 0, 0)

    def test_ne_operator(self):
        op, major, minor, patch = VersionManager.parse_version("!=1.5.0")
        assert (op, major, minor, patch) == ("!=", 1, 5, 0)

    def test_malformed_missing_patch(self):
        with pytest.raises(ValueError):
            VersionManager.parse_version("1.0")

    def test_malformed_too_many_parts(self):
        with pytest.raises(ValueError):
            VersionManager.parse_version("1.0.0.0")

    def test_malformed_non_numeric(self):
        with pytest.raises(ValueError):
            VersionManager.parse_version("a.b.c")

    def test_operator_prefix_not_stripped_as_single_char(self):
        # ">=1.0.0" must not be parsed as ">" + "=1.0.0"
        op, major, minor, patch = VersionManager.parse_version(">=1.0.0")
        assert op == ">="
        assert major == 1

    def test_major_wildcard_parse(self):
        op, major, minor, patch = VersionManager.parse_version("0.*")
        assert (op, major, minor, patch) == ("major-only", 0, 0, 0)


class TestCheckCompatibility:
    def test_empty_list_always_passes(self):
        vm = make_vm("0.0.0")
        vm.check_compatibility([])  # must not raise

    def test_all_patterns_match_passes(self):
        vm = make_vm("1.2.3")
        vm.check_compatibility([">=1.0.0", "<2.0.0"])  # (1,2,3) satisfies both

    def test_one_pattern_fails_raises(self):
        vm = make_vm("1.2.3")
        with pytest.raises(VersionCompatibilityError):
            vm.check_compatibility([">=1.0.0", "<1.2.0"])  # (1,2,3) fails <1.2.0

    def test_all_patterns_fail_raises(self):
        vm = make_vm("0.0.0")
        with pytest.raises(VersionCompatibilityError):
            vm.check_compatibility([">=1.0.0", "<2.0.0"])

    def test_exact_match_passes(self):
        vm = make_vm("1.2.3")
        vm.check_compatibility(["1.2.3"])

    def test_exact_match_fails(self):
        vm = make_vm("1.2.4")
        with pytest.raises(VersionCompatibilityError):
            vm.check_compatibility(["1.2.3"])

    def test_ne_passes_when_different(self):
        vm = make_vm("1.0.0")
        vm.check_compatibility(["!=0.0.0"])

    def test_ne_fails_when_same(self):
        vm = make_vm("0.0.0")
        with pytest.raises(VersionCompatibilityError):
            vm.check_compatibility(["!=0.0.0"])

    def test_error_contains_core_version_and_patterns(self):
        vm = make_vm("0.0.0")
        with pytest.raises(VersionCompatibilityError) as exc_info:
            vm.check_compatibility([">=1.0.0"])
        err = exc_info.value
        assert "0.0.0" in err.message
        assert ">=1.0.0" in err.message
        assert err.detail["core_version"] == "0.0.0"
        assert err.detail["required_patterns"] == [">=1.0.0"]

    def test_single_gte_boundary_equal_passes(self):
        vm = make_vm("1.0.0")
        vm.check_compatibility([">=1.0.0"])

    def test_single_gt_boundary_equal_fails(self):
        vm = make_vm("1.0.0")
        with pytest.raises(VersionCompatibilityError):
            vm.check_compatibility([">1.0.0"])

    def test_single_lt_boundary_equal_fails(self):
        vm = make_vm("2.0.0")
        with pytest.raises(VersionCompatibilityError):
            vm.check_compatibility(["<2.0.0"])

    def test_single_lte_boundary_equal_passes(self):
        vm = make_vm("2.0.0")
        vm.check_compatibility(["<=2.0.0"])

    def test_range_current_version_in_range(self):
        vm = make_vm("1.5.0")
        vm.check_compatibility([">=1.0.0", "<=2.0.0"])

    def test_range_current_version_below_range(self):
        vm = make_vm("0.9.0")
        with pytest.raises(VersionCompatibilityError):
            vm.check_compatibility([">=1.0.0", "<=2.0.0"])

    def test_range_current_version_above_range(self):
        vm = make_vm("3.0.0")
        with pytest.raises(VersionCompatibilityError):
            vm.check_compatibility([">=1.0.0", "<=2.0.0"])

    def test_wildcard_matches_same_major(self):
        vm = make_vm("0.5.3")
        vm.check_compatibility(["0.*"])  # must not raise

    def test_wildcard_mismatch_raises(self):
        vm = make_vm("1.0.0")
        with pytest.raises(VersionCompatibilityError):
            vm.check_compatibility(["0.*"])
