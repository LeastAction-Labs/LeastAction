# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import concurrent.futures

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from pydantic import __version__ as _pv

from src.core.catalog.api_request import CreateItemResponse
from src.core.catalog.item.schema import Item
from src.core.catalog.link.schema import Link
from src.core.db.types import MongoDatabase
from tests.integration.schema import TestRequest
from tests.integration.utils import create_base_folders, execute_request

PYDANTIC_MISSING_URL = f"https://errors.pydantic.dev/{'.'.join(_pv.split('.')[:2])}/v/missing"

# The pytestmark is needed for running anyio tests
# Documentation: https://anyio.readthedocs.io/en/stable/testing.html#creating-asynchronous-tests
pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase):
    await test_database.items.drop()
    await test_database.links.delete_many({})
    yield  # Test runs here
    await test_database.items.drop()
    await test_database.links.drop()


async def test_create_item_with_no_data_fail(client: TestClient):
    response = execute_request(
        client=client, request=TestRequest(url="/api/v1/catalog/create", method="post", json={})
    )

    assert response.status_code == 422

    parsed_response = response.json()

    assert parsed_response["message"] == "Invalid request parameters provided."

    detail = parsed_response["detail"]

    assert len(detail) == 1
    assert detail[0]["field"] == "body.item_type"
    assert detail[0]["error_type"] == "missing"


async def test_create_item_with_only_item_type_fail(client: TestClient):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create", method="post", json={"item_type": "operator"}
        ),
    )

    assert response.status_code == 422

    parsed_response = response.json()
    assert isinstance(parsed_response.get("detail"), list)

    detail = parsed_response["detail"]

    fields = {err.get("field") for err in detail if isinstance(err, dict)}

    assert "name" in fields
    assert "codeblock" in fields


async def test_create_item_missing_is_root_and_parent_laui_fail(
    client: TestClient, item_type: str = "operator"
):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": item_type,
                "name": "abc",
                "codeblock": {"main.py": "abc"},
                "bashblock": {"main.sh": "def"},
            },
        ),
    )
    assert response.status_code == 422
    resp_json = response.json()
    if isinstance(resp_json.get("detail"), dict):
        assert resp_json["detail"].get("msg") == "parent_laui must be present for non root item"


async def test_create_item_is_root_false_and_missing_parent_laui_fail(
    client: TestClient, item_type: str = "operator"
):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": item_type,
                "name": "abc",
                "codeblock": {"main.py": "abc"},
                "bashblock": {"main.sh": "def"},
                "is_root": False,
            },
        ),
    )
    assert response.status_code == 422
    resp_json = response.json()
    if isinstance(resp_json.get("detail"), dict):
        assert resp_json["detail"].get("msg") == "parent_laui must be present for non root item"


async def test_create_item_is_root_true_and_valid_parent_laui_fail(
    client: TestClient, item_type: str = "operator"
):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": item_type,
                "name": "abc",
                "codeblock": {"main.py": "abc"},
                "bashblock": {"main.sh": "def"},
                "is_root": True,
                "parent_laui": str(ObjectId()),
            },
        ),
    )
    assert response.status_code == 422
    resp_json = response.json()
    if isinstance(resp_json.get("detail"), dict):
        assert resp_json["detail"].get("msg") == "parent_laui must be none for root item"


async def test_create_valid_root_item(client: TestClient, test_database: MongoDatabase):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={"item_type": "folder.account", "name": "root_account_folder", "is_root": True},
        ),
    )
    assert response.status_code == 200
    response = CreateItemResponse(**response.json())
    item = await test_database.items.find_one({"_id": ObjectId(response.item_laui)})
    assert item is not None
    item = Item(**item)
    assert item.name == "root_account_folder"
    assert item.item_type == "folder.account"
    assert item.is_root == True


async def test_create_root_item_with_invalid_item_type(
    client: TestClient, test_database: MongoDatabase
):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={"item_type": "folder.project", "name": "root_project_folder", "is_root": True},
        ),
    )
    assert response.status_code == 422


async def test_create_invalid_number_of_root_items(
    client: TestClient, test_database: MongoDatabase
):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={"item_type": "folder.account", "name": "root_account_folder", "is_root": True},
        ),
    )
    assert response.status_code == 200
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={"item_type": "folder.account", "name": "root_account_folder_2", "is_root": True},
        ),
    )
    assert response.status_code == 422


async def test_create_item_with_version_compatibility_wildcard(
    client: TestClient, test_database: MongoDatabase
):
    base_folders = create_base_folders(client)
    ai_folder_response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.ai",
                "name": "ai_folder",
                "parent_laui": base_folders.project_folder_laui,
                "account_laui": base_folders.account_folder_laui,
                "project_laui": base_folders.project_folder_laui,
            },
        ),
    )
    assert ai_folder_response.status_code == 200
    ai_folder_laui = CreateItemResponse(**ai_folder_response.json()).item_laui
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "usecase",
                "name": "vc_wildcard.usecase",
                "parent_laui": ai_folder_laui,
                "version_compatibility": {"core": ["0.*"]},
                "account_laui": base_folders.account_folder_laui,
                "project_laui": base_folders.project_folder_laui,
            },
        ),
    )
    assert response.status_code == 200


async def test_create_item_with_version_compatibility_range(
    client: TestClient, test_database: MongoDatabase
):
    base_folders = create_base_folders(client)
    ai_folder_response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.ai",
                "name": "ai_folder",
                "parent_laui": base_folders.project_folder_laui,
                "account_laui": base_folders.account_folder_laui,
                "project_laui": base_folders.project_folder_laui,
            },
        ),
    )
    assert ai_folder_response.status_code == 200
    ai_folder_laui = CreateItemResponse(**ai_folder_response.json()).item_laui
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "usecase",
                "name": "vc_range.usecase",
                "parent_laui": ai_folder_laui,
                "version_compatibility": {"core": [">=0.0.0", "<1.0.0"]},
                "account_laui": base_folders.account_folder_laui,
                "project_laui": base_folders.project_folder_laui,
            },
        ),
    )
    assert response.status_code == 200


async def test_create_valid_item_with_parent(client: TestClient, test_database: MongoDatabase):
    base_folders = create_base_folders(client)
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.config",
                "name": "root_config_folder",
                "parent_laui": base_folders.project_folder_laui,
                "account_laui": base_folders.account_folder_laui,
                "project_laui": base_folders.project_folder_laui,
            },
        ),
    )
    print(response.json())
    assert response.status_code == 200
    response = CreateItemResponse(**response.json())
    parent_item_laui = response.item_laui

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "config",
                "name": "config_item",
                "parent_laui": parent_item_laui,
                "content": {"abc": "def"},
                "config_type": "system",
                "account_laui": base_folders.account_folder_laui,
                "project_laui": base_folders.project_folder_laui,
            },
        ),
    )
    print(response.json())
    assert response.status_code == 200
    response = CreateItemResponse(**response.json())
    child_item_laui = response.item_laui
    child_item = await test_database.items.find_one({"_id": ObjectId(child_item_laui)})
    assert child_item is not None
    child_item = Item(**child_item)
    assert child_item.name == "config_item"
    assert child_item.item_type == "config"
    assert child_item.content == {"abc": "def"}
    assert child_item.config_type == "system"

    parent_child_link = await test_database.links.find_one(
        {"child_laui": ObjectId(child_item_laui)}
    )
    assert parent_child_link is not None
    parent_child_link = Link(**parent_child_link)
    assert parent_child_link.child_laui == ObjectId(child_item_laui)
    assert parent_child_link.parent_laui == ObjectId(parent_item_laui)
    assert parent_child_link.true_parent


# create 2 items , send request at once
async def test_create_2_items(client: TestClient, test_database: MongoDatabase):
    base_folders = create_base_folders(client)
    request_1 = TestRequest(
        url="/api/v1/catalog/create",
        method="post",
        json={
            "item_type": "folder.workflow",
            "name": "workflow_folder",
            "parent_laui": base_folders.project_folder_laui,
            "project_laui": base_folders.project_folder_laui,
            "account_laui": base_folders.account_folder_laui,
        },
    )

    request_2 = TestRequest(
        url="/api/v1/catalog/create",
        method="post",
        json={
            "item_type": "folder.workflow",
            "name": "workflow_folder",
            "parent_laui": base_folders.project_folder_laui,
            "project_laui": base_folders.project_folder_laui,
            "account_laui": base_folders.account_folder_laui,
        },
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_1 = executor.submit(execute_request, client=client, request=request_1)
        future_2 = executor.submit(execute_request, client=client, request=request_2)

        response_1 = future_1.result()
        response_2 = future_2.result()
    assert response_1.status_code == 200
    assert response_2.status_code == 200
    n = await test_database.items.count_documents({"item_type": "folder.workflow"})
    assert n == 1
