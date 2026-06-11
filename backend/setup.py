# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio
import importlib.util
import json
import os
import time
import traceback
from datetime import UTC, datetime, timedelta
from pathlib import Path

import requests
from bson import ObjectId

from src.common.secrets import get_secret
from src.common.utils import generate_password
from src.core.db.service import create_mongo_client
from src.core.db.types import MongoDatabase
from src.core.ee.iam.session.service import SessionService
from src.core.ee.iam.user.repo import UserRepository
from src.core.ee.iam.user.schema import CreateUser, UserType
from src.core.ee.iam.user.service import UserService

ACCESS_TOKEN = None
BACKEND_URL = os.getenv("BACKEND_URL")
ONBOARDING_DIR = Path(__file__).parent / "onboarding_setup"

# AI category types whose subfolders should be folder.ai (not folder.agent etc.)
AI_CATEGORY_TYPES = {"agent", "generate", "skill", "usecase"}

# Maps category folder name → singular item_type name used in the API
CATEGORY_MAP = {
    "operators": "operator",
    "actions": "action",
    "connections": "connection",
    "payloads": "payload",
    "configs": "config",
    "workflows": "workflow",
    "assets": "asset",
    "ai/agent": "agent",
    "ai/generate": "generate",
    "ai/skills": "skill",
    "ai/usecases": "usecase",
}

# Single source of truth for the admins group name
ADMINS_GROUP_NAME = "admins"


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


async def find_item(db, query: dict) -> str | None:
    item = await db["items"].find_one(query)
    return str(item["_id"]) if item else None


def with_parent(parent_laui: str | None) -> dict:
    if parent_laui:
        return {"parent_laui": ObjectId(parent_laui)}
    return {}


# ---------------------------------------------------------------------------
# System user
# ---------------------------------------------------------------------------


async def create_system_user(db_client) -> tuple[str, str]:
    """Get or create system user and return (laui, access_token)."""
    print("[setup] Ensuring system user exists...")

    user_repo = UserRepository(db=db_client.get_db())
    user_service = UserService(user_repo=user_repo)

    private_key = SessionService.load_private_key()
    public_key = SessionService.load_public_key()
    session_service = SessionService(public_key=public_key, private_key=private_key)

    try:
        existing_user = await user_service.get_user_by_email(email="system@leastactionlabs.com")
    except Exception:
        existing_user = None

    if existing_user:
        if existing_user.user_type != UserType.SYSTEM:
            await user_repo.update_user(
                laui=ObjectId(existing_user.laui), update_data={"user_type": UserType.SYSTEM}
            )

        print(f"[setup] System user already exists with LAUI: {existing_user.laui}")
        if hasattr(existing_user, "system_access_token") and existing_user.system_access_token:
            return str(existing_user.laui), existing_user.system_access_token

        # Token missing — generate and persist it
        print("[setup] system_access_token missing, generating one now...")
        long_lived_token = session_service.generate_access_token(
            user=existing_user, expires_in_hours=87600
        )
        await user_repo.db["users"].update_one(
            {"_id": ObjectId(existing_user.laui)},
            {"$set": {"system_access_token": long_lived_token}},
        )
        print("[setup] Stored system_access_token for existing system user")
        return str(existing_user.laui), long_lived_token

    existing_system_user = await user_repo.find_system_user()
    if existing_system_user:
        await user_repo.db["users"].update_one(
            {"_id": ObjectId(existing_user.laui)}, {"$unset": {"user_type": ""}}
        )

    system_user_data = CreateUser(
        email="system@leastactionlabs.com",
        username="System",
        password=generate_password(20),
        user_type=UserType.SYSTEM,
    )

    await user_service.create_user(system_user_data)
    system_user = await user_service.get_user_by_email(email="system@leastactionlabs.com")
    print(f"[setup] Created system user with LAUI: {system_user.laui}")

    long_lived_token = session_service.generate_access_token(
        user=system_user, expires_in_hours=87600
    )

    await user_repo.db["users"].update_one(
        {"_id": ObjectId(system_user.laui)}, {"$set": {"system_access_token": long_lived_token}}
    )
    print("[setup] Stored system_access_token in user document")

    return str(system_user.laui), long_lived_token


# ---------------------------------------------------------------------------
# Root user
# ---------------------------------------------------------------------------


async def create_root_user(db_client) -> str:
    """Get or create the root admin user from env vars. Returns laui."""
    root_email = get_secret("ROOT_EMAIL")
    root_username = get_secret("ROOT_USERNAME")
    root_password = get_secret("ROOT_PASSWORD")

    if not root_email or not root_username or not root_password:
        raise Exception(
            "ROOT_EMAIL, ROOT_USERNAME, and ROOT_PASSWORD must be set to create the root account"
        )

    print(f"[setup] Ensuring root user exists ({root_email})...")

    user_repo = UserRepository(db=db_client.get_db())
    user_service = UserService(user_repo=user_repo)

    try:
        existing = await user_service.get_user_by_email(root_email)
        if existing.username != root_username:
            raise
        if existing:
            if existing.user_type != UserType.ROOT:
                await user_repo.update_user(
                    laui=ObjectId(existing.laui), update_data={"user_type": UserType.ROOT}
                )

            print(f"[setup] Root user already exists with LAUI: {existing.laui}")
            return str(existing.laui)
    except Exception:
        pass

    existing_root_user = await user_repo.find_root_user()
    if existing_root_user:
        await user_repo.db["users"].update_one(
            {"_id": ObjectId(existing_root_user.laui)}, {"$unset": {"user_type": ""}}
        )

    root_user_data = CreateUser(
        email=root_email, username=root_username, password=root_password, user_type=UserType.ROOT
    )
    await user_service.create_user(root_user_data)
    root_user = await user_service.get_user_by_email(root_email)
    print(f"[setup] Created root user '{root_username}' with LAUI: {root_user.laui}")
    return str(root_user.laui)


# ---------------------------------------------------------------------------
# Admins group
# ---------------------------------------------------------------------------


async def create_admins_group(db_client, root_user_laui: str) -> str:
    """Get or create the admins group; ensure only the root user is an owner in Keto."""
    print("[setup] Ensuring admins group exists...")

    active_db = db_client.get_db()

    # Check if group already exists in MongoDB — use ADMINS_GROUP_NAME consistently
    existing = await active_db["groups"].find_one({"name": ADMINS_GROUP_NAME})
    if existing:
        group_laui = str(existing["_id"])
        print(f"[setup] Admins group already exists with LAUI: {group_laui}")
    else:
        # Create via backend API — system user (ACCESS_TOKEN) becomes owner automatically
        resp = requests.post(
            f"{BACKEND_URL}/api/v1/group/create",
            json={"name": ADMINS_GROUP_NAME},
            headers={"Cookie": f"frontend_token={ACCESS_TOKEN}"},
        )
        resp.raise_for_status()
        print(resp.json())
        group_laui = resp.json()
        time.sleep(1)  # allow Keto access writer to sync
        print(f"[setup] Created admins group with LAUI: {group_laui}")
        resp = requests.post(
            f"{BACKEND_URL}/api/v1/group/create",
            json={
                "name": ADMINS_GROUP_NAME,
                "access_patch": {"add": {"owners": {f"U{root_user_laui}": ""}}},
            },
            headers={"Cookie": f"frontend_token={ACCESS_TOKEN}"},
        )
        time.sleep(1)  # allow Keto access writer to sync

    return group_laui


async def grant_owners_group_item_access(active_db: MongoDatabase, owners_group_laui: str) -> None:
    folder_account = await active_db["items"].find_one({"item_type": "folder.account"})

    await create_item(
        {
            "item_type": "folder.account",
            "is_root": True,
            "name": folder_account["name"],
            "access_patch": {"add": {"owners": {f"G{owners_group_laui}": ""}}},
        }
    )


# ---------------------------------------------------------------------------
# API helper
# ---------------------------------------------------------------------------


async def create_item(item_body: dict) -> dict:
    item_response = None
    try:
        item_response = requests.post(
            f"{BACKEND_URL}/api/v1/catalog/create",
            json=item_body,
            headers={"Cookie": f"frontend_token={ACCESS_TOKEN}"},
        )
        item_response.raise_for_status()
        time.sleep(0.1)
        return item_response.json()
    except requests.RequestException as e:
        print(f"Error creating item: {e}")
        print(f"Request payload: {json.dumps(item_body, indent=2, default=str)}")
        if item_response is not None:
            try:
                print(f"Response body: {item_response.text}")
            except Exception:
                pass
        raise


async def delete_item(item_laui: str, parent_laui: str) -> None:
    requests.post(
        f"{BACKEND_URL}/api/v1/catalog/delete",
        json={"item_laui": item_laui, "parent_laui": parent_laui, "hard_delete": True},
        headers={"Cookie": f"frontend_token={ACCESS_TOKEN}"},
    ).raise_for_status()


# ---------------------------------------------------------------------------
# Folder helpers (always create)
# ---------------------------------------------------------------------------


async def get_or_create_account_folder(db) -> str:
    existing = await db["items"].find_one({"item_type": "folder.account"})
    if existing:
        laui = str(existing["_id"])
        print(f"[setup] Account folder already exists with LAUI: {laui}")
        return laui
    payload = {
        "item_type": "folder.account",
        "name": "setup_account_la",
        "is_root": True,
    }
    response = await create_item(payload)
    laui = response.get("item_laui")
    print(f"[setup] Created account folder with LAUI: {laui}")
    return laui


async def get_or_create_trash_folder(db, account_laui: str):
    await create_item(
        {
            "name": "trash",
            "item_type": "folder.trash",
            "parent_laui": account_laui,
            "account_laui": account_laui,
        }
    )
    print("[setup] Created trash folder")


async def get_or_create_users_folder(db, account_laui: str) -> str:
    """Create folder.users under the account."""
    response = await create_item(
        {
            "item_type": "folder.users",
            "name": "users",
            "parent_laui": account_laui,
            "account_laui": account_laui,
        }
    )
    laui = response.get("item_laui")
    print(f"[setup] Created users folder with LAUI: {laui}")
    return laui


async def get_or_create_user_folder(
    db, users_folder_laui: str, username: str, account_laui: str
) -> str:
    """Create folder.user for the given username under folder.users."""
    response = await create_item(
        {
            "item_type": "folder.user",
            "name": username,
            "parent_laui": users_folder_laui,
            "account_laui": account_laui,
        }
    )
    laui = response.get("item_laui")
    print(f"[setup] Created user folder '{username}' with LAUI: {laui}")
    return laui


async def get_or_create_project_folder(db, account_laui: str) -> str:
    existing = await db["items"].find_one(
        {"item_type": "folder.project", "name": "sample_project_preview"}
    )
    if existing:
        laui = str(existing["_id"])
        print(f"[setup] Project folder already exists with LAUI: {laui}")
        return laui
    payload = {
        "item_type": "folder.project",
        "name": "sample_project_preview",
        "parent_laui": account_laui,
        "account_laui": account_laui,
    }
    response = await create_item(payload)
    laui = response.get("item_laui")
    print(f"[setup] Created project folder with LAUI: {laui}")
    return laui


async def get_or_create_organizational_folders(
    db, project_laui: str, account_laui: str
) -> dict[str, str]:
    folders = {}
    folder_types = ["payload", "config", "connection", "operator", "action", "workflow", "ai"]
    for folder_type in folder_types:
        response = await create_item(
            {
                "item_type": f"folder.{folder_type}",
                "name": folder_type,
                "parent_laui": project_laui,
                "project_laui": project_laui,
                "account_laui": account_laui,
            }
        )
        folders[folder_type] = response.get("item_laui")
        print(f"[setup] Created {folder_type} folder with LAUI: {folders[folder_type]}")
    return folders


async def get_or_create_asset_folder(
    project_laui: str, account_laui: str, skill_laui: str = None
) -> str:
    payload = {
        "item_type": "folder.asset",
        "name": "asset",
        "parent_laui": project_laui,
        "project_laui": project_laui,
        "account_laui": account_laui,
    }
    if skill_laui:
        payload["skill_laui"] = skill_laui
    response = await create_item(payload)
    laui = response.get("item_laui")
    print(f"[setup] Created asset folder with LAUI: {laui} (skill_laui={skill_laui})")
    return laui


# ---------------------------------------------------------------------------
# Item builders
# ---------------------------------------------------------------------------


def load_module_from_file(file_path: Path):
    module_name = file_path.stem
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_operator_item(
    module, name: str, parent_laui: str, project_laui: str = None, account_laui: str = None
) -> dict:
    operator_type = getattr(module, "operator_type", "unknown")
    meta = getattr(module, "metadata", {}) or {}
    item = {
        "item_type": f"operator.{operator_type}",
        "name": name,
        "codeblock": getattr(module, "codeblock", {}),
        "bashblock": getattr(module, "bashblock", {}),
        "connection": getattr(module, "connection", {}),
        "payload": getattr(module, "payload", ""),
        "description": getattr(module, "description", ""),
        "prompt": getattr(module, "prompt", ""),
        "guide_docs": getattr(module, "guide_docs", ""),
        "install_docs": getattr(module, "install_docs", ""),
        "publisher": getattr(module, "publisher", ""),
        "version_details": getattr(module, "version_details", {}),
        "tags": meta.get("tags", []),
        "category": [meta["category"]]
        if isinstance(meta.get("category"), str)
        else meta.get("category", []),
        "parent_laui": parent_laui,
    }
    if project_laui:
        item["project_laui"] = project_laui
    if account_laui:
        item["account_laui"] = account_laui
    return item


def build_action_item(
    module, name: str, parent_laui: str, project_laui: str = None, account_laui: str = None
) -> dict:
    item = {
        "item_type": "action",
        "name": name,
        "codeblock": getattr(module, "codeblock", {}),
        "bashblock": getattr(module, "bashblock", {}),
        "action_variables": getattr(module, "action_variables", {}),
        "connection": getattr(module, "connection", {}),
        "parent_laui": parent_laui,
    }
    if project_laui:
        item["project_laui"] = project_laui
    if account_laui:
        item["account_laui"] = account_laui
    return item


def build_connection_item(
    module, name: str, parent_laui: str, project_laui: str = None, account_laui: str = None
) -> dict:
    connection_type = getattr(module, "connection_type", "unknown")
    item = {
        "item_type": f"connection.{connection_type}",
        "name": name,
        "content": getattr(module, "connection", {}),
        "parent_laui": parent_laui,
    }
    if project_laui:
        item["project_laui"] = project_laui
    if account_laui:
        item["account_laui"] = account_laui
    return item


def build_payload_item(
    module, name: str, parent_laui: str, project_laui: str = None, account_laui: str = None
) -> dict:
    content = getattr(module, "payload", None) or getattr(module, "paylaod", "")
    item = {
        "item_type": "payload",
        "name": name,
        "content": content,
        "parent_laui": parent_laui,
    }
    if project_laui:
        item["project_laui"] = project_laui
    if account_laui:
        item["account_laui"] = account_laui
    return item


def build_config_item(
    module, name: str, parent_laui: str, project_laui: str = None, account_laui: str = None
) -> dict:
    item = {
        "item_type": "config",
        "name": name,
        "config_type": getattr(module, "config_type", "task"),
        "content": getattr(module, "config", {}),
        "parent_laui": parent_laui,
    }
    if project_laui:
        item["project_laui"] = project_laui
    if account_laui:
        item["account_laui"] = account_laui
    return item


def build_workflow_item(
    module, name: str, parent_laui: str, project_laui: str = None, account_laui: str = None
) -> dict:
    item = {
        "item_type": "workflow",
        "name": name,
        "content": getattr(module, "workflow", {}),
        "parent_laui": parent_laui,
    }
    if project_laui:
        item["project_laui"] = project_laui
    if account_laui:
        item["account_laui"] = account_laui
    return item


def build_asset_item(
    module,
    name: str,
    parent_laui: str,
    project_laui: str = None,
    account_laui: str = None,
    **kwargs,
) -> dict:
    module_item_type = getattr(module, "item_type", "asset")
    if module_item_type == "html_report":
        item = {
            "item_type": "html_report",
            "name": name,
            "description": getattr(module, "description", ""),
            "html": getattr(module, "html", ""),
            "parent_laui": parent_laui,
        }
    else:
        item = {
            "item_type": "asset",
            "name": name,
            "content": getattr(module, "asset", {}),
            "parent_laui": parent_laui,
        }
    skill_name = getattr(module, "skill_name", None)
    if skill_name:
        skill_laui = kwargs.get("skill_lauis_map", {}).get(skill_name)
        if skill_laui:
            item["skill_laui"] = skill_laui
    if project_laui:
        item["project_laui"] = project_laui
    if account_laui:
        item["account_laui"] = account_laui
    return item


def build_ai_agent_item(
    module,
    name: str,
    parent_laui: str,
    project_laui: str = None,
    account_laui: str = None,
    **kwargs,
) -> dict:
    item = {
        "item_type": "agent",
        "name": name,
        "codeblock": getattr(module, "codeblock", {}),
        "bashblock": getattr(module, "bashblock", {}),
        "connection": getattr(module, "connection", {}),
        "parent_laui": parent_laui,
    }
    if project_laui:
        item["project_laui"] = project_laui
    if account_laui:
        item["account_laui"] = account_laui
    return item


def build_ai_generate_item(
    module,
    name: str,
    parent_laui: str,
    project_laui: str = None,
    account_laui: str = None,
    **kwargs,
) -> dict:
    item = {
        "item_type": "generate",
        "name": name,
        "codeblock": getattr(module, "codeblock", {}),
        "bashblock": getattr(module, "bashblock", {}),
        "connection": getattr(module, "connection", {}),
        "parent_laui": parent_laui,
    }
    if project_laui:
        item["project_laui"] = project_laui
    if account_laui:
        item["account_laui"] = account_laui
    return item


def build_ai_skill_item(
    module,
    name: str,
    parent_laui: str,
    project_laui: str = None,
    account_laui: str = None,
    **kwargs,
) -> dict:
    skill_data = getattr(module, "skill", {})
    item = {
        "item_type": "skill",
        "name": name,
        "description": skill_data.get("description", ""),
        "content": skill_data.get("content", ""),
        "parent_laui": parent_laui,
    }
    if project_laui:
        item["project_laui"] = project_laui
    if account_laui:
        item["account_laui"] = account_laui
    return item


def build_usecase_item(
    module,
    name: str,
    parent_laui: str,
    project_laui: str = None,
    account_laui: str = None,
    **kwargs,
) -> dict:
    meta = getattr(module, "metadata", {})
    item = {
        "item_type": "usecase",
        "name": name,
        "description": getattr(module, "description", ""),
        "prompt": getattr(module, "prompt", ""),
        "guide_docs": getattr(module, "guide_docs", ""),
        "payloads": getattr(module, "payloads", {}),
        "skills": getattr(module, "skills", {}),
        "tags": meta.get("tags", []),
        "category": [meta["category"]]
        if isinstance(meta.get("category"), str)
        else meta.get("category", []),
        "publisher": getattr(module, "publisher", ""),
        "parent_laui": parent_laui,
    }
    if project_laui:
        item["project_laui"] = project_laui
    if account_laui:
        item["account_laui"] = account_laui
    return item


ITEM_BUILDERS = {
    "operator": build_operator_item,
    "action": build_action_item,
    "connection": build_connection_item,
    "payload": build_payload_item,
    "config": build_config_item,
    "workflow": build_workflow_item,
    "asset": build_asset_item,
    "agent": build_ai_agent_item,
    "generate": build_ai_generate_item,
    "skill": build_ai_skill_item,
    "usecase": build_usecase_item,
}


# ---------------------------------------------------------------------------
# Category registration (always create)
# ---------------------------------------------------------------------------


async def _register_directory(
    db,
    dir_path: Path,
    category_type: str,
    parent_laui: str,
    builder,
    category_root: Path,
    project_laui: str = None,
    account_laui: str = None,
    **extra_kwargs,
) -> dict:
    """
    Recursively walk *dir_path*, creating folder items for subdirectories
    and catalog items for .py files.  Always calls create_item regardless of
    whether an item with the same name already exists.
    Returns {relative_key: laui}.
    """
    all_items = {}

    # Process .py files in the current directory
    py_files = sorted(
        [
            f
            for f in dir_path.iterdir()
            if f.is_file() and f.suffix == ".py" and f.name != "__init__.py"
        ]
    )

    for py_file in py_files:
        name = py_file.stem
        key = str(py_file.relative_to(category_root).with_suffix(""))

        try:
            module = load_module_from_file(py_file)
            item_body = builder(
                module,
                name,
                parent_laui,
                project_laui=project_laui,
                account_laui=account_laui,
                **extra_kwargs,
            )
            response = await create_item(item_body)
            item_laui = response.get("item_laui")
            all_items[key] = item_laui
            print(f"[setup] Created {category_type} '{name}' with LAUI: {item_laui}")
        except Exception as e:
            print(f"[setup] Warning: Failed to process {py_file}: {e}")
            traceback.print_exc()

    # Recurse into subdirectories
    subdirs = sorted([d for d in dir_path.iterdir() if d.is_dir() and d.name != "__pycache__"])

    for subdir in subdirs:
        subfolder_item_type = (
            "folder.ai" if category_type in AI_CATEGORY_TYPES else f"folder.{category_type}"
        )
        subfolder_payload = {
            "item_type": subfolder_item_type,
            "name": subdir.name,
            "parent_laui": parent_laui,
        }
        if project_laui:
            subfolder_payload["project_laui"] = project_laui
        if account_laui:
            subfolder_payload["account_laui"] = account_laui
        response = await create_item(subfolder_payload)
        subfolder_laui = response.get("item_laui")
        print(
            f"[setup] Created {category_type} subfolder '{subdir.name}' with LAUI: {subfolder_laui}"
        )

        nested_items = await _register_directory(
            db,
            subdir,
            category_type,
            subfolder_laui,
            builder,
            category_root,
            project_laui,
            account_laui,
            **extra_kwargs,
        )
        all_items.update(nested_items)

    return all_items


async def register_category(
    db,
    category_folder: str,
    category_type: str,
    org_folder_laui: str,
    project_laui: str = None,
    account_laui: str = None,
    **extra_kwargs,
) -> dict:
    """
    Discover subfolders (arbitrarily nested) and .py files under a category
    folder and register them.  Always calls create_item for every item found.
    Returns {relative/path/name: laui} for all created items.
    """
    category_path = ONBOARDING_DIR / category_folder

    if not category_path.is_dir():
        print(f"[setup] Warning: Category folder not found: {category_path}")
        return {}

    builder = ITEM_BUILDERS.get(category_type)
    if not builder:
        print(f"[setup] Warning: No builder for category type: {category_type}")
        return {}

    return await _register_directory(
        db,
        category_path,
        category_type,
        org_folder_laui,
        builder,
        category_path,
        project_laui,
        account_laui,
        **extra_kwargs,
    )


# ---------------------------------------------------------------------------
# PostgreSQL tasks and workflow config (always create)
# ---------------------------------------------------------------------------


async def get_or_create_postgres_tasks(
    db,
    all_items: dict,
    workflow_folder_laui: str,
    account_laui: str,
    project_laui: str,
) -> dict:
    """Always create PostgreSQL tasks."""
    operator_laui = all_items["operator"]["Postgresql/PostgresqlExecuteSQL"]
    connection_laui = all_items["connection"]["Postgresql/PostgresqlPlusClaude"]
    create_payload_laui = all_items["payload"]["PostgresqlDemo/create_sql"]
    insert_payload_laui = all_items["payload"]["PostgresqlDemo/insert_sql"]
    update_payload_laui = all_items["payload"]["PostgresqlDemo/update_sql"]
    check_parents_action_laui = all_items["action"][
        "LeastActionLabs/LeastActionCheckIfParentsAreDone"
    ]

    now = datetime.now(UTC)
    start_date = (now + timedelta(minutes=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_date = (now + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

    task_configs = [
        {
            "name": "Postgres_Create_Table_Task",
            "payload_laui": create_payload_laui,
            "pre_actions": [],
        },
        {
            "name": "Postgres_Insert_Rows_Task",
            "payload_laui": insert_payload_laui,
            "depends_on": "Postgres_Create_Table_Task",
        },
        {
            "name": "Postgres_Update_Rows_Task",
            "payload_laui": update_payload_laui,
            "depends_on": "Postgres_Insert_Rows_Task",
        },
    ]

    created = {}
    for cfg in task_configs:
        task_name = cfg["name"]

        body = {
            "item_type": "task",
            "name": task_name,
            "project_laui": project_laui,
            "account_laui": account_laui,
            "parent_laui": workflow_folder_laui,
            "operator_laui": operator_laui,
            "connection_laui": connection_laui,
            "payload_laui": cfg["payload_laui"],
            "frequency": "*/3 * * * *",
            "start_date": start_date,
            "end_date": end_date,
        }

        depends_on = cfg.get("depends_on")
        if depends_on:
            body["actions"] = {
                "pre_actions": [
                    {
                        "laui": check_parents_action_laui,
                        "action_variables": {
                            "parents": [
                                {
                                    "task_name": depends_on,
                                    "project_laui": "{{ project_laui }}",
                                    "account_laui": "{{ account_laui }}",
                                    "partition": "{{ partition }}",
                                }
                            ]
                        },
                    }
                ],
            }

        response = await create_item(body)
        task_laui = response.get("item_laui")
        created[task_name] = task_laui
        print(f"[setup] Created task '{task_name}' with LAUI: {task_laui}")

    return created


async def get_or_create_workflow_config(
    db, workflow_folder_laui: str, project_laui: str, account_laui: str
):
    body = {
        "item_type": "config",
        "config_type": "workflow",
        "parent_laui": workflow_folder_laui,
        "name": "workflow_config",
        "project_laui": project_laui,
        "account_laui": account_laui,
        "content": {
            "defaults": {
                "task": {},
                "cron": {},
                "taskControlActions": [
                    {"action": "LeastActionCancel", "variables": {"state": ["running"]}},
                ],
                "uiActions": [
                    {"action": "LeastActionCancel", "variables": {"state": ["running"]}},
                    {"action": "LeastActionSchedule", "variables": {"state": ["error", "fail"]}},
                    {
                        "action": "LeastActionGitToTask",
                        "variables": {
                            "git_repo_url": "https://github.com/LeastAction-Labs/LeastAction-samples.git",
                            "git_branch": "main",
                            "folder_path": "DemoSaleReportingTasks_Postgresql",
                            "workflow_folder_name": "workflow",
                            "partition": "ALL",
                            "state": ["running"],
                        },
                    },
                ],
            },
            "parameters": {},
            "partition": "",
            "git": {},
            "priority": [],
            "overridable": [],
            "not_overridable": {},
        },
    }
    response = await create_item(body)
    print(f"[setup] Created workflow config with LAUI: {response.get('item_laui')}")


# ---------------------------------------------------------------------------
# Main setup
# ---------------------------------------------------------------------------


async def setup():
    """
    Setup: always creates all items on every run, regardless of whether they
    already exist in the DB.
    """
    uri = os.getenv("MONGO_URI")
    if not uri:
        raise Exception("MONGO_URI is not set")

    db_client = await create_mongo_client(uri)
    active_db = db_client.get_db()

    # System user (already idempotent — token-based, safe to keep)
    print("\n" + "=" * 60)
    print("SYSTEM USER")
    print("=" * 60 + "\n")
    system_user_laui, system_access_token = await create_system_user(db_client)

    global ACCESS_TOKEN
    ACCESS_TOKEN = system_access_token

    print("\n" + "=" * 60)
    print("ROOT USER")
    print("=" * 60 + "\n")
    root_user_laui = await create_root_user(db_client)

    print("\n" + "=" * 60)
    print("ADMINS GROUP")
    print("=" * 60 + "\n")
    admins_group_laui = await create_admins_group(db_client, root_user_laui)

    print("\n" + "=" * 60)
    print("FOLDER AND RESOURCE SETUP")
    print("=" * 60 + "\n")

    account_laui = await get_or_create_account_folder(active_db)
    await grant_owners_group_item_access(active_db, admins_group_laui)
    await get_or_create_trash_folder(active_db, account_laui)
    users_folder_laui = await get_or_create_users_folder(active_db, account_laui)
    await get_or_create_user_folder(active_db, users_folder_laui, "System", account_laui)
    project_laui = await get_or_create_project_folder(active_db, account_laui)
    folders = await get_or_create_organizational_folders(active_db, project_laui, account_laui)

    # Register skills first so we can wire skill_laui onto the asset folder
    print("\n--- Registering ai/skills ---")
    skill_items = await register_category(
        active_db,
        "ai/skills",
        "skill",
        folders["ai"],
        project_laui=project_laui,
        account_laui=account_laui,
    )

    report_explorer_skill_laui = skill_items.get("ReportExplorer/report_explorer_assistant")
    folders["asset"] = await get_or_create_asset_folder(
        project_laui, account_laui, report_explorer_skill_laui
    )

    all_items: dict[str, dict] = {"skill": skill_items}
    for category_folder, category_type in CATEGORY_MAP.items():
        if category_type == "skill":
            continue  # already registered above
        print(f"\n--- Registering {category_folder} ---")
        if category_type in ("agent", "generate", "usecase"):
            org_folder_laui = folders["ai"]
        else:
            org_folder_laui = folders[category_type]
        extra = {"skill_lauis_map": skill_items} if category_type == "asset" else {}
        items = await register_category(
            active_db,
            category_folder,
            category_type,
            org_folder_laui,
            project_laui=project_laui,
            account_laui=account_laui,
            **extra,
        )
        all_items[category_type] = items

    print("\n--- PostgreSQL Tasks ---")
    await get_or_create_postgres_tasks(
        active_db,
        all_items=all_items,
        workflow_folder_laui=folders["workflow"],
        account_laui=account_laui,
        project_laui=project_laui,
    )

    print("\n--- Workflow Config ---")
    await get_or_create_workflow_config(
        active_db,
        workflow_folder_laui=folders["workflow"],
        project_laui=project_laui,
        account_laui=account_laui,
    )

    print("\n" + "=" * 60)
    print("SETUP SUMMARY")
    print("=" * 60)
    print(f"System User LAUI : {system_user_laui}")
    print(f"Root User LAUI   : {root_user_laui}")
    print(f"Account LAUI     : {account_laui}")
    print(f"Project LAUI     : {project_laui}")
    for category_type, items in all_items.items():
        print(f"\n  {category_type}s:")
        for name, laui in items.items():
            print(f"    {name}: {laui}")
    print("=" * 60 + "\n")


async def setup_with_retry(max_retries: int = 2):
    for attempt in range(max_retries):
        try:
            await setup()
            print(f"\n{'=' * 60}")
            print("SETUP COMPLETED SUCCESSFULLY!")
            print(f"{'=' * 60}")
            return
        except Exception as e:
            print(f"\n{'=' * 60}")
            print(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            print(f"{'=' * 60}")
            traceback.print_exc()

            if attempt == max_retries - 1:
                print("\nAll retry attempts exhausted. Setup failed.")
                raise

            print(f"\nRetrying in 2 seconds... (Attempt {attempt + 2}/{max_retries})")
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(setup_with_retry())
