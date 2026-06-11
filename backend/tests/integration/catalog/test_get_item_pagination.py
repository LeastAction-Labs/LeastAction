# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.

import random
import string

import pytest
from fastapi.testclient import TestClient
from pydantic_mongo import PydanticObjectId

from src.core.catalog.api_request import CreateItemResponse
from src.core.db.types import MongoDatabase
from tests.integration.schema import TestRequest
from tests.integration.utils import create_base_folders, execute_request

pytestmark = pytest.mark.anyio


async def _create_config_folder(client: TestClient, name: str, parent_laui: str):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={"item_type": "folder.config", "name": name, "parent_laui": parent_laui},
        ),
    )
    assert response.status_code == 200
    response = CreateItemResponse(**response.json())
    return response.item_laui


async def _create_config(client: TestClient, name: str, parent_laui: str) -> str:
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
                "config_type": "connection",
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
            1000 config items

    Args:
        client (TestClient): _description_
        test_database (MongoDatabase): _description_
    """
    await test_database.items.drop()
    await test_database.links.delete_many({})
    base_folders = create_base_folders(client)
    root_config_folder_laui = await _create_config_folder(
        client=client, name="root_config_folder", parent_laui=base_folders.project_folder_laui
    )
    depth1_config_folder1_laui = await _create_config_folder(
        client=client, name="depth1_config_folder1", parent_laui=root_config_folder_laui
    )
    item_lauis = await populate_config_folder(client=client, parent_laui=depth1_config_folder1_laui)
    yield {"config_folder_laui": depth1_config_folder1_laui, "item_lauis": item_lauis}
    await test_database.items.drop()
    await test_database.links.drop()


async def test_pagination(client: TestClient, setup_catalog: dict[str, any]):
    # limit is 10 by default
    for i in range(100):
        response = execute_request(
            client=client,
            request=TestRequest(
                url="/api/v1/catalog/get",
                method="get",
                params={
                    "item_laui": setup_catalog["config_folder_laui"],
                    "item_type": "config",
                    "page": i + 1,
                    "parent_or_child": "child",
                },
            ),
        )
        parsed_response = response.json()
        items = parsed_response["items"]
        assert len(items) == 10
        expected_item_lauis = setup_catalog["item_lauis"][i * 10 : (i + 1) * 10]
        for index, item in enumerate(items):
            assert item["item"]["laui"] == expected_item_lauis[index]
        pagination = parsed_response["pagination"]
        assert pagination["current_page"] == i + 1
        assert pagination["per_page"] == 10
        assert pagination["has_next"] == (i != 99)


async def populate_config_folder(client: TestClient, parent_laui: PydanticObjectId):
    length = 10
    chars = string.ascii_letters + string.digits
    item_lauis = []
    for i in range(1000):
        item_lauis.append(
            await _create_config(
                client=client,
                name="".join(random.choice(chars) for _ in range(length)),
                parent_laui=parent_laui,
            )
        )
    return item_lauis
