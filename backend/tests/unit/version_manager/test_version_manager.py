# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from unittest.mock import patch

import pytest

from src.common.exceptions import UnprocessableEntityError, VersionCompatibilityError
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

    @pytest.mark.parametrize(
        "pattern,expected",
        [
            (" 0.*", ("major-only", 0, 0, 0)),
            ("0.* ", ("major-only", 0, 0, 0)),
            (" >=0.4.0 ", (">=", 0, 4, 0)),
            (">= 0.4.0", (">=", 0, 4, 0)),
            (" 1.2.3 ", (None, 1, 2, 3)),
            ("<= 2.0.0", ("<=", 2, 0, 0)),
        ],
    )
    def test_whitespace_and_spaced_operators(self, pattern, expected):
        assert VersionManager.parse_version(pattern) == expected

    @pytest.mark.parametrize("pattern", ["-1.0.0", "0.-1.0", "1.2.*", "0.*.0", "²2.0.0"])
    def test_negative_or_bad_wildcard_rejected(self, pattern):
        with pytest.raises(ValueError):
            VersionManager.parse_version(pattern)


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

    def test_multiple_entries_with_whitespace_and_operators_pass(self):
        # Multiple compat entries; leading spaces and spaced operators tolerated.
        vm = make_vm("0.5.0")
        vm.check_compatibility([" 0.*", ">= 0.4.0", "<1.0.0"])

    def test_gte_operator_pattern_passes(self):
        vm = make_vm("0.5.0")
        vm.check_compatibility([">=0.4.0"])

    def test_gte_operator_pattern_fails_below(self):
        vm = make_vm("0.3.0")
        with pytest.raises(VersionCompatibilityError):
            vm.check_compatibility([">=0.4.0"])

    def test_wildcard_matches_any_minor_patch_in_major(self):
        # "0.*" is compatible with every 0.y.z release.
        for core in ("0.0.0", "0.4.0", "0.99.99"):
            make_vm(core).check_compatibility(["0.*"])

    @pytest.mark.parametrize("bad", ["abc", ">=x", "1.2.*", "1.2", "-1.0.0", ""])
    def test_malformed_pattern_raises_unprocessable_not_valueerror(self, bad):
        # Malformed compat entries must be a clean 422, never a raw ValueError/500.
        vm = make_vm("0.5.0")
        with pytest.raises(UnprocessableEntityError):
            vm.check_compatibility([bad])

    def test_malformed_pattern_reported_before_incompatibility(self):
        # A garbage pattern alongside a valid-but-incompatible one still reports the
        # malformed entry (as a 422), not the compatibility mismatch.
        vm = make_vm("0.5.0")
        with pytest.raises(UnprocessableEntityError):
            vm.check_compatibility([">=9.0.0", "abc"])


class TestParseSemver:
    @pytest.mark.parametrize("value", ["0.0.0", "1.2.3", "10.20.30", " 0.1.0 "])
    def test_valid_semver(self, value):
        assert VersionManager.parse_semver(value) == tuple(int(p) for p in value.strip().split("."))

    @pytest.mark.parametrize(
        "value",
        # "².0.0" uses a unicode superscript: isdigit() would accept it but int()
        # rejects it — isdecimal() correctly rejects it up front (no 500).
        ["-1.0.0", "0.-1.0", "0.0.-1", "1.2", "1.2.3.4", "a.b.c", "", "1..0", "v1.0.0", "².0.0", 123, None],
    )
    def test_invalid_semver_raises(self, value):
        with pytest.raises(UnprocessableEntityError):
            VersionManager.parse_semver(value)


class TestValidateVersionTransition:
    def make(self):
        return make_vm("0.0.0")

    def test_new_item_valid_version_ok(self):
        self.make().validate_version_transition("0.1.0", None)

    def test_new_item_negative_rejected(self):
        with pytest.raises(UnprocessableEntityError):
            self.make().validate_version_transition("-1.0.0", None)

    @pytest.mark.parametrize("new", ["0.1.0", "0.1.1", "1.0.0", "0.2.0", "5.0.0"])
    def test_increase_or_equal_allowed(self, new):
        # equal (0.1.0) and any increase over 0.1.0 pass the baseline transition check
        self.make().validate_version_transition(new, "0.1.0")

    @pytest.mark.parametrize("old,new", [("0.2.0", "0.1.0"), ("1.0.0", "0.9.9"), ("0.0.2", "0.0.1")])
    def test_decrease_rejected(self, old, new):
        with pytest.raises(UnprocessableEntityError):
            self.make().validate_version_transition(new, old)

    def test_malformed_existing_does_not_block(self):
        # legacy/garbage existing version should not prevent setting a valid one
        self.make().validate_version_transition("0.1.0", "garbage")
