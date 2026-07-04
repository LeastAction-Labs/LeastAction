# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.

bashblock = {"install_dependencies.sh": "pip install requests"}

codeblock = {
    "main.py": '''
import json
import os
import requests
from src.common.logger.logger import log_error, log_info

BANNER = "=" * 60


def _fetch_item(laui: str, auth_token: str, backend_host: str) -> dict | None:
    try:
        resp = requests.get(
            f"http://{backend_host}:8000/api/v1/catalog/get?item_laui={laui}",
            headers={"Cookie": f"frontend_token={auth_token}", "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log_error("action", "_fetch_item", "error", f"Failed to fetch item {laui}: {str(e)}")
        return None


def _search_item(name: str, auth_token: str, backend_host: str,
                 project_laui: str = None, account_laui: str = None) -> dict | None:
    try:
        item_filter = {"item_type": "skill", "name": name}
        if project_laui:
            item_filter["project_laui"] = project_laui
        if account_laui:
            item_filter["account_laui"] = account_laui
        resp = requests.post(
            f"http://{backend_host}:8000/api/v1/catalog/search",
            json={"item_filter": item_filter, "pagination": {}, "projection": {"include": ["name", "laui", "content", "prompt", "description"]}},
            headers={"Cookie": f"frontend_token={auth_token}", "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return items[0] if items else None
    except Exception as e:
        log_error("action", "_search_item", "error", f"Failed to search for skill '{name}': {str(e)}")
        return None


def _log_section(title: str, content: str) -> None:
    log_info("action", "run", "debug", f"\\n{BANNER}\\n  {title}\\n{BANNER}\\n{content}\\n{BANNER}")


def _dump(obj) -> str:
    if obj is None:
        return "(not found)"
    try:
        return json.dumps(obj, indent=2, default=str)
    except Exception:
        return str(obj)


def run(
    least_action_action_object: dict,
    skill_names: list | None = None,
    task_lauies: list | None = None,
    include_task_context: bool = True,
    **kwargs,
) -> bool:
    """
    Debug action for the dbt sales reporting pipeline.

    Reads one or more skill documents from the catalog and dumps their content to logs,
    then optionally fetches the current task and any extra task lauies for state inspection.

    action_variables:
      skill_names        — list of skill names to look up (e.g. ["DBT_Postgresql_Sales_Pipelines_Skill"])
      task_lauies        — list of extra task lauies to fetch and log (optional)
      include_task_context — if True, also log the current task object from the action object (default True)
    """
    try:
        auth_token = least_action_action_object.get("user_access_token")
        if not auth_token:
            log_error("action", "run", "missing_auth_token", "user_access_token not found")
            return False

        backend_host = os.getenv("BACKEND_HOST", "backend")
        current_task = least_action_action_object.get("task", {})
        project_laui = current_task.get("project_laui") or None
        account_laui = current_task.get("account_laui") or None

        log_info("action", "run", "start",
            f"LeastActionDebug started | "
            f"skill_names={skill_names} | "
            f"task_lauies={task_lauies} | "
            f"include_task_context={include_task_context}"
        )

        # ── 1. Current task context ──────────────────────────────────────────
        if include_task_context:
            task_laui = current_task.get("laui")
            if task_laui:
                fetched = _fetch_item(str(task_laui), auth_token, backend_host)
                _log_section("CURRENT TASK", _dump(fetched or current_task))
            else:
                _log_section("CURRENT TASK (from action object)", _dump(current_task))

        # ── 2. Skill documents ───────────────────────────────────────────────
        if skill_names:
            for skill_name in skill_names:
                skill_item = _search_item(
                    skill_name, auth_token, backend_host, project_laui, account_laui
                )
                if skill_item:
                    content = skill_item.get("content", "(no content field)")
                    _log_section(f"SKILL: {skill_name}", content if isinstance(content, str) else _dump(content))
                    prompt = skill_item.get("prompt", "")
                    if prompt:
                        _log_section(f"SKILL PROMPT: {skill_name}", prompt)
                else:
                    _log_section(f"SKILL: {skill_name}", "(not found in catalog)")
        else:
            log_info("action", "run", "no_skills", "No skill_names provided — skipping skill lookup")

        # ── 3. Extra task lauies ─────────────────────────────────────────────
        if task_lauies:
            for t_laui in task_lauies:
                item = _fetch_item(str(t_laui), auth_token, backend_host)
                label = item.get("name", t_laui) if item else t_laui
                _log_section(f"TASK: {label} ({t_laui})", _dump(item))

        log_info("action", "run", "done", "LeastActionDebug complete")
        return True

    except Exception as e:
        import traceback
        log_error("action", "run", "unexpected_error", f"Unexpected error: {str(e)}\\n{traceback.format_exc()}")
        return False
'''
}

action_variables = {
    "skill_names": [
        "DBT_Postgresql_Sales_Pipelines_Skill",
        "DBT_Postgresql_Sales_Data_Contract",
    ],
    "task_lauies": [],
    "include_task_context": True,
}

connection = {}

prompt = (
    "Debug a dbt sales pipeline run: fetch and log one or more skill documents by name from the "
    "catalog, log the current task state, and optionally fetch extra tasks by LAUI. "
    "action_variables: skill_names (list of skill names to look up), "
    "task_lauies (optional list of task lauies to fetch), "
    "include_task_context (bool, default True — log the current task)."
)

description = (
    "Debug action for the dbt sales reporting pipeline. "
    "Reads named skill documents from the catalog and dumps their content, prompt, and task state "
    "to logs. Attach as a post_action on any failing task to see what skill it was using and what "
    "state the pipeline is in."
)

install_docs = """# LeastActionDebug — Install Guide

## Dependencies

    pip install requests
"""

guide_docs = """# LeastActionDebug — Action Guide

## What it does

Fetches and logs the content of named skill documents plus the current task state.
Attach as a post_action on any dbt sales pipeline task to get full debug output in logs.

---

## action_variables

```json
{
  "skill_names": ["DBT_Postgresql_Sales_Pipelines_Skill", "DBT_Postgresql_Sales_Data_Contract"],
  "task_lauies": [],
  "include_task_context": true
}
```

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `skill_names` | list[str] | `[]` | Names of `ai.skill` items to fetch and log |
| `task_lauies` | list[str] | `[]` | Extra task LAUIs to fetch and log |
| `include_task_context` | bool | `true` | Whether to log the current task state |

---

## Returns

Always `True` (debug-only — does not gate the pipeline).

---

## Typical use

Attach to `01_cube_aggregation` as a post_action to see the pipeline skill when the model fails:

```json
{
  "skill_names": ["DBT_Postgresql_Sales_Pipelines_Skill"],
  "include_task_context": true
}
```
"""

publisher = "LeastAction"

metadata = {
    "service": "dbt",
    "category": "Debug",
    "tags": ["dbt", "debug", "skill", "pipeline", "sales", "inspect", "logs"],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
