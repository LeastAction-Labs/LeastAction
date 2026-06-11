# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from typing import Any

from src.core.catalog.api_request import BaseCreateItemRequest
from src.core.catalog.orchestrator import ItemOrchestrator

# (folder_name, item_type) pairs – mirrors get_or_create_organizational_folders in setup.py
FOLDER_STRUCTURE: list[tuple] = [
    ("action", "folder.action"),
    ("ai", "folder.ai"),
    ("assets", "folder.asset"),
    ("config", "folder.config"),
    ("connection", "folder.connection"),
    ("operator", "folder.operator"),
    ("payload", "folder.payload"),
    ("workflow", "folder.workflow"),
]


async def bootstrap_project_structure(
    project_laui: str,
    item_orchestrator: ItemOrchestrator,
) -> list[dict[str, Any]]:
    """
    Creates the standard folder structure under a project.

    Args:
        project_laui:       LAUI of the parent project (folder.project).
        item_orchestrator:  Initialised ItemOrchestrator (from request.app.state).

    Returns:
        List of dicts: [{"name": ..., "item_type": ..., "laui": ...}, ...]
    """
    account_laui = str(await item_orchestrator.catalog_service.item_repo.get_account_laui())

    created: list[dict[str, Any]] = []

    for folder_name, folder_item_type in FOLDER_STRUCTURE:
        request = BaseCreateItemRequest(
            item_type=folder_item_type,
            name=folder_name,
            parent_laui=project_laui,
            project_laui=project_laui,
            account_laui=account_laui,
        )

        response = await item_orchestrator.create_item(request)
        folder_laui = response.item_laui

        created.append(
            {
                "name": folder_name,
                "item_type": folder_item_type,
                "laui": folder_laui,
            }
        )

    return created
