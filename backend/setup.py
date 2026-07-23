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
from src.core.ee.license.repo import LicenseRepository
from src.core.ee.license.schema import License
from src.core.ee.license.service import LicenseService

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

    license_repo = LicenseRepository(db=db_client.get_db())
    license_service = LicenseService(license_repo)
    user_repo = UserRepository(db=db_client.get_db())
    user_service = UserService(user_repo=user_repo, license_service=license_service)

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

    license_repo = LicenseRepository(db=db_client.get_db())
    license_service = LicenseService(license_repo)
    user_repo = UserRepository(db=db_client.get_db())
    user_service = UserService(user_repo=user_repo, license_service=license_service)

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
    url = f"{BACKEND_URL}/api/v1/catalog/create"
    if item_body.get("item_type") in ["task", "action"]:
        url = f"{BACKEND_URL}/api/v1/{item_body['item_type']}"
    try:
        item_response = requests.post(
            url,
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
        "category": meta.get("category", ""),
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
    metadata = getattr(module, "metadata", {})
    service = ""
    if isinstance(metadata, dict):
        service = str(metadata.get("service", "")).strip().lower()
    item = {
        "item_type": f"agent.{service}" if service else "agent",
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
        "category": meta.get("category", ""),
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
    connection_laui = all_items["connection"]["Postgresql/Postgresql"]
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


async def get_or_create_sales_pipeline_tasks(
    db,
    all_items: dict,
    workflow_folder_laui: str,
    reports_folder_laui: str,
    account_laui: str,
    project_laui: str,
    debug_reports_folder_laui: str = None,
    ai_connection_laui: str = None,
    ai_chat_laui: str = None,
) -> dict:
    """Create the 8-task dbt sales reporting pipeline (seed + contract + 3 dbt + validation + 2 reports)."""
    sql_operator_laui = all_items["operator"]["Postgresql/PostgresqlExecuteSQL"]
    dbt_operator_laui = all_items["operator"]["DBT/DBTRunModel"]
    report_operator_laui = all_items["operator"]["Postgresql/PostgresqlGenerateHtmlTableReport"]
    validator_operator_laui = all_items["operator"]["Postgresql/PostgresqlValidatorSQL"]
    pg_connection_laui = all_items["connection"]["Postgresql/dbt_postgresql"]
    dbt_connection_laui = all_items["connection"]["DBT/DbtServer"]
    check_parents_action_laui = all_items["action"][
        "LeastActionLabs/LeastActionCheckIfParentsAreDone"
    ]

    task_configs = [
        {
            "name": "00_fact_sales_daily",
            "operator_laui": sql_operator_laui,
            "connection_laui": pg_connection_laui,
            "payload": """
DROP TABLE IF EXISTS fact_sales_daily CASCADE;
CREATE TABLE fact_sales_daily (
    sale_id BIGSERIAL, sale_date DATE NOT NULL, sale_timestamp TIMESTAMP NOT NULL,
    product_id VARCHAR(50) NOT NULL, product_name VARCHAR(100) NOT NULL,
    category_id VARCHAR(50) NOT NULL, category_name VARCHAR(100) NOT NULL,
    region_id VARCHAR(50) NOT NULL, region_name VARCHAR(100) NOT NULL,
    sub_region_name VARCHAR(100), store_id VARCHAR(50) NOT NULL, store_name VARCHAR(100) NOT NULL,
    sales_channel VARCHAR(50),
    revenue DECIMAL(15,2) NOT NULL, units_sold INTEGER NOT NULL, cost DECIMAL(15,2) NOT NULL,
    discount_amount DECIMAL(15,2) DEFAULT 0, shipping_cost DECIMAL(15,2) DEFAULT 0,
    tax_amount DECIMAL(15,2) DEFAULT 0,
    PRIMARY KEY (sale_id)
);

-- Realistic 5-year tech-retail sales, generated DETERMINISTICALLY (hash-based, not
-- random()) so every reseed is identical. Layers: catalog x stores x calendar, with a
-- multiplicative demand model = base_units * store_scale * weekday * season/holiday
-- * lifecycle(product age) * deterministic-noise. This gives real weekend lift, Nov/Dec
-- holiday spikes, and per-SKU ramp/decline so the downstream DoD/WoW/YoY/rolling metrics
-- are meaningful rather than noise.
INSERT INTO fact_sales_daily (
    sale_date, sale_timestamp, product_id, product_name,
    category_id, category_name, region_id, region_name, sub_region_name,
    store_id, store_name, sales_channel,
    revenue, units_sold, cost, discount_amount, shipping_cost, tax_amount
)
WITH products0(product_id, product_name, category_id, category_name, base_price, cost_ratio, base_units, launch_date, holiday_lift) AS (
    VALUES
    ('P001','Aurora 13 Ultrabook','CAT-01','Electronics',1299.00,0.84,5,DATE '2020-02-01',0.60),
    ('P002','Aurora 15 Pro Laptop','CAT-01','Electronics',1799.00,0.85,4,DATE '2020-02-01',0.60),
    ('P003','Vertex Gaming Laptop','CAT-01','Electronics',2199.00,0.84,3,DATE '2021-06-01',0.75),
    ('P004','Lumina 27-inch 4K Monitor','CAT-01','Electronics',549.00,0.72,6,DATE '2020-05-01',0.45),
    ('P005','Lumina 32-inch Ultrawide','CAT-01','Electronics',899.00,0.74,4,DATE '2021-09-01',0.45),
    ('P006','Pulse 11 Tablet','CAT-01','Electronics',649.00,0.80,7,DATE '2020-08-01',0.55),
    ('P007','Pulse Phone X','CAT-01','Electronics',999.00,0.82,8,DATE '2021-10-01',0.70),
    ('P008','Pulse Phone SE','CAT-01','Electronics',499.00,0.78,10,DATE '2022-04-01',0.55),
    ('P009','Nimbus Mini PC','CAT-01','Electronics',749.00,0.79,3,DATE '2023-03-01',0.40),
    ('P010','Aurora 14 (2024 refresh)','CAT-01','Electronics',1399.00,0.84,5,DATE '2024-01-15',0.60),
    ('P011','Glide Wireless Mouse','CAT-02','Peripherals',39.00,0.55,20,DATE '2020-01-01',0.30),
    ('P012','Glide Pro Ergo Mouse','CAT-02','Peripherals',79.00,0.58,10,DATE '2021-03-01',0.30),
    ('P013','Clack Mechanical Keyboard','CAT-02','Peripherals',129.00,0.60,9,DATE '2020-04-01',0.35),
    ('P014','Clack TKL Wireless','CAT-02','Peripherals',149.00,0.61,7,DATE '2022-02-01',0.35),
    ('P015','LinkHub USB-C Dock','CAT-02','Peripherals',89.00,0.56,12,DATE '2020-06-01',0.30),
    ('P016','View HD Webcam','CAT-02','Peripherals',69.00,0.57,11,DATE '2020-03-15',0.35),
    ('P017','View 4K Webcam','CAT-02','Peripherals',149.00,0.62,6,DATE '2022-07-01',0.35),
    ('P018','Echo Gaming Headset','CAT-03','Audio',119.00,0.63,10,DATE '2020-05-15',0.55),
    ('P019','Echo Wireless Earbuds','CAT-03','Audio',149.00,0.60,14,DATE '2021-05-01',0.65),
    ('P020','Echo Studio Earbuds Pro','CAT-03','Audio',229.00,0.62,8,DATE '2023-05-01',0.65),
    ('P021','Boom Bluetooth Speaker','CAT-03','Audio',99.00,0.58,12,DATE '2020-09-01',0.55),
    ('P022','Clarity USB Microphone','CAT-03','Audio',129.00,0.60,6,DATE '2021-08-01',0.40),
    ('P023','Halo LED Desk Lamp','CAT-04','Lighting',49.00,0.52,13,DATE '2020-02-15',0.30),
    ('P024','Halo Smart Lamp','CAT-04','Lighting',89.00,0.55,8,DATE '2022-03-01',0.35),
    ('P025','Glow LED Strip Kit','CAT-04','Lighting',34.00,0.50,16,DATE '2021-01-15',0.45),
    ('P026','Ring Light Studio','CAT-04','Lighting',79.00,0.53,7,DATE '2021-11-01',0.40),
    ('P027','Ascend Standing Desk','CAT-05','Furniture',599.00,0.64,4,DATE '2020-07-01',0.35),
    ('P028','Ascend Desk Compact','CAT-05','Furniture',399.00,0.62,5,DATE '2022-05-01',0.35),
    ('P029','Recline Ergonomic Chair','CAT-05','Furniture',449.00,0.60,5,DATE '2020-10-01',0.40),
    ('P030','Mount Pro Monitor Arm','CAT-05','Furniture',119.00,0.56,8,DATE '2021-04-01',0.30)
),
products AS (
    -- Roll the staggered launch dates forward with the window so the newest SKU
    -- launches ~1 year before today and every reseed stays current (CURRENT_DATE-relative).
    SELECT product_id, product_name, category_id, category_name, base_price, cost_ratio, base_units,
           (launch_date + (CURRENT_DATE - DATE '2024-12-31'))::date AS launch_date, holiday_lift
    FROM products0
),
stores(store_id, store_name, region_id, region_name, sub_region_name, sales_channel, store_scale) AS (
    VALUES
    ('S001','Manhattan Flagship','R01','North America','Northeast','retail',1.7),
    ('S002','SF Union Square','R01','North America','West Coast','retail',1.5),
    ('S003','Chicago Mag Mile','R01','North America','Midwest','retail',1.2),
    ('S004','Online US','R01','North America','National','online',2.3),
    ('S005','London Oxford St','R02','Europe','Western Europe','retail',1.4),
    ('S006','Berlin Mitte','R02','Europe','Central Europe','retail',1.1),
    ('S007','Online EU','R02','Europe','Continental','online',1.9),
    ('S008','Tokyo Ginza','R03','Asia Pacific','East Asia','retail',1.3),
    ('S009','Singapore Orchard','R03','Asia Pacific','Southeast Asia','retail',1.1),
    ('S010','Sydney CBD','R03','Asia Pacific','Oceania','retail',1.0)
),
calendar AS (
    SELECT d::date AS sale_date,
           EXTRACT(dow FROM d)::int   AS dow,
           EXTRACT(doy FROM d)::int   AS doy,
           EXTRACT(month FROM d)::int AS mon,
           EXTRACT(day FROM d)::int   AS dom
    FROM generate_series((CURRENT_DATE - INTERVAL '5 years')::date, CURRENT_DATE, INTERVAL '1 day') AS g(d)
),
demand AS (
    SELECT
        c.sale_date, c.dow, c.mon, c.dom,
        p.product_id, p.product_name, p.category_id, p.category_name, p.base_price, p.cost_ratio,
        s.store_id, s.store_name, s.region_id, s.region_name, s.sub_region_name, s.sales_channel,
        GREATEST(0, round(
            p.base_units * s.store_scale
            -- weekday: retail lifts on the weekend (dow 0=Sun, 6=Sat)
            * (CASE c.dow WHEN 0 THEN 1.25 WHEN 6 THEN 1.40 WHEN 5 THEN 1.08 ELSE 0.92 END)
            -- annual seasonal wave x holiday windows (Nov/Dec surge, back-to-school, post-holiday slump)
            * ((1.0 + 0.10 * sin(2 * pi() * (c.doy - 80) / 365.0))
               * (CASE
                    WHEN c.mon = 12 THEN 1.0 + p.holiday_lift
                    WHEN c.mon = 11 AND c.dom >= 20 THEN 1.0 + p.holiday_lift
                    WHEN c.mon = 11 THEN 1.15
                    WHEN c.mon = 8 THEN 1.18
                    WHEN c.mon = 7 AND c.dom <= 7 THEN 1.12
                    WHEN c.mon = 1 AND c.dom <= 12 THEN 0.78
                    ELSE 1.0 END))
            -- lifecycle by product age: ramp (0-90d) -> mild growth to ~2y -> slow decline
            * (CASE
                 WHEN (c.sale_date - p.launch_date) < 90 THEN 0.35 + 0.65 * ((c.sale_date - p.launch_date) / 90.0)
                 WHEN (c.sale_date - p.launch_date) <= 730 THEN 1.0 + 0.12 * (((c.sale_date - p.launch_date) - 90) / 640.0)
                 ELSE GREATEST(0.45, 1.12 - 0.00035 * ((c.sale_date - p.launch_date) - 730)) END)
            -- deterministic noise in [0.78, 1.22], stable across reseeds
            * (0.78 + 0.44 * ((abs(hashtext(p.product_id || s.store_id || c.sale_date::text)) % 1000) / 1000.0))
        ))::int AS units
    FROM calendar c
    CROSS JOIN products p
    CROSS JOIN stores s
    WHERE c.sale_date >= p.launch_date
)
SELECT
    d.sale_date,
    d.sale_date::timestamp + ((10 + (abs(hashtext(d.product_id || d.store_id || d.sale_date::text || 'h')) % 11)) * INTERVAL '1 hour') AS sale_timestamp,
    d.product_id, d.product_name, d.category_id, d.category_name,
    d.region_id, d.region_name, d.sub_region_name,
    d.store_id, d.store_name, d.sales_channel,
    round((d.units * d.base_price) * (1 - disc.rate), 2)                 AS revenue,
    d.units                                                             AS units_sold,
    round(d.units * d.base_price * d.cost_ratio, 2)                      AS cost,
    round((d.units * d.base_price) * disc.rate, 2)                       AS discount_amount,
    CASE WHEN d.sales_channel = 'online' THEN round(d.units * 1.50, 2) ELSE 0.00 END AS shipping_cost,
    round((d.units * d.base_price) * (1 - disc.rate) * 0.08, 2)          AS tax_amount
FROM demand d
CROSS JOIN LATERAL (
    -- promo depth: deeper on the holiday window + weekends, but always < margin so profit stays positive
    SELECT (CASE
        WHEN d.mon = 12 OR (d.mon = 11 AND d.dom >= 20) THEN 0.10
        WHEN d.mon = 8 THEN 0.07
        WHEN d.dow IN (0, 6) THEN 0.05
        ELSE 0.02 END) AS rate
) disc
WHERE d.units >= 1;
""",
        },
        {
            "name": "00b_sales_contract",
            "operator_laui": validator_operator_laui,
            "connection_laui": pg_connection_laui,
            "payload": """
report_title: 'Data Contract — fact_sales_daily'
output_table: 'sales_contract_reports'

queries:
  - name: 'Schema — required columns & types'
    sql: "SELECT COUNT(*) AS missing FROM (VALUES ('sale_id','bigint'),('sale_date','date'),('revenue','numeric'),('units_sold','integer'),('cost','numeric'),('product_id','character varying'),('category_name','character varying'),('region_name','character varying'),('store_id','character varying')) AS c(col, typ) LEFT JOIN information_schema.columns ic ON ic.table_name='fact_sales_daily' AND ic.column_name=c.col AND ic.data_type=c.typ WHERE ic.column_name IS NULL"
    severity: critical
    pass_condition: 'missing == 0'
    display: scalar

  - name: 'Schema — product_name is VARCHAR(100)'
    description: 'The contracted max length; changing it is a breaking contract change (needs consumer sign-off).'
    sql: "SELECT count(*) AS mismatch FROM information_schema.columns WHERE table_name='fact_sales_daily' AND column_name='product_name' AND character_maximum_length <> 100"
    severity: critical
    pass_condition: 'mismatch == 0'
    display: scalar

  - name: 'Primary key — sale_id unique'
    sql: "SELECT sale_id, COUNT(*) AS dupes FROM fact_sales_daily GROUP BY sale_id HAVING COUNT(*) > 1 LIMIT 5"
    severity: critical
    pass_condition: 'row_count == 0'
    display: table

  - name: 'Nullability — required NOT NULL'
    sql: "SELECT COUNT(*) AS null_rows FROM fact_sales_daily WHERE sale_date IS NULL OR revenue IS NULL OR units_sold IS NULL OR cost IS NULL OR product_id IS NULL OR category_name IS NULL OR region_name IS NULL OR store_id IS NULL"
    severity: critical
    pass_condition: 'null_rows == 0'
    display: scalar

  - name: 'Domain — revenue & profit non-negative'
    sql: "SELECT COUNT(*) AS bad FROM fact_sales_daily WHERE revenue < 0 OR cost < 0 OR revenue < cost"
    severity: warning
    pass_condition: 'bad == 0'
    display: scalar

  - name: 'Domain — units_sold positive'
    sql: "SELECT COUNT(*) AS bad FROM fact_sales_daily WHERE units_sold <= 0"
    severity: warning
    pass_condition: 'bad == 0'
    display: scalar

  - name: 'Domain — per-row revenue within a sane ceiling'
    description: 'Guards against a source fan-out inflating a single product/store/day.'
    sql: "SELECT COUNT(*) AS bad FROM fact_sales_daily WHERE revenue > 500000"
    severity: warning
    pass_condition: 'bad == 0'
    display: scalar

  - name: 'Referential — category_name in the allowed set'
    sql: "SELECT COUNT(*) AS bad FROM fact_sales_daily WHERE category_name NOT IN ('Electronics','Peripherals','Audio','Lighting','Furniture')"
    severity: warning
    pass_condition: 'bad == 0'
    display: scalar

  - name: 'Referential — region_name in the allowed set'
    sql: "SELECT COUNT(*) AS bad FROM fact_sales_daily WHERE region_name NOT IN ('North America','Europe','Asia Pacific','Latin America','Middle East')"
    severity: warning
    pass_condition: 'bad == 0'
    display: scalar

  - name: 'Referential — product_id format Pnnn'
    sql: "SELECT COUNT(*) AS bad FROM fact_sales_daily WHERE product_id !~ '^P[0-9]{3}$'"
    severity: warning
    pass_condition: 'bad == 0'
    display: scalar

  - name: 'Freshness — multi-year span present'
    sql: "SELECT (MAX(sale_date) - MIN(sale_date)) AS span_days FROM fact_sales_daily"
    severity: critical
    pass_condition: 'span_days >= 1400'
    display: scalar

  - name: 'Volume — row count within the expected band'
    sql: "SELECT COUNT(*) AS row_count FROM fact_sales_daily"
    severity: critical
    pass_condition: 'row_count >= 100000 and row_count <= 2000000'
    display: scalar
""",
            "depends_on": "00_fact_sales_daily",
        },
        {
            "name": "01_cube_aggregation",
            "operator_laui": dbt_operator_laui,
            "connection_laui": dbt_connection_laui,
            "payload": '{"model": "fact_product_agg_daily_stage1"}',
            "depends_on": "00_fact_sales_daily",
        },
        {
            "name": "02_rolling_metrics",
            "operator_laui": dbt_operator_laui,
            "connection_laui": dbt_connection_laui,
            "payload": '{"model": "fact_product_agg_daily_stage2"}',
            "depends_on": "01_cube_aggregation",
        },
        {
            "name": "03_final_metrics",
            "operator_laui": dbt_operator_laui,
            "connection_laui": dbt_connection_laui,
            "payload": '{"model": "fact_product_agg_daily"}',
            "depends_on": "02_rolling_metrics",
        },
        {
            "name": "03b_sales_validation",
            "operator_laui": validator_operator_laui,
            "connection_laui": pg_connection_laui,
            "payload": f"""
report_title: 'Sales Pipeline Validation'
output_table: 'sales_validation_reports'
output_parent_laui: '{reports_folder_laui}'

queries:
  - name: 'Stage1 non-empty'
    sql: "SELECT COUNT(*) AS row_count FROM fact_product_agg_daily_stage1"
    severity: critical
    pass_condition: 'row_count > 0'
    display: scalar

  - name: 'Final table non-empty'
    sql: "SELECT COUNT(*) AS row_count FROM fact_product_agg_daily"
    severity: critical
    pass_condition: 'row_count > 0'
    display: scalar

  - name: 'Metric coverage — at least 25 metric types'
    sql: "SELECT COUNT(DISTINCT metric_key) AS metric_count FROM fact_product_agg_daily"
    severity: warning
    pass_condition: 'metric_count >= 25'
    display: scalar

  - name: 'No NULL metric values'
    sql: "SELECT COUNT(*) AS null_count FROM fact_product_agg_daily WHERE metric_value IS NULL"
    severity: critical
    pass_condition: 'null_count == 0'
    display: scalar

  - name: 'Reconciliation — product revenue sums to the grand total'
    description: 'Sum of per-product revenue must equal the fully-aggregated total each day (cube integrity; catches source fan-out).'
    sql: "SELECT COUNT(*) AS bad FROM (SELECT p.date FROM fact_product_agg_daily p JOIN fact_product_agg_daily g ON g.date=p.date AND g.metric_key='revenue' AND g.dim_key_grouping='dim_product::dim_category::dim_region::dim_subregion' WHERE p.metric_key='revenue' AND p.dim_key_grouping LIKE '%::dim_category::dim_region::dim_subregion' AND p.dim_key_grouping NOT LIKE 'dim_product::%' GROUP BY p.date HAVING ABS(SUM(p.metric_value) - MAX(g.metric_value)) > 1.0) x"
    severity: critical
    pass_condition: 'bad == 0'
    display: scalar

  - name: 'Freshness — no missing days in the last 14'
    sql: "SELECT COUNT(*) AS missing_days FROM (SELECT generate_series((SELECT MAX(date) FROM fact_product_agg_daily) - INTERVAL '13 days', (SELECT MAX(date) FROM fact_product_agg_daily), INTERVAL '1 day')::date AS d) cal LEFT JOIN (SELECT DISTINCT date FROM fact_product_agg_daily) f ON f.date=cal.d WHERE f.date IS NULL"
    severity: critical
    pass_condition: 'missing_days == 0'
    display: scalar

  - name: 'WoW — same-day-last-week swing within band (grand total)'
    description: 'Total revenue should not swing more than 50% versus the same weekday last week.'
    sql: "SELECT COUNT(*) AS bad FROM fact_product_agg_daily r JOIN fact_product_agg_daily w ON w.date=r.date AND w.dim_key_grouping=r.dim_key_grouping AND w.dim_value=r.dim_value AND w.metric_key='revenue_wow' WHERE r.metric_key='revenue' AND r.dim_key_grouping='dim_product::dim_category::dim_region::dim_subregion' AND r.date >= (SELECT MAX(date) FROM fact_product_agg_daily) - INTERVAL '30 days' AND r.metric_value > 0 AND ABS(w.metric_value) > 0.5 * r.metric_value"
    severity: warning
    pass_condition: 'bad == 0'
    display: scalar

  - name: 'Anomaly — revenue within 3 sigma of its 10-day moving average'
    description: 'Flags product/day points deviating more than 3 standard deviations from their own 10-day mean.'
    sql: "SELECT COUNT(*) AS bad FROM fact_product_agg_daily r JOIN fact_product_agg_daily a ON a.date=r.date AND a.dim_key_grouping=r.dim_key_grouping AND a.dim_value=r.dim_value AND a.metric_key='revenue_avg_10d' JOIN fact_product_agg_daily s ON s.date=r.date AND s.dim_key_grouping=r.dim_key_grouping AND s.dim_value=r.dim_value AND s.metric_key='revenue_std_10d' WHERE r.metric_key='revenue' AND r.date >= (SELECT MAX(date) FROM fact_product_agg_daily) - INTERVAL '30 days' AND s.metric_value > 0 AND ABS(r.metric_value - a.metric_value) > 3 * s.metric_value"
    severity: warning
    pass_condition: 'bad <= 20'
    display: scalar

  - name: 'YoY — year-over-year within a plausible band (grand total)'
    description: 'Total revenue YoY delta should stay within 60% of current; a larger jump signals a fan-out, not real growth.'
    sql: "SELECT COUNT(*) AS bad FROM fact_product_agg_daily y JOIN fact_product_agg_daily r ON r.date=y.date AND r.dim_key_grouping=y.dim_key_grouping AND r.dim_value=y.dim_value AND r.metric_key='revenue' WHERE y.metric_key='revenue_yoy' AND y.dim_key_grouping='dim_product::dim_category::dim_region::dim_subregion' AND y.date >= (SELECT MAX(date) FROM fact_product_agg_daily) - INTERVAL '30 days' AND r.metric_value > 0 AND ABS(y.metric_value) > 0.6 * r.metric_value"
    severity: warning
    pass_condition: 'bad == 0'
    display: scalar
""",
            "depends_on": "03_final_metrics",
        },
    ]

    import json as _json

    # Analyst-grade dashboards: each block is a section that expands one dimension
    # into item rows, with indented %-variance sub-rows (DoD/LWSD/YoY) and a set of
    # right-hand analytic columns. Everything derives from cube metrics that already
    # exist (<base>_dod/_wow/_yoy/_pct_of_total); the operator computes the sparkline
    # + Std + true WoW from the trailing series it pulls (default 12 weeks).
    # dim_key = product::category::region::subregion; '*' expands one row per value.
    _grand = "dim_product::dim_category::dim_region::dim_subregion"  # grand-total grouping (dim_value='')
    _summary_cols = ["trend", "std", "dod", "yoy", "lwsd", "share"]  # DoD not WoW: these are daily reports

    perf_template = [
        # Company-wide totals (fixed grand-total grouping, no '*') with variance sub-rows.
        {
            "display_name": "Gross Revenue",
            "dim_key_grouping": _grand,
            "dim_value": "",
            "metric_key": "revenue",
            "cell_format": "${value:,.0f}",
            "indent": 0,
            "text_bold": True,
            "variance_rows": ["dod", "lwsd", "yoy"],
        },
        {
            # Gross Profit stands in for "Discounts" from the mock: discount has no
            # derived cube metrics (_dod/_yoy/_pct_of_total), so its variance/share
            # cells would be blank. Profit is fully covered. (Add discount to the
            # dbt metric_key lists + reseed if a Discounts block is required.)
            "display_name": "Gross Profit",
            "dim_key_grouping": _grand,
            "dim_value": "",
            "metric_key": "profit",
            "cell_format": "${value:,.0f}",
            "indent": 0,
            "text_bold": True,
            "variance_rows": ["dod", "lwsd", "yoy"],
        },
        # Revenue expanded by product (top 10 by latest revenue), each with a DoD row.
        {
            "display_name": "Revenue by Product",
            "show_display_name": True,
            "dim_key_grouping": "*::dim_category::dim_region::dim_subregion",
            "metric_key": "revenue",
            "cell_format": "${value:,.0f}",
            "cell_bg_color": "#E8F5E9",
            "indent": 0,
            "sort_order": "value",
            "limit": 10,
            "variance_rows": ["dod"],
        },
        # Revenue expanded by region.
        {
            "display_name": "Revenue by Region",
            "show_display_name": True,
            "dim_key_grouping": "dim_product::dim_category::*::dim_subregion",
            "metric_key": "revenue",
            "cell_format": "${value:,.0f}",
            "cell_bg_color": "#E3F2FD",
            "indent": 0,
            "sort_order": "value",
            "variance_rows": ["dod"],
        },
        # Revenue by product x region (two '*'); renders only if the cube carries the
        # combined grouping, otherwise the block is skipped with no error.
        {
            "display_name": "Revenue by Product and Region",
            "show_display_name": True,
            "dim_key_grouping": "*::dim_category::*::dim_subregion",
            "metric_key": "revenue",
            "cell_format": "${value:,.0f}",
            "indent": 0,
            "sort_order": "value",
            "limit": 10,
        },
    ]
    category_template = [
        {
            "display_name": "Gross Revenue",
            "dim_key_grouping": _grand,
            "dim_value": "",
            "metric_key": "revenue",
            "cell_format": "${value:,.0f}",
            "indent": 0,
            "text_bold": True,
            "variance_rows": ["dod", "lwsd", "yoy"],
        },
        {
            "display_name": "Revenue by Category",
            "show_display_name": True,
            "dim_key_grouping": "dim_product::*::dim_region::dim_subregion",
            "metric_key": "revenue",
            "cell_format": "${value:,.0f}",
            "cell_bg_color": "#E8F5E9",
            "indent": 0,
            "sort_order": "value",
            "variance_rows": ["dod", "yoy"],
        },
        {
            "display_name": "Profit by Category",
            "show_display_name": True,
            "dim_key_grouping": "dim_product::*::dim_region::dim_subregion",
            "metric_key": "profit",
            "cell_format": "${value:,.0f}",
            "cell_bg_color": "#E3F2FD",
            "indent": 0,
            "sort_order": "value",
            "variance_rows": ["dod"],
        },
    ]

    report_configs = [
        (
            "04_sales_performance_report",
            "Sales Performance Dashboard",
            "fact_product_agg_daily",
            "#1565C0",
            "corporate_blue",
            perf_template,
        ),
        (
            "05_category_performance_report",
            "Category Performance",
            "fact_product_agg_daily",
            "#2E7D32",
            "modern_green",
            category_template,
        ),
    ]

    for name, title, table, header_color, theme, metric_template in report_configs:
        payload = _json.dumps(
            {
                "data": {
                    "report_title": title,
                    "output_table": "sales_pipeline_reports",
                    "output_parent_laui": reports_folder_laui,
                    "report_style": {
                        "theme": theme,
                        "header_bg_color": header_color,
                        "header_text_color": "#FFFFFF",
                        "row_bg_color_even": "#f9f9f9",
                        "row_bg_color_odd": "#ffffff",
                        "row_hover_color": "#E3F2FD",
                        "border_color": "#BBDEFB",
                        "font_family": "Segoe UI, Arial, sans-serif",
                    },
                    "database": {
                        "host": "postgres-demo",
                        "port": 5432,
                        "database": "postgres_demo_db",
                        "user": "postgres",
                        "password": "postgres",
                    },
                    "date_columns": 4,
                    "trend_weeks": 12,
                    "summary_columns": _summary_cols,
                    "query": {
                        "table": table,
                        "limit": None,
                    },
                    "metric_template": metric_template,
                }
            }
        )
        task_configs.append(
            {
                "name": name,
                "operator_laui": report_operator_laui,
                "connection_laui": pg_connection_laui,
                "payload": payload,
                "depends_on": "03_final_metrics",
            }
        )

    now = datetime.now(UTC)
    created = {}
    for cfg in task_configs:
        task_name = cfg["name"]

        body = {
            "item_type": "task",
            "name": task_name,
            "project_laui": project_laui,
            "account_laui": account_laui,
            "parent_laui": workflow_folder_laui,
            "operator_laui": cfg["operator_laui"],
            "connection_laui": cfg["connection_laui"],
            "frequency": "0 2 * * *",
            "start_date": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_date": (now + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "partition": "ALL",
            "payload": cfg["payload"],
        }

        depends_on = cfg.get("depends_on")
        pre_actions = []
        if depends_on:
            if isinstance(depends_on, str):
                depends_on = [depends_on]
            pre_actions = [
                {
                    "laui": check_parents_action_laui,
                    "action_variables": {
                        "parents": [
                            {
                                "task_name": dep,
                                "project_laui": "{{ project_laui }}",
                                "account_laui": "{{ account_laui }}",
                                "partition": "{{ partition }}",
                            }
                            for dep in depends_on
                        ]
                    },
                }
            ]

        debug_action_laui = all_items["action"].get("LeastActionLabs/LeastActionAgentDebug")
        post_actions = []
        if debug_action_laui and debug_reports_folder_laui and ai_connection_laui and ai_chat_laui:
            post_actions = [
                {
                    "laui": debug_action_laui,
                    "name": "LeastActionAgentDebug",
                    "action_variables": {
                        "skill_names": [
                            "DBT_Postgresql_Sales_Pipelines_Skill",
                            "DBT_Postgresql_Sales_Data_Contract",
                        ],
                        "chat_laui": ai_chat_laui,
                        "ai_connection": ai_connection_laui,
                        "notify": {
                            "asset_laui": debug_reports_folder_laui,
                            "asset_project_laui": project_laui,
                            "asset_account_laui": account_laui,
                        },
                    },
                }
            ]

        body["actions"] = {
            "pre_actions": pre_actions,
            "post_actions": post_actions,
        }

        response = await create_item(body)
        task_laui = response.get("item_laui")
        created[task_name] = task_laui
        print(f"[setup] Created sales task '{task_name}' with LAUI: {task_laui}")

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

    report_explorer_skill_laui = skill_items.get("skills/LeastAction/report_explorer_assistant")
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

    # Create workflow subfolders
    print("\n--- Workflow Subfolders ---")
    pg_demo_workflow = await create_item(
        {
            "item_type": "folder.workflow",
            "name": "postgresql_demo",
            "parent_laui": folders["workflow"],
            "project_laui": project_laui,
            "account_laui": account_laui,
        }
    )
    pg_demo_folder_laui = pg_demo_workflow.get("item_laui")
    print(f"[setup] Created postgresql_demo workflow folder: {pg_demo_folder_laui}")

    print("\n--- PostgreSQL Demo Tasks ---")
    await get_or_create_postgres_tasks(
        active_db,
        all_items=all_items,
        workflow_folder_laui=pg_demo_folder_laui,
        account_laui=account_laui,
        project_laui=project_laui,
    )

    # --- Sales Pipeline ---
    print("\n--- Sales Pipeline Workflow Folder ---")
    sales_workflow = await create_item(
        {
            "item_type": "folder.workflow",
            "name": "dbt_sales_reporting",
            "parent_laui": folders["workflow"],
            "project_laui": project_laui,
            "account_laui": account_laui,
        }
    )
    sales_workflow_folder_laui = sales_workflow.get("item_laui")
    print(f"[setup] Created dbt_sales_reporting workflow folder: {sales_workflow_folder_laui}")

    print("\n--- Sales Reports Folder ---")
    sales_reports_resp = await create_item(
        {
            "item_type": "folder.asset",
            "name": "sales_pipeline_reports",
            "parent_laui": folders["asset"],
            "project_laui": project_laui,
            "account_laui": account_laui,
        }
    )
    sales_reports_folder_laui = sales_reports_resp.get("item_laui")
    print(f"[setup] Created sales_pipeline_reports folder: {sales_reports_folder_laui}")

    print("\n--- Debug Reports Folder ---")
    debug_reports_resp = await create_item(
        {
            "item_type": "folder.asset",
            "name": "DebugReports",
            "parent_laui": folders["asset"],
            "project_laui": project_laui,
            "account_laui": account_laui,
        }
    )
    debug_reports_folder_laui = debug_reports_resp.get("item_laui")
    print(f"[setup] Created DebugReports folder: {debug_reports_folder_laui}")

    # Resolve Claude connection and chat LAUIs from registered items (optional — only wired if present)
    ai_connection_laui = all_items.get("connection", {}).get("anthropic/ClaudeApi")
    ai_chat_laui = all_items.get("agent", {}).get("agent/Anthropic/AnthropicAgent")
    print(f"[setup] AI connection LAUI: {ai_connection_laui} | AI chat LAUI: {ai_chat_laui}")

    print("\n--- Sales Pipeline Tasks ---")
    await get_or_create_sales_pipeline_tasks(
        active_db,
        all_items=all_items,
        workflow_folder_laui=sales_workflow_folder_laui,
        reports_folder_laui=sales_reports_folder_laui,
        account_laui=account_laui,
        project_laui=project_laui,
        debug_reports_folder_laui=debug_reports_folder_laui,
        ai_connection_laui=ai_connection_laui,
        ai_chat_laui=ai_chat_laui,
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
