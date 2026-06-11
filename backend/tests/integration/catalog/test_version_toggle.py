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
async def setup_base_folders(client: TestClient, database_cleanup):
    base_folders = create_base_folders(client)
    yield base_folders


async def test_create_version(
    client: TestClient, test_database: MongoDatabase, setup_base_folders: BaseFolders
):
    response = execute_request(
        client=client,
        request=TestRequest(
            method="post",
            url="/api/v1/catalog/create",
            json={
                "item_type": "folder.connection",
                "name": "root_connection_folder",
                "parent_laui": setup_base_folders.project_folder_laui,
                "account_laui": setup_base_folders.account_folder_laui,
                "project_laui": setup_base_folders.project_folder_laui,
            },
        ),
    )
    assert response.status_code == 200
    response = CreateItemResponse(**response.json())
    root_connection_folder_laui = response.item_laui

    response = execute_request(
        client=client,
        request=TestRequest(
            method="post",
            url="/api/v1/catalog/create",
            json={
                "item_type": "connection",
                "name": "connection_1",
                "parent_laui": root_connection_folder_laui,
                "max_parallelism": 10,
                "content": {"type": "content_1"},
                "sort_order": {"priority": "asc"},
                "account_laui": setup_base_folders.account_folder_laui,
                "project_laui": setup_base_folders.project_folder_laui,
            },
        ),
    )
    print(response.json())
    assert response.status_code == 200
    response = CreateItemResponse(**response.json())
    connection_item_laui = response.item_laui
    item = await test_database.items.find_one({"_id": ObjectId(connection_item_laui)})
    assert item is not None
    item = Item(**item)
    assert item.laui == connection_item_laui
    assert item.name == "connection_1"
    assert item.item_type == "connection"
    assert item.version == 1
    assert item.max_parallelism == 10
    assert item.current_parallelism == 0
    assert item.content == {"type": "content_1"}
    assert item.parent_laui == ObjectId(root_connection_folder_laui)
    assert await test_database.item_revisions.count_documents({}) == 0

    response = execute_request(
        client=client,
        request=TestRequest(
            method="post",
            url="/api/v1/catalog/create",
            json={
                "item_type": "connection",
                "name": "connection_1",
                "parent_laui": root_connection_folder_laui,
                "max_parallelism": 11,
                "content": {"type": "content_1"},
                "sort_dict": {"priority": "asc"},
                "account_laui": setup_base_folders.account_folder_laui,
                "project_laui": setup_base_folders.project_folder_laui,
            },
        ),
    )

    assert response.status_code == 200
    response = CreateItemResponse(**response.json())
    connection_item_laui = response.item_laui
    item = await test_database.items.find_one({"_id": ObjectId(connection_item_laui)})
    assert item is not None
    item = Item(**item)
    assert item.laui == connection_item_laui
    assert item.name == "connection_1"
    assert item.item_type == "connection"
    assert (
        item.version == 1
    )  # not updated , because none of the updated fields belongs to the version_fields in connection.json
    assert item.max_parallelism == 11  # updated
    assert item.current_parallelism == 0
    assert item.content == {"type": "content_1"}
    assert item.parent_laui == ObjectId(root_connection_folder_laui)

    assert (
        await test_database.item_revisions.count_documents({}) == 0
    )  # no version created so no item_revision found

    response = execute_request(
        client=client,
        request=TestRequest(
            method="post",
            url="/api/v1/catalog/create",
            json={
                "item_type": "connection",
                "name": "connection_1",
                "parent_laui": root_connection_folder_laui,
                "max_parallelism": 12,  # updated
                "content": {"type": "content_2"},  # field updated
                "account_laui": setup_base_folders.account_folder_laui,
                "project_laui": setup_base_folders.project_folder_laui,
            },
        ),
    )

    assert response.status_code == 200
    response = CreateItemResponse(**response.json())
    connection_item_laui = response.item_laui
    item = await test_database.items.find_one({"_id": ObjectId(connection_item_laui)})
    assert item is not None
    item = Item(**item)
    assert item.laui == connection_item_laui
    assert item.name == "connection_1"
    assert item.item_type == "connection"
    assert (
        item.version == 2
    )  # updated , because at least one of the updated fields belongs to the version_fields in connection.json
    assert item.max_parallelism == 12
    assert item.current_parallelism == 0  # updated
    assert item.content == {"type": "content_2"}  # updated
    assert item.parent_laui == ObjectId(root_connection_folder_laui)
    item_revisions = await test_database.item_revisions.find(
        {"item_laui": ObjectId(connection_item_laui)}, sort=[("version", 1)]
    ).to_list(length=None)
    assert len(item_revisions) == 1  # item_revision found
    item_revision_1 = ItemRevision(**item_revisions[0])
    assert item_revision_1.item_laui == ObjectId(connection_item_laui)
    assert item_revision_1.name == "connection_1"
    assert item_revision_1.item_type == "connection"
    assert item_revision_1.version == 1
    assert item_revision_1.max_parallelism == 11
    assert item_revision_1.current_parallelism == 0
    assert item_revision_1.content == {"type": "content_1"}
    assert item_revision_1.parent_laui == ObjectId(root_connection_folder_laui)
