# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from typing import Any

import pytest
from bson import ObjectId
from deepdiff import DeepDiff
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse
from src.core.db.types import MongoDatabase
from tests.integration.schema import TestRequest
from tests.integration.utils import create_base_folders, execute_request

pytestmark = pytest.mark.anyio


def extract_item_fields(item_dict: dict[str, Any]) -> dict[str, Any]:
    """Extract only relevant fields for assertion comparison, filtering out extra API response fields."""
    if not isinstance(item_dict, dict):
        return item_dict

    relevant_fields = {
        "name": item_dict.get("name"),
        "description": item_dict.get("description"),
        "laui": item_dict.get("laui"),
        "deleted_at": item_dict.get("deleted_at"),
        "item_type": item_dict.get("item_type"),
        "permission": item_dict.get("permission"),
        "supported_types": item_dict.get("supported_types"),
        "folder_metadata": item_dict.get("folder_metadata"),
        "parent_laui": item_dict.get("parent_laui"),
        "content": item_dict.get("content"),
    }
    return relevant_fields


def clean_response_tree(item_dict: dict[str, Any]) -> dict[str, Any]:
    """Recursively clean a response tree structure by extracting only relevant fields."""
    if not isinstance(item_dict, dict):
        return item_dict

    cleaned = {}

    if "item" in item_dict:
        cleaned["item"] = extract_item_fields(item_dict["item"])

    if "children" in item_dict:
        cleaned["children"] = [clean_response_tree(child) for child in item_dict["children"]]

    if "parents" in item_dict:
        cleaned["parents"] = [clean_response_tree(parent) for parent in item_dict["parents"]]

    return cleaned


def _create_config_folder(
    client: TestClient, name: str, parent_laui: str, account_laui: str, project_laui: str
):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.config",
                "name": name,
                "parent_laui": parent_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
            },
        ),
    )
    assert response.status_code == 200
    response = CreateItemResponse(**response.json())
    return response.item_laui


def _create_config(
    client: TestClient, name: str, parent_laui: str, account_laui: str, project_laui: str
) -> str:
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "config",
                "name": name,
                "parent_laui": parent_laui,
                "content": {"abc": "def"},
                "config_type": "system",
                "account_laui": account_laui,
                "project_laui": project_laui,
            },
        ),
    )
    assert response.status_code == 200
    response = CreateItemResponse(**response.json())
    return response.item_laui


@pytest.fixture(autouse=True)
async def setup_catalog(client: TestClient, test_database: MongoDatabase):
    """
    Structure of the catalog:
    root_config_folder
        depth1_config_folder1
            depth2_config1
        depth1_config_folder2
            depth2_config_folder1
                depth3_config1
            depth2_config2
            depth2_config3
        depth1_config_folder3
        depth1_config1
    trash
    """
    await test_database.items.drop()
    await test_database.links.delete_many({})
    base_folders = create_base_folders(client)
    root_config_folder_laui = _create_config_folder(
        client,
        "root_config_folder",
        parent_laui=base_folders.project_folder_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    depth1_config_folder1_laui = _create_config_folder(
        client,
        "depth1_config_folder1",
        parent_laui=root_config_folder_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    depth1_config_folder2_laui = _create_config_folder(
        client,
        "depth1_config_folder2",
        parent_laui=root_config_folder_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    depth1_config_folder3_laui = _create_config_folder(
        client,
        "depth1_config_folder3",
        parent_laui=root_config_folder_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    depth2_config_folder1_laui = _create_config_folder(
        client,
        "depth2_config_folder1",
        parent_laui=depth1_config_folder2_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    depth1_config1_laui = _create_config(
        client,
        "depth1_config1",
        parent_laui=root_config_folder_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    depth2_config1_laui = _create_config(
        client,
        "depth2_config1",
        parent_laui=depth1_config_folder1_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    depth2_config2_laui = _create_config(
        client,
        "depth2_config2",
        parent_laui=depth1_config_folder2_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    depth2_config3_laui = _create_config(
        client,
        "depth2_config3",
        parent_laui=depth1_config_folder2_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    depth3_config1_laui = _create_config(
        client,
        "depth3_config1",
        parent_laui=depth2_config_folder1_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    trash_laui = base_folders.trash_folder_laui
    account_folder = base_folders.account_folder_laui
    project_folder = base_folders.project_folder_laui

    name_laui_dict = {
        "root_config_folder": {"laui": root_config_folder_laui, "num_children": 4},
        "depth1_config_folder1": {"laui": depth1_config_folder1_laui, "num_children": 1},
        "depth1_config_folder2": {"laui": depth1_config_folder2_laui, "num_children": 3},
        "depth1_config_folder3": {"laui": depth1_config_folder3_laui, "num_children": 0},
        "depth2_config_folder1": {"laui": depth2_config_folder1_laui, "num_children": 1},
        "depth1_config1": {"laui": depth1_config1_laui, "num_children": 0},
        "depth2_config1": {"laui": depth2_config1_laui, "num_children": 0},
        "depth2_config2": {"laui": depth2_config2_laui, "num_children": 0},
        "depth2_config3": {"laui": depth2_config3_laui, "num_children": 0},
        "depth3_config1": {"laui": depth3_config1_laui, "num_children": 0},
        "trash": {"laui": trash_laui},
        "account_folder": {"laui": account_folder, "num_children": 2},
        "project_folder": {"laui": project_folder, "num_children": 1},
    }
    yield name_laui_dict

    await test_database.items.drop()
    await test_database.links.drop()


async def test_get_with_no_filters_returns_400_fail(client: TestClient):
    response = execute_request(
        client=client, request=TestRequest(url="/api/v1/catalog/get", method="get")
    )
    print("no_filter_test")
    print(response.json())
    assert response.status_code == 400


async def test_get_other_item_filters_passed_with_is_root_fail(
    client: TestClient, setup_catalog: dict[str, dict[str, str]]
):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={
                "is_root": True,
                "item_type": "config",
                "item_laui": setup_catalog["root_config_folder"]["laui"],
            },
        ),
    )
    assert response.status_code == 400
    print(response.json())
    assert response.json()["detail"] == {
        "error_type": "Invalid Field Combination",
        "message": "Invalid fields passed when 'is_root' is set to True.",
        "invalid_fields_passed": ["item_laui"],
        "fields_disallowed_for_root": ["item_laui", "parent_or_child"],
    }


async def test_get_root_items(client: TestClient, setup_catalog: dict[str, dict[str, str]]):
    response = execute_request(
        client=client,
        request=TestRequest(url="/api/v1/catalog/get", method="get", params={"is_root": True}),
    )
    assert response.status_code == 200
    cleaned_response_items = [clean_response_tree(item) for item in response.json()["items"]]
    expected_items = [
        {
            "item": {
                "name": "account_folder",
                "laui": setup_catalog["account_folder"]["laui"],
                "description": "",
                "deleted_at": None,
                "item_type": "folder.account",
                "permission": "own",
                "supported_types": ["folder.project", "folder.trash", "folder.users"],
                "folder_metadata": None,
                "parent_laui": None,
                "content": None,
            },
            "children": [
                {
                    "item": {
                        "name": "project_folder",
                        "laui": setup_catalog["project_folder"]["laui"],
                        "description": "",
                        "deleted_at": None,
                        "item_type": "folder.project",
                        "permission": "own",
                        "supported_types": [
                            "folder.action",
                            "folder.asset",
                            "folder.workflow",
                            "folder.operator",
                            "folder.payload",
                            "folder.connection",
                            "folder.bootstrap",
                            "folder.action",
                            "folder.config",
                            "folder.ai",
                        ],
                        "folder_metadata": None,
                        "parent_laui": setup_catalog["account_folder"]["laui"],
                        "content": None,
                    },
                    "children": [],
                    "parents": [],
                },
                {
                    "item": {
                        "name": "trash",
                        "laui": setup_catalog["trash"]["laui"],
                        "description": "",
                        "deleted_at": None,
                        "item_type": "folder.trash",
                        "permission": "own",
                        "supported_types": [
                            "task",
                            "connection",
                            "config",
                            "action",
                            "operator",
                            "payload",
                            "html_report",
                            "powerbi_report",
                            "looker_report",
                            "looker_studio_report",
                            "quicksight_report",
                            "tableau_report",
                            "table",
                            "agent",
                            "skill",
                            "usecase",
                        ],
                        "folder_metadata": None,
                        "parent_laui": setup_catalog["account_folder"]["laui"],
                        "content": None,
                    },
                    "children": [],
                    "parents": [],
                },
            ],
            "parents": [],
        }
    ]
    # Compare expected vs actual directly, completely ignoring list ordering
    diff = DeepDiff(expected_items, cleaned_response_items, ignore_order=True)

    # If they match, diff will be an empty dictionary
    assert not diff, f"Mismatched items found: {diff}"


async def test_get_root_items_depth_2(client: TestClient, setup_catalog: dict[str, dict[str, str]]):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"is_root": True, "depth": 2}
        ),
    )
    assert response.status_code == 200
    print(response.json())
    cleaned_response_items = [clean_response_tree(item) for item in response.json()["items"]]
    expected_items = [
        {
            "item": {
                "name": "account_folder",
                "laui": setup_catalog["account_folder"]["laui"],
                "description": "",
                "deleted_at": None,
                "item_type": "folder.account",
                "permission": "own",
                "supported_types": ["folder.project", "folder.trash", "folder.users"],
                "folder_metadata": None,
                "parent_laui": None,
                "content": None,
            },
            "children": [
                {
                    "item": {
                        "name": "project_folder",
                        "laui": setup_catalog["project_folder"]["laui"],
                        "description": "",
                        "deleted_at": None,
                        "item_type": "folder.project",
                        "permission": "own",
                        "supported_types": [
                            "folder.action",
                            "folder.asset",
                            "folder.workflow",
                            "folder.operator",
                            "folder.payload",
                            "folder.connection",
                            "folder.bootstrap",
                            "folder.action",
                            "folder.config",
                            "folder.ai",
                        ],
                        "folder_metadata": None,
                        "parent_laui": setup_catalog["account_folder"]["laui"],
                        "content": None,
                    },
                    "children": [
                        {
                            "item": {
                                "name": "root_config_folder",
                                "laui": setup_catalog["root_config_folder"]["laui"],
                                "description": "",
                                "deleted_at": None,
                                "item_type": "folder.config",
                                "permission": "own",
                                "supported_types": ["folder.config", "config"],
                                "folder_metadata": None,
                                "parent_laui": setup_catalog["project_folder"]["laui"],
                                "content": None,
                            },
                            "children": [],
                            "parents": [],
                        }
                    ],
                    "parents": [],
                },
                {
                    "item": {
                        "name": "trash",
                        "laui": setup_catalog["trash"]["laui"],
                        "description": "",
                        "deleted_at": None,
                        "item_type": "folder.trash",
                        "permission": "own",
                        "supported_types": [
                            "task",
                            "connection",
                            "config",
                            "action",
                            "operator",
                            "payload",
                            "html_report",
                            "powerbi_report",
                            "looker_report",
                            "looker_studio_report",
                            "quicksight_report",
                            "tableau_report",
                            "table",
                            "agent",
                            "skill",
                            "usecase",
                        ],
                        "folder_metadata": None,
                        "parent_laui": setup_catalog["account_folder"]["laui"],
                        "content": None,
                    },
                    "children": [],
                    "parents": [],
                },
            ],
            "parents": [],
        }
    ]
    diff = DeepDiff(expected_items, cleaned_response_items, ignore_order=True)
    assert not diff, f"Mismatched items found: {diff}"


async def test_only_item_laui_passed(client: TestClient, setup_catalog: dict[str, dict[str, str]]):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={"item_laui": setup_catalog["depth1_config_folder1"]["laui"]},
        ),
    )
    print(response.json())
    assert response.status_code == 200
    item = response.json()
    assert item["name"] == "depth1_config_folder1"
    assert item["laui"] == setup_catalog["depth1_config_folder1"]["laui"]
    assert item["parent_laui"] == setup_catalog["root_config_folder"]["laui"]
    assert not item["is_root"]
    assert item["item_type"] == "folder.config"
    diff = DeepDiff(
        item["supported_types"],
        ["folder.config", "config"],
        ignore_order=True,
    )
    assert not diff, f"Mismatched item found: {diff}"


async def test_non_existing_item_laui_passed_fail(client: TestClient):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": ObjectId()}
        ),
    )
    assert response.status_code == 403


async def test_case_item_laui_and_item_type_folder_passed(
    client: TestClient, setup_catalog: dict[str, dict[str, str]]
):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={
                "item_laui": setup_catalog["depth1_config_folder2"]["laui"],
                "item_type": "folder",
                "parent_or_child": "child",
            },
        ),
    )
    print(response.json())
    assert response.status_code == 200
    print(response.json()["items"])
    cleaned_response_items = [clean_response_tree(item) for item in response.json()["items"]]
    expected_items = [
        {
            "item": {
                "name": "depth2_config_folder1",
                "description": "",
                "laui": setup_catalog["depth2_config_folder1"]["laui"],
                "deleted_at": None,
                "item_type": "folder.config",
                "permission": "own",
                "supported_types": ["folder.config", "config"],
                "folder_metadata": {},
                "parent_laui": setup_catalog["depth1_config_folder2"]["laui"],
                "content": None,
            },
            "children": [],
            "parents": [],
        }
    ]
    diff = DeepDiff(expected_items, cleaned_response_items, ignore_order=True)
    assert not diff, f"Mismatched items found: {diff}"


async def test_case_item_laui_and_item_type_config_passed(
    client: TestClient, setup_catalog: dict[str, dict[str, str]]
):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={
                "item_laui": setup_catalog["depth1_config_folder2"]["laui"],
                "item_type": "config",
                "parent_or_child": "child",
            },
        ),
    )
    assert response.status_code == 200
    print(response.json()["items"])
    cleaned_response_items = [clean_response_tree(item) for item in response.json()["items"]]
    expected_items = [
        {
            "item": {
                "name": "depth2_config2",
                "description": "",
                "laui": setup_catalog["depth2_config2"]["laui"],
                "deleted_at": None,
                "item_type": "config",
                "permission": "own",
                "supported_types": ["task"],
                "folder_metadata": None,
                "content": {"abc": "def"},
                "parent_laui": setup_catalog["depth1_config_folder2"]["laui"],
            },
            "children": [],
            "parents": [],
        },
        {
            "item": {
                "name": "depth2_config3",
                "description": "",
                "laui": setup_catalog["depth2_config3"]["laui"],
                "deleted_at": None,
                "item_type": "config",
                "permission": "own",
                "supported_types": ["task"],
                "folder_metadata": None,
                "content": {"abc": "def"},
                "parent_laui": setup_catalog["depth1_config_folder2"]["laui"],
            },
            "children": [],
            "parents": [],
        },
    ]
    diff = DeepDiff(expected_items, cleaned_response_items, ignore_order=True)
    assert not diff, f"Mismatched items found: {diff}"


async def test_case_item_laui_parent_or_child_is_parent(
    client: TestClient, setup_catalog: dict[str, dict[str, str]]
):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={
                "item_laui": setup_catalog["depth3_config1"]["laui"],
                "item_type": "folder",
                "parent_or_child": "parent",
                "depth": 3,
            },
        ),
    )
    print(response.json())
    assert response.status_code == 200
    cleaned_response_items = [clean_response_tree(item) for item in response.json()["items"]]
    expected_items = [
        {
            "item": {
                "name": "depth2_config_folder1",
                "description": "",
                "laui": setup_catalog["depth2_config_folder1"]["laui"],
                "deleted_at": None,
                "item_type": "folder.config",
                "permission": "own",
                "supported_types": ["folder.config", "config"],
                "folder_metadata": {},
                "parent_laui": setup_catalog["depth1_config_folder2"]["laui"],
                "content": None,
            },
            "children": [],
            "parents": [
                {
                    "item": {
                        "name": "depth1_config_folder2",
                        "description": "",
                        "laui": setup_catalog["depth1_config_folder2"]["laui"],
                        "deleted_at": None,
                        "item_type": "folder.config",
                        "permission": "own",
                        "supported_types": ["folder.config", "config"],
                        "folder_metadata": {},
                        "parent_laui": setup_catalog["root_config_folder"]["laui"],
                        "content": None,
                    },
                    "children": [],
                    "parents": [
                        {
                            "item": {
                                "name": "root_config_folder",
                                "description": "",
                                "laui": setup_catalog["root_config_folder"]["laui"],
                                "deleted_at": None,
                                "item_type": "folder.config",
                                "permission": "own",
                                "supported_types": ["folder.config", "config"],
                                "folder_metadata": {},
                                "parent_laui": setup_catalog["project_folder"]["laui"],
                                "content": None,
                            },
                            "children": [],
                            "parents": [
                                {
                                    "item": {
                                        "name": "project_folder",
                                        "description": "",
                                        "item_type": "folder.project",
                                        "laui": setup_catalog["project_folder"]["laui"],
                                        "deleted_at": None,
                                        "permission": "own",
                                        "supported_types": [
                                            "folder.action",
                                            "folder.asset",
                                            "folder.workflow",
                                            "folder.operator",
                                            "folder.payload",
                                            "folder.connection",
                                            "folder.bootstrap",
                                            "folder.action",
                                            "folder.config",
                                            "folder.ai",
                                        ],
                                        "folder_metadata": {},
                                        "parent_laui": setup_catalog["account_folder"]["laui"],
                                        "content": None,
                                    },
                                    "children": [],
                                    "parents": [],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    ]
    diff = DeepDiff(expected_items, cleaned_response_items, ignore_order=True)
    assert not diff, f"Mismatched items found: {diff}"


async def test_is_deleted_param_check(client: TestClient, setup_catalog: dict[str, dict[str, str]]):
    parent_laui = setup_catalog["root_config_folder"]["laui"]
    item_laui = setup_catalog["depth1_config_folder1"]["laui"]

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": item_laui}
        ),
    )
    assert response.status_code == 200

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={"item_laui": item_laui, "is_deleted": False},
        ),
    )
    assert response.status_code == 200

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/delete",
            method="post",
            json={"item_laui": item_laui, "parent_laui": parent_laui},
        ),
    )
    print(response.json())

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get",
            method="get",
            params={"item_laui": item_laui, "is_deleted": False},
        ),
    )
    print(response.json())
    assert response.status_code == 404

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get", method="get", params={"item_laui": item_laui}
        ),
    )
    assert response.status_code == 200
