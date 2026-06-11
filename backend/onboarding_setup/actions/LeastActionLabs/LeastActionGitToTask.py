# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
bashblock = {"script.sh": ""}
codeblock = {"main.py": '''import os
import re
import json
import copy
import requests
import tempfile
import shutil
from pathlib import Path
from git import Repo
from src.common.logger.logger import log_info, log_error


FOLDER_TYPES = {
    "action", "asset", "workflow", "operator",
    "payload", "connection", "bootstrap", "config"
}
ITEM_TYPES = {"connection", "payload", "config"}

# Files that carry their own task definition inside a comment block
COMMENT_STYLE_EXTS = (".py", ".sql", ".yaml")

# Suffix for standalone JSON task definition files
LEASTACTION_SUFFIX = ".leastaction.json"


# ---------------------------------------------------------------------------
# Catalog search helpers
# ---------------------------------------------------------------------------

def search_catalog_item(item_type, name, user_access_token):
    backend_host = os.getenv("BACKEND_HOST", "backend")
    api_url = f"http://{backend_host}:8000/api/v1/catalog/search"
    headers = {
        "Cookie": f"frontend_token={user_access_token}",
        "Content-Type": "application/json"
    }
    body = {
        "item_filter": {"item_type": item_type, "name": name},
        "pagination": {},
        "projection": {"include": ["name", "laui"]},
    }
    response = requests.post(api_url, json=body, headers=headers, timeout=30)
    if response.status_code not in (200, 201):
        raise Exception(f"Search failed for {item_type} \'{name}\': {response.status_code} {response.text}")
    items = response.json().get("items", [])
    if not items:
        raise Exception(f"No item found for type=\'{item_type}\' name=\'{name}\'")
    return items[0]["laui"]


def search_item_by_pk(item_type, name, parent_laui, user_access_token):
    backend_host = os.getenv("BACKEND_HOST", "backend")
    api_url = f"http://{backend_host}:8000/api/v1/catalog/search"
    headers = {
        "Cookie": f"frontend_token={user_access_token}",
        "Content-Type": "application/json"
    }
    body = {
        "item_filter": {
            "item_type": item_type,
            "name": name,
            "parent_laui": parent_laui,
        },
        "pagination": {},
        "projection": {"include": ["name", "laui"]},
    }
    try:
        response = requests.post(api_url, json=body, headers=headers, timeout=30)
        if response.status_code in (200, 201):
            items = response.json().get("items", [])
            if items:
                return items[0]["laui"]
    except Exception as e:
        log_error("action", "search_item_by_pk", "error",
                  f"PK search failed for {item_type} \'{name}\': {str(e)}")
    return None


def task_exists(task_name, project_laui, account_laui, partition, user_access_token):
    backend_host = os.getenv("BACKEND_HOST", "backend")
    api_url = f"http://{backend_host}:8000/api/v1/catalog/search"
    headers = {
        "Cookie": f"frontend_token={user_access_token}",
        "Content-Type": "application/json"
    }
    body = {
        "item_filter": {
            "item_type": "task",
            "name": task_name,
            "project_laui": project_laui,
            "account_laui": account_laui,
            "partition": partition,
            "get_by_pk": True,
        },
        "pagination": {},
        "projection": {"include": ["name", "laui"]},
    }
    try:
        response = requests.post(api_url, json=body, headers=headers, timeout=30)
        if response.status_code in (200, 201):
            items = response.json().get("items", [])
            if items:
                return items[0]["laui"]
    except Exception as e:
        log_error("action", "task_exists", "check_failed",
                  f"Could not check existence of task \'{task_name}\': {str(e)}")
    return None


# ---------------------------------------------------------------------------
# Catalog create helper
# ---------------------------------------------------------------------------

def create_catalog_item(body, headers):
    backend_host = os.getenv("BACKEND_HOST", "backend")
    api_url = f"http://{backend_host}:8000/api/v1/catalog/create"
    try:
        response = requests.post(api_url, json=body, headers=headers, timeout=30)
        if response.status_code in (200, 201):
            data = response.json()
            laui = (data.get("item_laui") or data.get("laui") or
                    data.get("id") or data.get("_id") or
                    data.get("item_id") or (data.get("item") or {}).get("laui"))
            if not laui:
                log_error("action", "create_catalog_item", "laui_missing",
                          f"Item created but could not extract laui. Response keys: {list(data.keys())} | body: {str(data)[:300]}")
            return True, laui
        return False, f"{response.status_code}: {response.text}"
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# File classification helpers
# ---------------------------------------------------------------------------

def get_folder_type(dir_name):
    parts = dir_name.rsplit(".", 1)
    if len(parts) == 2:
        prefix, ext = parts[0], parts[1].lower()
        if ext in FOLDER_TYPES:
            return prefix, f"folder.{ext}"
    return None


def get_item_extension(file_name):
    parts = file_name.rsplit(".", 1)
    if len(parts) == 2:
        ext = parts[1].lower()
        if ext in ITEM_TYPES:
            return ext
    return None


def is_comment_style_file(file_name):
    """
    .py / .sql / .yaml — task definition lives inside the file itself
    as a comment block. The same file is also the payload.
    """
    name_lower = file_name.lower()
    return any(name_lower.endswith(ext) for ext in COMMENT_STYLE_EXTS)


def is_leastaction_def_file(file_name):
    """
    abc.json.leastaction.json — pure JSON task definition.
    The corresponding payload file is abc.json (strip LEASTACTION_SUFFIX).
    """
    return file_name.lower().endswith(LEASTACTION_SUFFIX)


def stem_from_leastaction(file_name):
    """
    abc.json.leastaction.json  →  abc
    Strips LEASTACTION_SUFFIX, then strips any remaining extension.
    """
    base = file_name[: -len(LEASTACTION_SUFFIX)]   # → abc.json
    return Path(base).stem                          # → abc


# ---------------------------------------------------------------------------
# File collector
# ---------------------------------------------------------------------------

def collect_task_files(target_path):
    """
    Returns a list of dicts: {"meta_file": Path, "payload_file": Path | None}

    Rules
    -----
    Comment-style files (.py / .sql / .yaml)
        meta_file   = the file itself  (definition is inside the comment block)
        payload_file = the file itself  (everything after the comment block)

    JSON payload files (.json, excluding .leastaction.json)
        The .json file is ONLY a payload — it has no definition inside it.
        Look for  <name>.json.leastaction.json  in the same directory.
        If found  → meta_file = .leastaction.json, payload_file = .json
        If missing → skip with a warning (no definition to work with)

    .leastaction.json files encountered during a directory walk
        Already handled as the meta_file of a .json pair above — skip them
        here to avoid double-processing.

    Single-file path variants
        Passing a .json file directly works the same as above.
        Passing a .leastaction.json directly is also supported
        (payload_file will be set to the corresponding .json if it exists,
         otherwise None — task will be created without a payload).
    """

    # ── Single file ──────────────────────────────────────────────────────────
    if target_path.is_file():
        name = target_path.name

        # Comment-style: definition + payload in same file
        if is_comment_style_file(name):
            log_info("action", "collect_task_files", "single_file",
                     f"Comment-style file: {name}")
            return [{"meta_file": target_path, "payload_file": target_path}]

        # Caller passed the .leastaction.json directly
        if is_leastaction_def_file(name):
            payload_path = target_path.parent / name[: -len(LEASTACTION_SUFFIX)]
            if not payload_path.exists():
                log_info("action", "collect_task_files", "no_payload",
                         f"{name}: companion payload file not found, task will have no payload")
                payload_path = None
            return [{"meta_file": target_path, "payload_file": payload_path}]

        # Caller passed a plain .json payload file → find its .leastaction.json
        companion = target_path.parent / (name + LEASTACTION_SUFFIX)
        if companion.exists():
            log_info("action", "collect_task_files", "companion_resolved",
                     f"{name} → definition from {companion.name}")
            return [{"meta_file": companion, "payload_file": target_path}]

        log_error("action", "collect_task_files", "no_definition",
                  f"No task definition found for \'{name}\'. "
                  f"Expected companion \'{companion.name}\' in the same directory.")
        return []

    # ── Directory walk ────────────────────────────────────────────────────────
    found = []
    for root, _, files in os.walk(target_path):
        root_path = Path(root)
        file_set = set(files)

        for file_name in files:
            file_path = root_path / file_name

            # Comment-style: self-contained
            if is_comment_style_file(file_name):
                found.append({"meta_file": file_path, "payload_file": file_path})
                continue

            # .leastaction.json files are picked up via the .json branch below
            if is_leastaction_def_file(file_name):
                continue

            # Plain .json — look for companion definition
            if file_name.lower().endswith(".json"):
                companion_name = file_name + LEASTACTION_SUFFIX
                if companion_name in file_set:
                    found.append({
                        "meta_file": root_path / companion_name,
                        "payload_file": file_path,
                    })
                else:
                    log_info("action", "collect_task_files", "skipped_json",
                             f"Skipping \'{file_name}\': no companion \'{companion_name}\' found")

    return found


# ---------------------------------------------------------------------------
# Task file parser
# ---------------------------------------------------------------------------

def parse_task_file(meta_file, payload_file):
    """
    Reads task definition metadata from meta_file and payload content from
    payload_file.

    meta_file formats supported:
      1. /* JSON */ comment block  — SQL / JS style (non-greedy, stops at first */)
      2. Triple-quoted docstring   — Python style
      3. Leading # comment block  — Python / YAML style
      4. Pure JSON                 — .leastaction.json (entire file is the definition)

    For cases 1-3 the payload is extracted from the same file (everything
    after the comment block).  For case 4 the payload is read from
    payload_file (the companion .json file).

    Returns (meta_dict, payload_string) or (None, None) on failure.
    meta_dict is always a deep copy — mutations in the loop never bleed across
    files.
    """
    try:
        content = meta_file.read_text(encoding="utf-8")

        # 1. /* ... */ block — NON-GREEDY: stops at first */
        match = re.search(r"/\\*(.*?)\\*/", content, re.DOTALL)
        if match:
            meta = json.loads(match.group(1).strip())
            payload = content[match.end():].strip()
            return copy.deepcopy(meta), payload

        # 2. Triple-quoted docstring (""" or \'\'\')
        for quote in (chr(34) * 3, chr(39) * 3):
            start_idx = content.find(quote)
            if start_idx != -1:
                end_idx = content.find(quote, start_idx + 3)
                if end_idx != -1:
                    block = content[start_idx + 3:end_idx].strip()
                    js = block.find("{")
                    je = block.rfind("}")
                    if js != -1 and je > js:
                        try:
                            meta = json.loads(block[js:je + 1])
                            payload = content[end_idx + 3:].strip()
                            return copy.deepcopy(meta), payload
                        except json.JSONDecodeError:
                            pass

        # 3. Leading # comment block (Python / YAML)
        lines = content.splitlines()
        comment_lines, i = [], 0
        while i < len(lines) and lines[i].lstrip().startswith("#"):
            comment_lines.append(lines[i].lstrip()[1:].strip())
            i += 1
        joined = "\\n".join(comment_lines)
        js = joined.find("{")
        je = joined.rfind("}")
        if js != -1 and je > js:
            try:
                meta = json.loads(joined[js:je + 1])
                payload = "\\n".join(lines[i:]).strip()
                return copy.deepcopy(meta), payload
            except json.JSONDecodeError:
                pass

        # 4. Pure JSON definition (.leastaction.json)
        #    Payload comes from the companion payload_file
        try:
            meta = json.loads(content)
            payload = ""
            if payload_file and payload_file != meta_file and payload_file.exists():
                payload = payload_file.read_text(encoding="utf-8")
            return copy.deepcopy(meta), payload
        except json.JSONDecodeError:
            pass

        log_error("action", "parse_task_file", "no_metadata",
                  f"No JSON metadata found in {meta_file.name}")
        return None, None

    except Exception as e:
        log_error("action", "parse_task_file", "parse_failed",
                  f"Could not parse {meta_file.name}: {str(e)}")
        return None, None


# ---------------------------------------------------------------------------
# Task name helper
# ---------------------------------------------------------------------------

def derive_task_name(meta, meta_file):
    """
    Priority:
      1. name field inside the metadata JSON
      2. Stem of the meta_file, with .leastaction suffix stripped cleanly

    Examples
      meta_file = abc.json.leastaction.json  →  abc
      meta_file = src_insert.sql             →  src_insert
    """
    if meta.get("name"):
        return meta["name"]
    if is_leastaction_def_file(meta_file.name):
        return stem_from_leastaction(meta_file.name)
    return meta_file.stem


# ---------------------------------------------------------------------------
# Action list builder — module-level, no closure, fully isolated per call
# ---------------------------------------------------------------------------

def build_action_list(action_list, task_name, failed_items, user_access_token):
    """
    Resolves action_name strings to lauis.
    Defined at module level — no loop-variable capture.
    action_variables is deep-copied per entry.
    Returns list on success, None on any failure.
    """
    built = []
    for action_item in action_list:
        if not isinstance(action_item, dict):
            failed_items.append({"name": task_name, "reason": "Invalid action format"})
            return None

        action_name = action_item.get("action_name")
        if not action_name:
            failed_items.append({"name": task_name, "reason": "Missing action_name"})
            return None

        try:
            action_laui = search_catalog_item("action", action_name, user_access_token)
        except Exception as e:
            failed_items.append({
                "name": task_name,
                "reason": f"Action \'{action_name}\' not found: {str(e)}"
            })
            return None

        action_variables = action_item.get("action_variables", {})
        if not isinstance(action_variables, dict):
            failed_items.append({"name": task_name, "reason": "action_variables must be object"})
            return None

        built.append({
            "laui": action_laui,
            "action_variables": copy.deepcopy(action_variables)
        })
    return built


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------

def run(
    least_action_action_object,
    git_repo_url,
    git_branch,
    folder_path,
    project_laui,
    account_laui,
    partition=None,
    start_date=None,
    end_date=None,
    workflow_folder_laui=None,
    **kwargs,
):
    temp_dir = None
    failed_items = []

    try:
        log_info("action", "run", "start", "Starting Git catalog sync process")

        user_access_token = least_action_action_object.get("user_access_token")
        if not user_access_token:
            log_error("action", "run", "missing_token", "Missing user_access_token")
            return False

        git_creds = least_action_action_object.get("connection", {})
        git_username = git_creds.get("git_username")
        git_token = git_creds.get("git_token")

        api_headers = {
            "Cookie": f"frontend_token={user_access_token}",
            "Content-Type": "application/json"
        }

        # Clone repo
        temp_dir = tempfile.mkdtemp()
        if git_username and git_token:
            auth_url = git_repo_url.replace(
                "https://", f"https://{git_username}:{git_token}@"
            )
            Repo.clone_from(auth_url, temp_dir, branch=git_branch)
        else:
            Repo.clone_from(git_repo_url, temp_dir, branch=git_branch)

        target_path = Path(temp_dir) / folder_path
        if not target_path.exists():
            log_error("action", "run", "path_not_found",
                      f"Path not found in repo: {folder_path}")
            return False

        # Collect task files — handles single file and directory transparently
        task_files = collect_task_files(target_path)

        if not task_files:
            log_error("action", "run", "no_task_files",
                      f"No supported task files found at: {folder_path}")
            return False

        log_info(
            "action", "run", "collected_files",
            f"Found {len(task_files)} task file(s) under \'{folder_path}\': "
            + ", ".join(t["meta_file"].name for t in task_files)
        )

        if not workflow_folder_laui:
            log_error("action", "run", "workflow_folder_missing",
                      "workflow_folder_laui is required and was not provided")
            return False

        successful_tasks = 0

        # ------------------------------------------------------------------
        # TASK CREATION — each file pair is fully isolated
        # ------------------------------------------------------------------
        for task_info in task_files:

            meta_file    = task_info["meta_file"]
            payload_file = task_info["payload_file"]

            # parse_task_file always deep-copies meta — no cross-iteration bleed
            meta, payload_content = parse_task_file(meta_file, payload_file)

            if not meta:
                failed_items.append({
                    "name": meta_file.name,
                    "reason": "Invalid or missing JSON metadata"
                })
                log_error("action", "run", "invalid_metadata",
                          f"Skipping {meta_file.name}: invalid or missing JSON metadata")
                continue

            task_name = derive_task_name(meta, meta_file)

            log_info("action", "run", "processing_file",
                     f"Processing \'{meta_file.name}\' → task=\'{task_name}\'")

            # Partition: explicit arg > metadata > "ALL"
            resolved_partition = (
                partition if partition
                else (meta.get("partition") or "ALL")
            )

            resolved_start_date = start_date if start_date else meta.get("start_date")
            resolved_end_date   = end_date   if end_date   else meta.get("end_date")

            over_ride = meta.get("over_ride", False)

            if not over_ride:
                existing = task_exists(
                    task_name, project_laui, account_laui,
                    resolved_partition, user_access_token
                )
                if existing:
                    log_info(
                        "action", "run", "task_exists",
                        f"Task \'{task_name}\' already exists "
                        f"(project={project_laui}, account={account_laui}, "
                        f"partition=\'{resolved_partition}\') → skipping. "
                        f"If it is in Trash, restore or permanently delete it before re-importing."
                    )
                    successful_tasks += 1
                    continue

            # Resolve operator
            try:
                operator_laui = search_catalog_item(
                    "operator", meta.get("operator_name"), user_access_token
                )
            except Exception as e:
                msg = f"Operator resolve failed for task \'{task_name}\': {str(e)}"
                failed_items.append({"name": task_name, "reason": msg})
                log_error("action", "run", "operator_resolve_failed", msg)
                continue

            # Resolve connection
            try:
                connection_laui = search_catalog_item(
                    "connection", meta.get("connection_name"), user_access_token
                )
            except Exception as e:
                msg = f"Connection resolve failed for task \'{task_name}\': {str(e)}"
                failed_items.append({"name": task_name, "reason": msg})
                log_error("action", "run", "connection_resolve_failed", msg)
                continue

            # Resolve configs
            attached_config_lauis = []
            config_names = meta.get("config_name", [])
            if isinstance(config_names, str):
                config_names = [config_names]

            config_resolve_failed = False
            for cfg in config_names:
                try:
                    cfg_laui = search_catalog_item("config", cfg, user_access_token)
                    attached_config_lauis.append(cfg_laui)
                except Exception as e:
                    msg = f"Config \'{cfg}\' resolve failed for task \'{task_name}\': {str(e)}"
                    failed_items.append({"name": task_name, "reason": msg})
                    log_error("action", "run", "config_resolve_failed", msg)
                    config_resolve_failed = True
                    break

            if config_resolve_failed:
                continue

            # Actions — build_action_list is module-level, no closure
            actions_meta = meta.get("actions", {})

            pre_actions = build_action_list(
                actions_meta.get("pre_actions", []),
                task_name, failed_items, user_access_token
            )
            running_actions = build_action_list(
                actions_meta.get("running_actions", []),
                task_name, failed_items, user_access_token
            )
            post_actions = build_action_list(
                actions_meta.get("post_actions", []),
                task_name, failed_items, user_access_token
            )

            if None in (pre_actions, running_actions, post_actions):
                log_error("action", "run", "actions_build_failed",
                          f"Skipping task \'{task_name}\' due to invalid actions configuration")
                continue

            # Build task body
            task_body = {
                "item_type": "task",
                "name": task_name,
                "project_laui": project_laui,
                "account_laui": account_laui,
                "parent_laui": workflow_folder_laui,
                "operator_laui": operator_laui,
                "connection_laui": connection_laui,
                "attached_config_lauis": attached_config_lauis,
                "frequency": meta.get("frequency", "*/3 * * * *"),
                "partition": resolved_partition,
            }

            if payload_content:
                task_body["payload"] = payload_content

            # Dates only for non-adhoc tasks
            if str(task_body.get("frequency", "")).lower() != "adhoc":
                if resolved_start_date:
                    task_body["start_date"] = resolved_start_date
                if resolved_end_date:
                    task_body["end_date"] = resolved_end_date

            if pre_actions or running_actions or post_actions:
                task_body["actions"] = {
                    "create_actions": [],
                    "pre_actions": pre_actions,
                    "running_actions": running_actions,
                    "post_actions": post_actions,
                }

            log_info(
                "action", "run", "creating_task",
                f"Creating task \'{task_name}\' | frequency=\'{task_body[\'frequency\']}\' "
                f"| start=\'{task_body.get(\'start_date\')}\' end=\'{task_body.get(\'end_date\')}\' "
                f"| partition=\'{task_body[\'partition\']}\' "
                f"| pre={len(pre_actions)} running={len(running_actions)} post={len(post_actions)}"
            )

            success, result = create_catalog_item(task_body, api_headers)

            if success:
                successful_tasks += 1
            else:
                failed_items.append({"name": task_name, "reason": result})
                log_error("action", "run", "task_create_failed",
                          f"Failed to create task \'{task_name}\': {result}")

        log_info(
            "action", "run", "summary",
            f"GitToTask completed. total_files={len(task_files)}, "
            f"successful_tasks={successful_tasks}, failed_items={len(failed_items)}"
        )

        return len(failed_items) == 0

    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
'''}

action_variables = {
    "git_repo_url": "https://github.com/abc.git",
    "git_branch": "main",
    "folder_path": "",
    "project_laui": "",
    "account_laui": "",
    "partition": "",
    "start_date": "",
    "end_date": "",
    "workflow_folder_laui": ""
}

connection = {
    "git_username": "la",
    "git_token": "git_pat"
}

prompt = (
    "Clone a Git repository and sync Python task files from a folder to LeastAction catalog tasks. "
    "Action variables: git_repo_url, git_branch (default main), folder_path (subfolder to scan), "
    "project_laui, account_laui, partition, start_date, end_date, workflow_folder_laui. "
    "Connection: git_username + git_token (GitHub PAT). "
    "Discovers .py task files in folder_path, creates or updates catalog task items under workflow_folder_laui. "
    "Returns True if all tasks were synced successfully."
)

install_docs = """# LeastActionGitToTask — Install Guide

## Dependencies

No extra packages — uses GitPython or subprocess for cloning and the LeastAction catalog API.
Connection requires a GitHub Personal Access Token with repo read access.

## Git Access

    connection = {
        "git_username": "your_github_username",
        "git_token": "ghp_xxxxxxxxxxxx"
    }
"""

guide_docs = """# LeastActionGitToTask — Action Guide

## What it does

Clones a Git repository, scans a specified folder for Python task definition files,
and syncs them to the LeastAction catalog as task items under a workflow folder.

Useful for GitOps-style workflows where task definitions live in source control and
are automatically deployed to LeastAction on merge/push.

---

## Action Variables

    {
      "git_repo_url": "https://github.com/org/repo.git",
      "git_branch": "main",
      "folder_path": "tasks/",
      "project_laui": "proj_laui",
      "account_laui": "acct_laui",
      "partition": "2026-01-01",
      "workflow_folder_laui": "folder_laui"
    }

---

## Connection

    {"git_username": "your_username", "git_token": "ghp_xxxx"}

---

## Returns

True if all files were synced. False on any failure.
"""

description = """
Clones a Git repository and syncs Python task definition files to LeastAction catalog tasks
under a workflow folder. Enables GitOps-style deployment of task definitions from source control.
Requires a GitHub PAT in the connection.
"""

publisher = "LeastAction"

metadata = {
    "service": "LeastAction, GitHub",
    "category": "DevOps",
    "tags": ["git", "gitops", "sync", "task", "deploy", "workflow", "github"],
    "airflow_equivalent": "PythonOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

