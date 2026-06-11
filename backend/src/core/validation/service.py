# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from __future__ import annotations

import ast
import importlib.metadata
import os
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path

from bandit.core import config as b_config
from bandit.core import manager as b_manager
from fastapi import Request

from src.core.validation.config import ValidationPreset, load_validation_preset
from src.core.validation.schema import (
    CodeblockValidationEntry,
    ValidationResult,
)

ALLOWED_LOGGER_MODULE = "src.common.logger.logger"
ALLOWED_LOG_METHODS = {"log_info", "log_error", "log_warning", "log_critical", "log_debug"}

TAINTED_ROOT_NAMES = {"least_action_task_object", "least_action_action_object"}

OPERATOR_FUNCS: dict[str, int] = {
    "initialize": 1,
    "run": 2,
    "check_completion": 3,
    "finish": 4,
}

ACTION_FUNC_NAME = "run"


class CodeblockValidator:
    def __init__(self) -> None:
        self._preset = load_validation_preset()
        self._installed_packages = self._load_installed_packages()
        self._stdlib_names = set(sys.stdlib_module_names)
        self._module_to_dist = importlib.metadata.packages_distributions()

    @staticmethod
    def _load_installed_packages() -> set[str]:
        names: set[str] = set()
        for dist in importlib.metadata.distributions():
            name = dist.metadata.get("Name", None)
            if name:
                names.add(name.lower().replace("_", "-"))
        return names

    def validate(self, codeblock: dict[str, str], item_type: str) -> ValidationResult:
        preset = self._preset
        base_type = (item_type or "").split(".")[0]
        errors: list[CodeblockValidationEntry] = []
        warnings: list[CodeblockValidationEntry] = []

        if not codeblock or not isinstance(codeblock, dict):
            errors.append(
                CodeblockValidationEntry(
                    code="NO_MAIN_FILE",
                    message="Codeblock is empty or malformed; expected dict[filename, code]",
                )
            )
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        if "main.py" not in codeblock:
            errors.append(
                CodeblockValidationEntry(
                    code="NO_MAIN_FILE", message="Main file must be named 'main.py'"
                )
            )
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        trees: dict[str, ast.AST] = {}
        for fname, code in codeblock.items():
            if not isinstance(code, str):
                errors.append(
                    CodeblockValidationEntry(
                        code="SYNTAX_ERROR",
                        message=f"File '{fname}' content must be a string",
                        file=fname,
                    )
                )
                continue
            syn_err = self._check_syntax(fname, code)
            if syn_err:
                errors.append(syn_err)
                continue
            trees[fname] = ast.parse(code)

        valid_code = {f: codeblock[f] for f in trees}
        security_errors, security_warnings = self._run_security_scan(valid_code, preset)
        errors += security_errors
        warnings += security_warnings

        for fname, tree in trees.items():
            errors += self._check_dangerous(fname, tree, preset)
            errors += self._check_imports(fname, tree, codeblock, preset)
            if preset.checks.logger_check:
                errors += self._check_logger(fname, tree)
            if preset.checks.async_blocked:
                errors += self._check_async(fname, tree)
            if preset.checks.dunder_blocked:
                errors += self._check_dunder(fname, tree)

        if preset.checks.cyclic_import_check:
            errors += self._check_cyclic_imports(codeblock, trees)

        for fname, tree in trees.items():
            warnings += self._check_secret_leak(fname, tree, base_type)

        if "main.py" in trees:
            errors += self._check_interface(trees["main.py"], base_type)
            errors += self._check_return_types(trees["main.py"], base_type)

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    # ── Security scan ───────────────────────────────────────────────────

    @staticmethod
    def _run_security_scan(
        codeblock: dict[str, str], preset: ValidationPreset
    ) -> tuple[list[CodeblockValidationEntry], list[CodeblockValidationEntry]]:
        errors: list[CodeblockValidationEntry] = []
        warnings: list[CodeblockValidationEntry] = []
        all_rules = {**preset.block_rules, **preset.warning_rules}
        if not codeblock or not all_rules:
            return errors, warnings

        security_profile: dict[str, list[str]] = {"include": list(all_rules.keys())}

        with tempfile.TemporaryDirectory() as tmpdir:
            paths: list[str] = []
            path_map: dict[str, str] = {}
            for fname, code in codeblock.items():
                fpath = os.path.join(tmpdir, fname)
                os.makedirs(os.path.dirname(fpath), exist_ok=True)
                with open(fpath, "w") as f:
                    f.write(code)
                paths.append(fpath)
                path_map[fpath] = fname

            conf = b_config.BanditConfig()
            mgr = b_manager.BanditManager(
                conf, agg_type="file", quiet=True, profile=security_profile
            )
            mgr.discover_files(paths)
            mgr.run_tests()

            for issue in mgr.get_issue_list():
                orig = path_map.get(issue.fname, os.path.basename(issue.fname))
                is_warn = issue.test_id in preset.warning_rules
                rule = (
                    preset.warning_rules.get(issue.test_id)
                    if is_warn
                    else preset.block_rules.get(issue.test_id)
                )
                platform_code = rule[1] if rule and len(rule) > 1 else "DANGEROUS_PATTERN"
                entry = CodeblockValidationEntry(
                    code=platform_code, message=issue.text, file=orig, line=issue.lineno
                )
                if is_warn:
                    warnings.append(entry)
                else:
                    errors.append(entry)

        return errors, warnings

    # ── Syntax ──────────────────────────────────────────────────────────

    @staticmethod
    def _check_syntax(fname: str, code: str) -> CodeblockValidationEntry | None:
        try:
            compile(code, fname, "exec")
            return None
        except SyntaxError as e:
            return CodeblockValidationEntry(
                code="SYNTAX_ERROR", message=f"{e.msg}", file=fname, line=e.lineno
            )

    # ── Dangerous calls / patterns ──────────────────────────────────────

    def _check_dangerous(
        self, fname: str, tree: ast.AST, preset: ValidationPreset
    ) -> list[CodeblockValidationEntry]:
        errors: list[CodeblockValidationEntry] = []
        attr_call_rules = [(r[0], r[1], r[2]) for r in preset.attr_call_rules if len(r) >= 3]
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                errors += self._check_call_dangerous(fname, node, attr_call_rules)
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if (
                        isinstance(tgt, ast.Subscript)
                        and self._full_attr_chain(tgt.value) == "sys.modules"
                    ):
                        errors.append(
                            CodeblockValidationEntry(
                                code="DANGEROUS_PATTERN",
                                message="sys.modules manipulation is not allowed",
                                file=fname,
                                line=node.lineno,
                            )
                        )
        return errors

    def _check_call_dangerous(
        self, fname: str, node: ast.Call, attr_call_rules: list[tuple[str, str, str]]
    ) -> list[CodeblockValidationEntry]:
        errors: list[CodeblockValidationEntry] = []
        func = node.func

        if isinstance(func, ast.Name):
            if func.id == "open":
                errors += self._check_open_call(fname, node)
            return errors

        if isinstance(func, ast.Attribute):
            chain = self._full_attr_chain(func)
            if not chain:
                return errors
            head = chain.split(".")[0]

            for match_type, pattern, msg_tpl in attr_call_rules:
                matched = (
                    (match_type == "head" and head == pattern)
                    or (match_type == "exact" and chain == pattern)
                    or (match_type == "prefix" and chain.startswith(pattern))
                )
                if matched:
                    errors.append(
                        CodeblockValidationEntry(
                            code="DANGEROUS_PATTERN",
                            message=msg_tpl.format(chain=chain),
                            file=fname,
                            line=node.lineno,
                        )
                    )
                    return errors

        return errors

    def _check_open_call(self, fname: str, node: ast.Call) -> list[CodeblockValidationEntry]:
        errors: list[CodeblockValidationEntry] = []
        if not node.args:
            return errors
        path_arg = node.args[0]
        mode_arg = node.args[1] if len(node.args) > 1 else None
        if mode_arg is None:
            for kw in node.keywords:
                if kw.arg == "mode":
                    mode_arg = kw.value
                    break
        mode_val: str | None = None
        if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
            mode_val = mode_arg.value
        is_write = mode_val is not None and any(c in mode_val for c in ("w", "a", "x", "+"))
        if not is_write:
            return errors
        if isinstance(path_arg, ast.Constant) and isinstance(path_arg.value, str):
            if path_arg.value.startswith(("/", "~")):
                errors.append(
                    CodeblockValidationEntry(
                        code="DANGEROUS_PATTERN",
                        message=f"open() write to absolute/home path '{path_arg.value}' is not allowed",
                        file=fname,
                        line=node.lineno,
                    )
                )
        return errors

    # ── Imports ─────────────────────────────────────────────────────────

    def _check_imports(
        self, fname: str, tree: ast.AST, codeblock: dict[str, str], preset: ValidationPreset
    ) -> list[CodeblockValidationEntry]:
        errors: list[CodeblockValidationEntry] = []
        local_stems = {Path(f).stem for f in codeblock}
        deny_imports = set(preset.deny_imports)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    errors += self._classify_import(
                        fname, node.lineno, top, local_stems, deny_imports
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    errors.append(
                        CodeblockValidationEntry(
                            code="RELATIVE_IMPORT",
                            message="Relative imports are not allowed (use absolute imports like `from helpers import foo`)",
                            file=fname,
                            line=node.lineno,
                        )
                    )
                    continue
                if node.module:
                    top = node.module.split(".")[0]
                    errors += self._classify_import(
                        fname, node.lineno, top, local_stems, deny_imports
                    )
        return errors

    def _classify_import(
        self,
        fname: str,
        lineno: int,
        top: str,
        local_stems: set[str],
        deny_imports: set[str],
    ) -> list[CodeblockValidationEntry]:
        errors: list[CodeblockValidationEntry] = []
        if not top:
            return errors
        if top in local_stems:
            return errors
        if top in deny_imports:
            errors.append(
                CodeblockValidationEntry(
                    code="DENIED_IMPORT",
                    message=f"Import of '{top}' is not allowed",
                    file=fname,
                    line=lineno,
                )
            )
            return errors
        if top in self._stdlib_names:
            return errors
        if top == "src":
            return errors
        dists = self._module_to_dist.get(top)
        if not dists:
            errors.append(
                CodeblockValidationEntry(
                    code="EXTERNAL_PATH_IMPORT",
                    message=f"Import of '{top}' cannot be resolved to a local file, stdlib, or installed package",
                    file=fname,
                    line=lineno,
                )
            )
            return errors
        normalized = [d.lower().replace("_", "-") for d in dists]
        if not any(d in self._installed_packages for d in normalized):
            errors.append(
                CodeblockValidationEntry(
                    code="PACKAGE_NOT_INSTALLED",
                    message=f"Package '{top}' (dist: {', '.join(dists)}) is not installed on the platform",
                    file=fname,
                    line=lineno,
                )
            )
        return errors

    # ── Logger ──────────────────────────────────────────────────────────

    def _check_logger(self, fname: str, tree: ast.AST) -> list[CodeblockValidationEntry]:
        errors: list[CodeblockValidationEntry] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                chain = self._full_attr_chain(node.func)
                if chain in ("logging.basicConfig", "logging.getLogger"):
                    errors.append(
                        CodeblockValidationEntry(
                            code="ROOT_LOGGER_CONFIG",
                            message=f"{chain}() is not allowed; use src.common.logger.logger",
                            file=fname,
                            line=node.lineno,
                        )
                    )

            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("src.common.logger"):
                    if node.module != ALLOWED_LOGGER_MODULE:
                        errors.append(
                            CodeblockValidationEntry(
                                code="INVALID_LOGGER_IMPORT",
                                message=f"Logger must be imported from '{ALLOWED_LOGGER_MODULE}', not '{node.module}'",
                                file=fname,
                                line=node.lineno,
                            )
                        )
                    else:
                        for alias in node.names:
                            if alias.name not in ALLOWED_LOG_METHODS:
                                errors.append(
                                    CodeblockValidationEntry(
                                        code="INVALID_LOG_METHOD",
                                        message=f"Log method '{alias.name}' is not allowed. Allowed: {sorted(ALLOWED_LOG_METHODS)}",
                                        file=fname,
                                        line=node.lineno,
                                    )
                                )
                elif node.module == "logging":
                    errors.append(
                        CodeblockValidationEntry(
                            code="INVALID_LOGGER_IMPORT",
                            message=f"Logger must be imported from '{ALLOWED_LOGGER_MODULE}', not 'logging'",
                            file=fname,
                            line=node.lineno,
                        )
                    )

            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "logging":
                        errors.append(
                            CodeblockValidationEntry(
                                code="INVALID_LOGGER_IMPORT",
                                message=f"Logger must be imported from '{ALLOWED_LOGGER_MODULE}', not 'logging'",
                                file=fname,
                                line=node.lineno,
                            )
                        )
        return errors

    # ── Async ───────────────────────────────────────────────────────────

    @staticmethod
    def _check_async(fname: str, tree: ast.AST) -> list[CodeblockValidationEntry]:
        errors: list[CodeblockValidationEntry] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                errors.append(
                    CodeblockValidationEntry(
                        code="ASYNC_FUNC",
                        message=f"async functions are not allowed (found 'async def {node.name}')",
                        file=fname,
                        line=node.lineno,
                    )
                )
        return errors

    # ── Dunder ──────────────────────────────────────────────────────────

    @staticmethod
    def _check_dunder(fname: str, tree: ast.AST) -> list[CodeblockValidationEntry]:
        errors: list[CodeblockValidationEntry] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                if node.attr.startswith("__") and node.attr.endswith("__"):
                    errors.append(
                        CodeblockValidationEntry(
                            code="DUNDER_ACCESS",
                            message=f"Access to dunder attribute '{node.attr}' is not allowed",
                            file=fname,
                            line=node.lineno,
                        )
                    )
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id.startswith("__") and node.func.id.endswith("__"):
                    errors.append(
                        CodeblockValidationEntry(
                            code="DUNDER_ACCESS",
                            message=f"Use of dunder function '{node.func.id}()' is not allowed",
                            file=fname,
                            line=node.lineno,
                        )
                    )
        return errors

    # ── Secret leak ─────────────────────────────────────────────────────

    def _check_secret_leak(
        self, fname: str, tree: ast.AST, base_type: str
    ) -> list[CodeblockValidationEntry]:
        errors: list[CodeblockValidationEntry] = []

        tainted: set[str] = set(TAINTED_ROOT_NAMES)
        assigns: list[ast.Assign] = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)]
        changed = True
        while changed:
            changed = False
            for a in assigns:
                rhs_names = {n.id for n in ast.walk(a.value) if isinstance(n, ast.Name)}
                rhs_taints = rhs_names & tainted
                if not rhs_taints:
                    for sub in ast.walk(a.value):
                        if isinstance(sub, ast.Attribute):
                            base = self._attribute_root_name(sub)
                            if base and base in tainted:
                                rhs_taints = {base}
                                break
                if not rhs_taints:
                    continue
                for tgt in a.targets:
                    for name in self._assign_target_names(tgt):
                        if name not in tainted:
                            tainted.add(name)
                            changed = True

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func_name: str | None = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            if func_name not in ({"print"} | ALLOWED_LOG_METHODS):
                continue
            for arg in list(node.args) + [kw.value for kw in node.keywords]:
                if self._expr_references_tainted(arg, tainted):
                    errors.append(
                        CodeblockValidationEntry(
                            code="SECRET_LEAK",
                            message=f"'{func_name}' call may leak sensitive data (references tainted object)",
                            file=fname,
                            line=node.lineno,
                        )
                    )
                    break
        return errors

    def _expr_references_tainted(self, expr: ast.AST, tainted: set[str]) -> bool:
        for sub in ast.walk(expr):
            if isinstance(sub, ast.Name) and sub.id in tainted:
                return True
            if isinstance(sub, ast.Attribute):
                base = self._attribute_root_name(sub)
                if base and base in tainted:
                    return True
            if isinstance(sub, ast.JoinedStr):
                for v in sub.values:
                    if isinstance(v, ast.FormattedValue) and self._expr_references_tainted(
                        v.value, tainted
                    ):
                        return True
        return False

    # ── Cyclic imports ──────────────────────────────────────────────────

    def _check_cyclic_imports(
        self,
        codeblock: dict[str, str],
        trees: dict[str, ast.AST],
    ) -> list[CodeblockValidationEntry]:
        errors: list[CodeblockValidationEntry] = []
        stems_to_file = {Path(f).stem: f for f in codeblock}
        graph: dict[str, list[str]] = {f: [] for f in codeblock}
        for fname, tree in trees.items():
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        if top in stems_to_file:
                            graph[fname].append(stems_to_file[top])
                elif isinstance(node, ast.ImportFrom):
                    if node.level and node.level > 0:
                        continue
                    if node.module:
                        top = node.module.split(".")[0]
                        if top in stems_to_file:
                            graph[fname].append(stems_to_file[top])

        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = dict.fromkeys(graph, WHITE)
        reported: set[tuple[str, str]] = set()

        def dfs(u: str, stack: list[str]) -> None:
            color[u] = GRAY
            stack.append(u)
            for v in graph.get(u, []):
                if color[v] == GRAY:
                    key = tuple(sorted([u, v]))
                    if key not in reported:
                        reported.add(key)
                        errors.append(
                            CodeblockValidationEntry(
                                code="CYCLIC_IMPORT",
                                message=f"Cyclic import detected between '{u}' and '{v}'",
                                file=u,
                            )
                        )
                elif color[v] == WHITE:
                    dfs(v, stack)
            stack.pop()
            color[u] = BLACK

        for node in graph:
            if color[node] == WHITE:
                dfs(node, [])
        return errors

    # ── Interface (main.py) ─────────────────────────────────────────────

    @staticmethod
    def _check_interface(main_tree: ast.AST, base_type: str) -> list[CodeblockValidationEntry]:
        errors: list[CodeblockValidationEntry] = []
        top_funcs: dict[str, ast.FunctionDef] = {}
        for node in main_tree.body if isinstance(main_tree, ast.Module) else []:
            if isinstance(node, ast.FunctionDef):
                top_funcs[node.name] = node

        if base_type == "operator":
            for name, expected_args in OPERATOR_FUNCS.items():
                fn = top_funcs.get(name)
                if not fn:
                    errors.append(
                        CodeblockValidationEntry(
                            code="MISSING_FUNC",
                            message=f"Missing required function: {name}",
                            file="main.py",
                        )
                    )
                    continue
                actual = len(fn.args.args)
                if actual != expected_args:
                    errors.append(
                        CodeblockValidationEntry(
                            code="WRONG_SIGNATURE",
                            message=f"Function '{name}' must accept {expected_args} positional argument(s), found {actual}",
                            file="main.py",
                            line=fn.lineno,
                        )
                    )

        elif base_type == "action":
            fn = top_funcs.get(ACTION_FUNC_NAME)
            if not fn:
                errors.append(
                    CodeblockValidationEntry(
                        code="MISSING_FUNC",
                        message=f"Missing required function: {ACTION_FUNC_NAME}",
                        file="main.py",
                    )
                )
            else:
                if len(fn.args.args) < 1:
                    errors.append(
                        CodeblockValidationEntry(
                            code="WRONG_SIGNATURE",
                            message="Action 'run' must accept at least 1 positional argument (least_action_action_object)",
                            file="main.py",
                            line=fn.lineno,
                        )
                    )

        return errors

    # ── Return types (main.py) ──────────────────────────────────────────

    @staticmethod
    def _check_return_types(main_tree: ast.AST, base_type: str) -> list[CodeblockValidationEntry]:
        errors: list[CodeblockValidationEntry] = []
        top_funcs: dict[str, ast.FunctionDef] = {}
        for node in main_tree.body if isinstance(main_tree, ast.Module) else []:
            if isinstance(node, ast.FunctionDef):
                top_funcs[node.name] = node

        def _literal_returns(fn: ast.FunctionDef) -> list[ast.Return]:
            return [n for n in ast.walk(fn) if isinstance(n, ast.Return)]

        if base_type == "operator":
            init = top_funcs.get("initialize")
            if init:
                for r in _literal_returns(init):
                    if r.value is None or (
                        isinstance(r.value, ast.Constant) and r.value.value is None
                    ):
                        errors.append(
                            CodeblockValidationEntry(
                                code="INVALID_RETURN",
                                message="operator.initialize() must return a non-None value",
                                file="main.py",
                                line=r.lineno,
                            )
                        )

            run_fn = top_funcs.get("run")
            if run_fn:
                for r in _literal_returns(run_fn):
                    v = r.value
                    if v is None:
                        errors.append(
                            CodeblockValidationEntry(
                                code="INVALID_RETURN",
                                message="operator.run() must return a dict with 'status' and 'execution_type'",
                                file="main.py",
                                line=r.lineno,
                            )
                        )
                    elif isinstance(v, ast.Constant) and not isinstance(v.value, dict):
                        if isinstance(v.value, (str, int, float, bool)) or v.value is None:
                            errors.append(
                                CodeblockValidationEntry(
                                    code="INVALID_RETURN",
                                    message="operator.run() must return a dict with 'status' and 'execution_type'",
                                    file="main.py",
                                    line=r.lineno,
                                )
                            )
                    elif isinstance(v, (ast.List, ast.Tuple, ast.Set)):
                        errors.append(
                            CodeblockValidationEntry(
                                code="INVALID_RETURN",
                                message="operator.run() must return a dict with 'status' and 'execution_type'",
                                file="main.py",
                                line=r.lineno,
                            )
                        )
                    elif isinstance(v, ast.Dict):
                        keys = {
                            k.value
                            for k in v.keys
                            if isinstance(k, ast.Constant) and isinstance(k.value, str)
                        }
                        if "status" not in keys or "execution_type" not in keys:
                            errors.append(
                                CodeblockValidationEntry(
                                    code="INVALID_RETURN",
                                    message="operator.run() dict literal must contain keys 'status' and 'execution_type'",
                                    file="main.py",
                                    line=r.lineno,
                                )
                            )

            cc = top_funcs.get("check_completion")
            if cc:
                for r in _literal_returns(cc):
                    v = r.value
                    if v is None or (isinstance(v, ast.Constant) and v.value is None):
                        errors.append(
                            CodeblockValidationEntry(
                                code="INVALID_RETURN",
                                message="operator.check_completion() must return a dict with 'status'",
                                file="main.py",
                                line=r.lineno,
                            )
                        )
                    elif isinstance(v, ast.Dict):
                        keys = {
                            k.value
                            for k in v.keys
                            if isinstance(k, ast.Constant) and isinstance(k.value, str)
                        }
                        if "status" not in keys:
                            errors.append(
                                CodeblockValidationEntry(
                                    code="INVALID_RETURN",
                                    message="operator.check_completion() dict literal must contain key 'status'",
                                    file="main.py",
                                    line=r.lineno,
                                )
                            )

            fin = top_funcs.get("finish")
            if fin:
                for r in _literal_returns(fin):
                    v = r.value
                    if v is not None and not (isinstance(v, ast.Constant) and v.value is None):
                        errors.append(
                            CodeblockValidationEntry(
                                code="INVALID_RETURN",
                                message="operator.finish() must return None",
                                file="main.py",
                                line=r.lineno,
                            )
                        )

        elif base_type == "action":
            run_fn = top_funcs.get("run")
            if run_fn:
                for r in _literal_returns(run_fn):
                    v = r.value
                    if v is None:
                        errors.append(
                            CodeblockValidationEntry(
                                code="INVALID_RETURN",
                                message="action.run() must return a boolean",
                                file="main.py",
                                line=r.lineno,
                            )
                        )
                    elif isinstance(v, ast.Constant):
                        if not isinstance(v.value, bool) and v.value is not None or v.value is None:
                            errors.append(
                                CodeblockValidationEntry(
                                    code="INVALID_RETURN",
                                    message="action.run() must return a boolean",
                                    file="main.py",
                                    line=r.lineno,
                                )
                            )
                    elif isinstance(v, (ast.Dict, ast.List, ast.Set, ast.Tuple)):
                        errors.append(
                            CodeblockValidationEntry(
                                code="INVALID_RETURN",
                                message="action.run() must return a boolean",
                                file="main.py",
                                line=r.lineno,
                            )
                        )

        return errors

    # ── AST helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _full_attr_chain(node: ast.AST) -> str:
        parts: list[str] = []
        cur = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
            return ".".join(reversed(parts))
        return ""

    @staticmethod
    def _attribute_root_name(node: ast.Attribute) -> str | None:
        cur: ast.AST = node
        while isinstance(cur, ast.Attribute):
            cur = cur.value
        if isinstance(cur, ast.Name):
            return cur.id
        return None

    @staticmethod
    def _assign_target_names(tgt: ast.AST) -> Iterable[str]:
        if isinstance(tgt, ast.Name):
            yield tgt.id
        elif isinstance(tgt, (ast.Tuple, ast.List)):
            for elt in tgt.elts:
                yield from CodeblockValidator._assign_target_names(elt)


def get_codeblock_validator(request: Request) -> CodeblockValidator:
    return request.app.state.codeblock_validator
