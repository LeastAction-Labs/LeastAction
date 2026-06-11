# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from pydantic_mongo import PydanticObjectId

from src.core.catalog.api_request import CreateItemResponse, CreateLinkResponse
from src.core.catalog.link.schema import Link
from src.core.db.types import MongoDatabase
from tests.integration.schema import TestRequest
from tests.integration.utils import create_base_folders, execute_request

pytestmark = pytest.mark.anyio


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
                "config_type": "connection",
                "account_laui": account_laui,
                "project_laui": project_laui,
            },
        ),
    )
    assert response.status_code == 200
    response = CreateItemResponse(**response.json())
    return response.item_laui


def _create_soft_link(client: TestClient, parent_laui: str, child_laui: str):
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create/link",
            method="post",
            json={"parent_laui": parent_laui, "child_laui": child_laui},
        ),
    )
    print(response.json())
    assert response.status_code == 200
    response = CreateLinkResponse(**response.json())
    return response.link_laui


async def _children_graph_lookup(test_database: MongoDatabase, item_laui: ObjectId) -> list[Link]:

    pipeline = [
        {"$match": {"parent_laui": item_laui}},
        {
            "$graphLookup": {
                "from": "links",
                "startWith": "$child_laui",
                "connectFromField": "child_laui",
                "connectToField": "parent_laui",
                "as": "children",
            }
        },
    ]

    pipeline_output = await (await test_database.links.aggregate(pipeline=pipeline)).to_list(
        length=None
    )
    if pipeline_output:
        links: list[Link] = []
        for link in pipeline_output:
            links.append(Link(**link))
            children_links = link["children"]
            for link in children_links:
                links.append(Link(**link))
        return links
    return []


@pytest.fixture(autouse=True)
async def setup_catalog(client: TestClient, test_database: MongoDatabase):
    """
    Structure of the catalog:
    root_config_folder
        depth1_config_folder1
            depth2_config1
            depth3_config1 [non true child] [soft link 1]
        depth1_config_folder2
            depth1_config1 [non true child] [soft link 2]
            depth2_config_folder1
                depth1_config1 [non true child] [soft link 3]
                depth3_config1
            depth2_config2
            depth2_config3
        depth1_config_folder3
        depth1_config1

    Args:
        client (TestClient): _description_
        test_database (MongoDatabase): _description_
    """
    await test_database.items.drop()
    await test_database.item_revisions.delete_many({})
    await test_database.links.delete_many({})
    base_folders = create_base_folders(client=client)
    root_config_folder_laui = _create_config_folder(
        client=client,
        name="root_config_folder",
        parent_laui=base_folders.project_folder_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    depth1_config_folder1_laui = _create_config_folder(
        client=client,
        name="depth1_config_folder1",
        parent_laui=root_config_folder_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    depth1_config_folder2_laui = _create_config_folder(
        client=client,
        name="depth1_config_folder2",
        parent_laui=root_config_folder_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    depth1_config_folder3_laui = _create_config_folder(
        client=client,
        name="depth1_config_folder3",
        parent_laui=root_config_folder_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    depth2_config_folder1_laui = _create_config_folder(
        client=client,
        name="depth2_config_folder1",
        parent_laui=depth1_config_folder2_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    depth1_config1_laui = _create_config(
        client=client,
        name="depth1_config1",
        parent_laui=root_config_folder_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    depth2_config1_laui = _create_config(
        client=client,
        name="depth2_config1",
        parent_laui=depth1_config_folder1_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    depth2_config2_laui = _create_config(
        client=client,
        name="depth2_config2",
        parent_laui=depth1_config_folder2_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    depth2_config3_laui = _create_config(
        client=client,
        name="depth2_config3",
        parent_laui=depth1_config_folder2_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    depth3_config1_laui = _create_config(
        client=client,
        name="depth3_config1",
        parent_laui=depth2_config_folder1_laui,
        account_laui=base_folders.account_folder_laui,
        project_laui=base_folders.project_folder_laui,
    )
    trash_laui = base_folders.trash_folder_laui
    soft_link1_laui = _create_soft_link(
        client=client, parent_laui=depth1_config_folder1_laui, child_laui=depth3_config1_laui
    )
    soft_link2_laui = _create_soft_link(
        client=client, parent_laui=depth1_config_folder2_laui, child_laui=depth1_config1_laui
    )
    soft_link3_laui = _create_soft_link(
        client=client, parent_laui=depth2_config_folder1_laui, child_laui=depth1_config1_laui
    )

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
        "soft_link1": {"laui": soft_link1_laui},
        "soft_link2": {"laui": soft_link2_laui},
        "soft_link3": {"laui": soft_link3_laui},
        "trash": {"laui": trash_laui},
    }
    yield name_laui_dict
    await test_database.items.drop()
    await test_database.links.drop()


async def test_delete_non_existing_parent_laui_fail(
    client: TestClient, setup_catalog: dict[str, dict[str, any]]
):
    # "Non existing parent_laui passed"
    object_laui = ObjectId()
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/delete",
            method="post",
            json={
                "item_laui": setup_catalog["depth1_config1"]["laui"],
                "parent_laui": str(object_laui),
            },
        ),
    )
    print(response.json())
    assert response.status_code == 404


async def test_delete_config_item(
    client: TestClient, test_database: MongoDatabase, setup_catalog: dict[str, dict[str, any]]
):
    item_laui = ObjectId(setup_catalog["depth1_config1"]["laui"])
    parent_laui = ObjectId(setup_catalog["root_config_folder"]["laui"])
    trash_laui = ObjectId(setup_catalog["trash"]["laui"])

    item = await test_database.items.find_one({"_id": item_laui})
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/delete",
            method="post",
            json={"parent_laui": str(parent_laui), "item_laui": str(item_laui)},
        ),
    )
    assert response.status_code == 200

    # verify item got updated
    item = await test_database.items.find_one({"_id": item_laui})
    assert item != None
    assert item["deleted_at"] != None

    # verify link between item_laui and trash folder laui got created
    links = await test_database.links.find(
        {"parent_laui": trash_laui, "child_laui": item_laui}
    ).to_list(length=None)
    assert len(links) == 1
    assert links[0]["true_parent"] == True
    assert links[0]["child_type"] == "config"
    assert links[0]["parent_type"] == "folder.trash"


async def test_delete_config_folder(
    client: TestClient, test_database: MongoDatabase, setup_catalog: dict[str, dict[str, any]]
):
    item_laui = ObjectId(setup_catalog["depth1_config_folder2"]["laui"])
    parent_laui = ObjectId(setup_catalog["root_config_folder"]["laui"])
    trash_laui = ObjectId(setup_catalog["trash"]["laui"])

    links_before = await _children_graph_lookup(test_database=test_database, item_laui=item_laui)

    soft_links_before = [link for link in links_before if link.true_parent == False]
    hard_links_before = [link for link in links_before if link.true_parent == True]

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/delete",
            method="post",
            json={"parent_laui": str(parent_laui), "item_laui": str(item_laui)},
        ),
    )

    assert response.status_code == 200

    item = await test_database.items.find_one({"_id": item_laui})
    assert item != None
    assert item["deleted_at"] != None

    link = await test_database.links.find_one({"parent_laui": trash_laui, "child_laui": item_laui})
    assert link["true_parent"] == True
    assert link["child_type"] == "folder.config"
    assert link["parent_type"] == "folder.trash"

    links_after = await _children_graph_lookup(test_database=test_database, item_laui=item_laui)

    soft_links_after = [link for link in links_after if link.true_parent == False]
    hard_links_after = [link for link in links_after if link.true_parent == True]

    assert len(soft_links_after) == len(soft_links_before)  # all soft links untouched
    assert len(hard_links_after) == len(hard_links_before)  # hard links untouched

    hard_children_item_lauis = [link.child_laui for link in hard_links_after]

    # check all hard children got updated
    hard_children_items = await test_database.items.find(
        {"_id": {"$in": hard_children_item_lauis}}
    ).to_list(length=None)
    for hard_child_item in hard_children_items:
        assert hard_child_item["deleted_at"] != None

    # hard delete the item
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/delete",
            method="post",
            json={"parent_laui": str(trash_laui), "item_laui": str(item_laui)},
        ),
    )

    assert response.status_code == 200

    links_after_hard_delete = await _children_graph_lookup(
        item_laui=item_laui, test_database=test_database
    )
    items_lauis_to_delete = hard_children_item_lauis + [PydanticObjectId(item_laui)]
    links_associated_with_hard_children = await test_database.links.find(
        {"child_laui": {"$in": items_lauis_to_delete}}
    ).to_list(length=None)
    assert len(links_associated_with_hard_children) == 0
    assert len(links_after_hard_delete) == 0
    items = await test_database.items.find({"_id": {"$in": items_lauis_to_delete}}).to_list(
        length=None
    )
    assert len(items) == 0


async def test_delete_soft_link(
    client: TestClient, test_database: MongoDatabase, setup_catalog: dict[str, dict[str, any]]
):
    item_laui = setup_catalog["depth3_config1"]["laui"]
    parent_laui = setup_catalog["depth1_config_folder1"]["laui"]
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/delete",
            method="post",
            json={"parent_laui": str(parent_laui), "item_laui": str(item_laui)},
        ),
    )
    assert response.status_code == 200
    soft_link1_laui = setup_catalog["soft_link1"]["laui"]
    soft_link = await test_database.links.find_one({"_id": soft_link1_laui})
    assert soft_link == None


async def test_multiple_soft_delete_fail(
    client: TestClient, test_database: MongoDatabase, setup_catalog: dict[str, dict[str, any]]
):
    item_laui = ObjectId(setup_catalog["depth1_config1"]["laui"])
    parent_laui = ObjectId(setup_catalog["root_config_folder"]["laui"])
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/delete",
            method="post",
            json={"parent_laui": str(parent_laui), "item_laui": str(item_laui)},
        ),
    )
    assert response.status_code == 200
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/delete",
            method="post",
            json={"parent_laui": str(parent_laui), "item_laui": str(item_laui)},
        ),
    )
    assert response.status_code == 404
