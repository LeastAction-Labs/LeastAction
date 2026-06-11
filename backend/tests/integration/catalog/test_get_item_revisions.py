# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse, GetItemRevisionsResponse
from src.core.db.types import MongoDatabase
from tests.integration.schema import TestRequest
from tests.integration.utils import create_base_folders, execute_request

pytestmark = pytest.mark.anyio


async def _create_config_folder(
    client: TestClient,
    name: str,
    parent_laui: str,
    account_laui: str,
    project_laui: str,
    description: str = "",
):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "item_type": "folder.config",
                "name": name,
                "description": description,
                "parent_laui": parent_laui,
                "account_laui": account_laui,
                "project_laui": project_laui,
            },
        ),
    )
    print(response.json())
    assert response.status_code == 200
    response = CreateItemResponse(**response.json())
    return response.item_laui


async def _create_config(
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
    await test_database.items.drop()
    await test_database.links.delete_many({})
    await test_database.item_revisions.delete_many({})
    base_folders = create_base_folders(client)
    root_config_folder_laui = await _create_config_folder(
        client=client,
        name="root_config_folder",
        parent_laui=base_folders.project_folder_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    await _create_config_folder(
        client=client,
        name="root_config_folder",
        description="1",
        parent_laui=base_folders.project_folder_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    await _create_config_folder(
        client=client,
        name="root_config_folder",
        description="2",
        parent_laui=base_folders.project_folder_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    await _create_config_folder(
        client=client,
        name="root_config_folder",
        description="3",
        parent_laui=base_folders.project_folder_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    config_item_laui = await _create_config(
        client=client,
        name="test_config",
        parent_laui=root_config_folder_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    await _create_config(
        client=client,
        name="test_config",
        parent_laui=root_config_folder_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    await _create_config(
        client=client,
        name="test_config",
        parent_laui=root_config_folder_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    await _create_config(
        client=client,
        name="test_config",
        parent_laui=root_config_folder_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    config_item2_laui = await _create_config(
        client=client,
        name="test_config2",
        parent_laui=root_config_folder_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    laui_dict = {
        "root_config_folder": {"laui": root_config_folder_laui, "num_revisions": 3},
        "config_item": {"laui": config_item_laui, "num_revisions": 3},
        "config_item2": {"laui": config_item2_laui, "num_revisions": 0},
    }

    yield laui_dict
    await test_database.items.drop()
    await test_database.item_revisions.delete_many({})
    await test_database.links.drop()


async def test_get_with_no_item_laui_422_fail(client: TestClient):
    response = execute_request(
        client=client, request=TestRequest(url="/api/v1/catalog/get/item_revisions", method="get")
    )
    assert response.status_code == 422
    response = execute_request(
        client=client,
        request=TestRequest(url="/api/v1/catalog/get/item_revisions?version=2", method="get"),
    )
    assert response.status_code == 422


async def test_get_with_invalid_item_laui_fail(client: TestClient):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get/item_revisions", method="get", params={"item_laui": "abce"}
        ),
    )
    assert response.status_code == 422
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get/item_revisions", method="get", params={"item_laui": 124}
        ),
    )
    assert response.status_code == 422


async def test_get_with_valid_but_non_exisiting_item_laui_fail(
    client: TestClient, setup_catalog: dict[str, dict[str, str]]
):
    item_laui = ObjectId()
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get/item_revisions", method="get", params={"item_laui": item_laui}
        ),
    )
    assert response.status_code == 404


async def test_get_item_revisions_by_laui(
    client: TestClient, setup_catalog: dict[str, dict[str, str]]
):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get/item_revisions",
            method="get",
            params={"item_laui": setup_catalog["root_config_folder"]["laui"]},
        ),
    )
    print(response.json())
    assert response.status_code == 200
    item_revisions = GetItemRevisionsResponse(**response.json()).item_revisions
    assert len(item_revisions) == setup_catalog["root_config_folder"]["num_revisions"]
    for item_revision in item_revisions:
        assert item_revision.item_laui == ObjectId(setup_catalog["root_config_folder"]["laui"])


async def test_get_item_revisions_for_item_laui_with_no_versions(
    client: TestClient, setup_catalog: dict[str, dict[str, str]]
):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get/item_revisions",
            method="get",
            params={"item_laui": setup_catalog["config_item2"]["laui"]},
        ),
    )
    assert response.status_code == 200
    response = GetItemRevisionsResponse(**response.json())
    assert response.item_revision is None
    assert response.item_revisions == []


# from here item_laui will be valid and that item will have versions


async def test_get_item_revision_for_invalid_version_fail(
    client: TestClient, setup_catalog: dict[str, dict[str, str]]
):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get/item_revisions",
            method="get",
            params={"item_laui": setup_catalog["config_item"]["laui"], "version": "abc"},
        ),
    )
    assert response.status_code == 422


async def test_get_item_revision_for_non_existing_version_fail(
    client: TestClient, setup_catalog: dict[str, dict[str, str]]
):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get/item_revisions",
            method="get",
            params={"item_laui": setup_catalog["config_item"]["laui"], "version": 10},
        ),
    )
    assert response.status_code == 404


async def test_get_item_revision(client: TestClient, setup_catalog: dict[str, dict[str, str]]):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get/item_revisions",
            method="get",
            params={"item_laui": setup_catalog["config_item"]["laui"], "version": 1},
        ),
    )
    assert response.status_code == 200
    item_revision = GetItemRevisionsResponse(**response.json()).item_revision
    assert item_revision.item_laui == ObjectId(setup_catalog["config_item"]["laui"])
    assert item_revision.version == 1
