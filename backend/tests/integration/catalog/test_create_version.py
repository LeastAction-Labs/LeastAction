# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse
from src.core.catalog.item.schema import Item
from src.core.catalog.item_revision.schema import ItemRevision
from src.core.db.types import MongoDatabase
from tests.integration.schema import BaseFolders, TestRequest
from tests.integration.utils import create_base_folders, execute_request

# The pytestmark is needed for running anyio tests
# Documentation: https://anyio.readthedocs.io/en/stable/testing.html#creating-asynchronous-tests
pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase):
    await test_database.items.drop()
    await test_database.links.delete_many({})
    await test_database.item_revisions.delete_many({})
    yield
    await test_database.items.drop()
    await test_database.links.drop()
    await test_database.item_revisions.delete_many({})


@pytest.fixture(autouse=True)
def base_folders_setup(client: TestClient, database_cleanup):
    base_folders = create_base_folders(client)
    yield base_folders


async def test_create_version(
    client: TestClient, test_database: MongoDatabase, base_folders_setup: BaseFolders
):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.config",
                "name": "root_config_folder",
                "parent_laui": base_folders_setup.project_folder_laui,
                "account_laui": base_folders_setup.account_folder_laui,
                "project_laui": base_folders_setup.project_folder_laui,
            },
        ),
    )

    assert response.status_code == 200
    response = CreateItemResponse(**response.json())
    root_config_folder_item_laui = response.item_laui
    item = await test_database.items.find_one({"_id": ObjectId(root_config_folder_item_laui)})
    assert item is not None
    item = Item(**item)
    assert item.name == "root_config_folder"
    assert item.item_type == "folder.config"
    assert item.parent_laui == ObjectId(base_folders_setup.project_folder_laui)
    assert item.version == 1
    assert item.laui == root_config_folder_item_laui
    assert await test_database.item_revisions.count_documents({}) == 0

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.config",
                "name": "root_config_folder",
                "parent_laui": base_folders_setup.project_folder_laui,
                "description": "this is root folder",
                "account_laui": base_folders_setup.account_folder_laui,
                "project_laui": base_folders_setup.project_folder_laui,
            },
        ),
    )

    assert response.status_code == 200
    response = CreateItemResponse(**response.json())
    root_config_folder_item_laui = response.item_laui
    item = await test_database.items.find_one({"_id": ObjectId(root_config_folder_item_laui)})
    assert item is not None
    print(item)
    item = Item(**item)
    assert item.name == "root_config_folder"
    assert item.item_type == "folder.config"
    assert item.description == "this is root folder"
    assert item.version == 2  # version incremented
    assert item.parent_laui == ObjectId(base_folders_setup.project_folder_laui)
    assert await test_database.item_revisions.count_documents({}) == 1
    item_revisions = await test_database.item_revisions.find(
        filter={"item_laui": ObjectId(root_config_folder_item_laui)}, sort=[("version", 1)]
    ).to_list(length=None)
    print(item_revisions[0])
    item_revision_1 = ItemRevision(**item_revisions[0])
    assert item_revision_1.item_laui == ObjectId(root_config_folder_item_laui)
    assert item_revision_1.name == "root_config_folder"
    assert item_revision_1.item_type == "folder.config"
    assert item_revision_1.version == 1
    assert item.parent_laui == ObjectId(base_folders_setup.project_folder_laui)

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "config",
                "name": "test_config",
                "parent_laui": root_config_folder_item_laui,
                "content": {"abc": "def"},
                "config_type": "system",
                "account_laui": base_folders_setup.account_folder_laui,
                "project_laui": base_folders_setup.project_folder_laui,
            },
        ),
    )

    assert response.status_code == 200
    response = CreateItemResponse(**response.json())
    item_laui = response.item_laui
    item = await test_database.items.find_one({"_id": ObjectId(item_laui)})
    assert item is not None
    item = Item(**item)
    assert item.name == "test_config"
    assert item.item_type == "config"
    assert item.content == {"abc": "def"}
    assert item.config_type == "system"
    assert item.parent_laui == ObjectId(root_config_folder_item_laui)
    assert item.version == 1

    assert await test_database.item_revisions.count_documents({}) == 1

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "config",
                "name": "test_config",
                "parent_laui": root_config_folder_item_laui,
                "content": {"abc": "def"},
                "config_type": "system",
                "account_laui": base_folders_setup.account_folder_laui,
                "project_laui": base_folders_setup.project_folder_laui,
            },
        ),
    )

    assert response.status_code == 200
    response = CreateItemResponse(**response.json())
    item_laui = response.item_laui

    assert await test_database.item_revisions.count_documents({}) == 1 + 1

    item = await test_database.items.find_one({"_id": ObjectId(item_laui)})
    assert item is not None
    item = Item(**item)
    assert item.name == "test_config"
    assert item.item_type == "config"
    assert item.content == {"abc": "def"}
    assert item.config_type == "system"
    assert item.parent_laui == ObjectId(root_config_folder_item_laui)
    assert item.version == 2  # version incremented

    item_revisions = await test_database.item_revisions.find(
        filter={"item_laui": ObjectId(item_laui)}, sort=[("version", 1)]
    ).to_list(length=None)
    item_revision_1 = ItemRevision(**item_revisions[0])
    assert item_revision_1.item_laui == ObjectId(item_laui)
    assert item_revision_1.name == "test_config"
    assert item_revision_1.item_type == "config"
    assert item_revision_1.parent_laui == ObjectId(root_config_folder_item_laui)
    assert item_revision_1.content == {"abc": "def"}
    assert item_revision_1.config_type == "system"
    assert item_revision_1.version == 1

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "config",
                "name": "test_config",
                "parent_laui": root_config_folder_item_laui,
                "content": {"abc": "def"},
                "config_type": "system",
                "account_laui": base_folders_setup.account_folder_laui,
                "project_laui": base_folders_setup.project_folder_laui,
            },
        ),
    )

    assert response.status_code == 200
    response = CreateItemResponse(**response.json())
    item_laui = response.item_laui

    assert await test_database.item_revisions.count_documents({}) == 1 + 2

    item = await test_database.items.find_one({"_id": ObjectId(item_laui)})
    assert item is not None
    item = Item(**item)
    assert item.name == "test_config"
    assert item.item_type == "config"
    assert item.content == {"abc": "def"}
    assert item.config_type == "system"
    assert item.parent_laui == ObjectId(root_config_folder_item_laui)
    assert item.version == 3  # version incremented
    item_revisions = await test_database.item_revisions.find(
        filter={"item_laui": ObjectId(item_laui)}, sort=[("version", 1)]
    ).to_list(length=None)
    item_revision_1 = ItemRevision(**item_revisions[0])
    assert item_revision_1.item_laui == ObjectId(item_laui)
    assert item_revision_1.name == "test_config"
    assert item_revision_1.item_type == "config"
    assert item_revision_1.content == {"abc": "def"}
    assert item_revision_1.config_type == "system"
    assert item_revision_1.version == 1
    assert item_revision_1.parent_laui == ObjectId(root_config_folder_item_laui)
    item_revision_2 = ItemRevision(**item_revisions[1])
    assert item_revision_2.item_laui == ObjectId(item_laui)
    assert item_revision_2.name == "test_config"
    assert item_revision_2.item_type == "config"
    assert item_revision_2.content == {"abc": "def"}
    assert item_revision_2.config_type == "system"
    assert item_revision_2.version == 2
    assert item_revision_2.parent_laui == ObjectId(root_config_folder_item_laui)
