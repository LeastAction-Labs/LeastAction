# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio
import time
from os import pardir

import pytest
from fastapi.testclient import TestClient
from pydantic_mongo import PydanticObjectId

from src.core.catalog.api_request import CreateItemResponse
from src.core.db.types import MongoDatabase
from src.core.ee.iam.session.service import SessionService
from src.core.ee.iam.user.repo import UserRepository
from src.core.ee.iam.user.schema import CreateUser, UserType
from src.core.ee.iam.user.service import UserService
from src.core.ee.license.repo import LicenseRepository
from src.core.ee.license.schema import LicenseClaims, LicenseTier, LicenseUploadRequest
from src.core.ee.license.service import LicenseService
from tests.integration.schema import TestRequest
from tests.integration.utils import create_base_folders, execute_request, get_session_service

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
        "root_config_folder": {
            "laui": root_config_folder_laui,
            "item_type": "folder.config",
            "num_children": 4,
        },
        "depth1_config_folder1": {
            "laui": depth1_config_folder1_laui,
            "item_type": "folder.config",
            "num_children": 1,
        },
        "depth1_config_folder2": {
            "laui": depth1_config_folder2_laui,
            "item_type": "folder.config",
            "num_children": 3,
        },
        "depth1_config_folder3": {
            "laui": depth1_config_folder3_laui,
            "item_type": "folder.config",
            "num_children": 0,
        },
        "depth2_config_folder1": {
            "laui": depth2_config_folder1_laui,
            "item_type": "folder.config",
            "num_children": 1,
        },
        "depth1_config1": {"laui": depth1_config1_laui, "item_type": "config", "num_children": 0},
        "depth2_config1": {"laui": depth2_config1_laui, "item_type": "config", "num_children": 0},
        "depth2_config2": {"laui": depth2_config2_laui, "item_type": "config", "num_children": 0},
        "depth2_config3": {"laui": depth2_config3_laui, "item_type": "config", "num_children": 0},
        "depth3_config1": {"laui": depth3_config1_laui, "item_type": "config", "num_children": 0},
        "trash": {
            "laui": trash_laui,
            "item_type": "folder.trash",
        },
        "account_folder": {
            "laui": account_folder,
            "item_type": "folder.account",
            "num_children": 2,
        },
        "project_folder": {
            "laui": project_folder,
            "item_type": "folder.project",
            "num_children": 1,
        },
    }
    yield name_laui_dict

    await test_database.items.drop()
    await test_database.links.drop()


# create root user , test users and assign license to test users and return a dict mapping username -> laui and token
@pytest.fixture(autouse=True)
async def setup_users(client: TestClient, test_database: MongoDatabase):
    license_repo = LicenseRepository(test_database)
    license_service = LicenseService(license_repo)
    user_service = UserService(
        user_repo=UserRepository(test_database), license_service=license_service
    )
    session_service = get_session_service()

    # create root user
    root_user_email = "root_user@gmail.com"
    root_user_username = "root_user"
    root_user_password = "password"
    try:
        root_user = await user_service.get_user_by_email(root_user_email)
        if root_user.user_type != "root":
            await test_database["users"].update_one(
                {"_id": PydanticObjectId(root_user.laui)}, {"$set": {"user_type": "root"}}
            )
    except Exception:
        await user_service.create_user(
            user=CreateUser(
                username=root_user_username,
                email=root_user_email,
                password=root_user_password,
                user_type=UserType.ROOT,
            )
        )
        root_user = await user_service.get_user_by_email(root_user_email)

    users = {
        root_user_username: {
            "token": session_service.generate_access_token(root_user),
            "laui": PydanticObjectId(root_user.laui),
        }
    }

    license_upload_body = _get_license_id_and_public_key(root_user_laui=root_user.laui)
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/admin/license/upload", method="post", json=license_upload_body.model_dump()
        ),
    )
    assert response.status_code == 200
    license_laui = response.json()["license_laui"]

    test_users = ["test_user1", "test_user2", "test_user3", "test_user4", "test_user5"]

    for test_user in test_users:
        test_user_email = f"{test_user}@gmail.com"
        try:
            user = await user_service.get_user_by_email(test_user_email)
        except Exception as e:
            print(e)
            response = execute_request(
                client=client,
                request=TestRequest(
                    url="/api/v1/admin/user/create",
                    method="post",
                    json={"username": test_user, "email": test_user_email},
                ),
            )
            assert response.status_code == 200
            user = await user_service.get_user_by_email(test_user_email)
        users[test_user] = {
            "laui": user.laui,
            "token": session_service.generate_access_token(user=user),
        }

    test_user_lauis = [users[test_user]["laui"] for test_user in test_users]

    # assign licenses to all test users
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/admin/license/update",
            method="post",
            json={"laui": str(license_laui), "user_list_patch": {"add": test_user_lauis}},
        ),
    )
    assert response.status_code == 200
    yield users, license_laui


@pytest.fixture(autouse=True)
async def setup_access(
    setup_catalog, setup_users, client: TestClient, test_database: MongoDatabase
):
    pass


async def test_item_user_permission(
    client: TestClient,
    test_database: MongoDatabase,
    setup_catalog: dict[str, any],
    setup_users: tuple[dict[str, any], str],
):
    users, license_laui = setup_users
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method="post",
            json={
                "name": "project_folder",
                "parent_laui": setup_catalog["account_folder"]["laui"],
                "item_type": "folder.project",
                "account_laui": setup_catalog["account_folder"]["laui"],
                "access_patch": {"add": {"owners": {f"U{users['test_user1']['laui']}": ""}}},
            },
        ),
    )
    assert response.status_code == 200

    for user_name, user in users.items():
        for item_name, item in setup_catalog.items():
            start_time = time.perf_counter()
            response = execute_request(
                client=client,
                request=TestRequest(
                    url="/api/v1/access/get/permission",
                    method="get",
                    headers={"Cookie": f"frontend_token={user['token']}"},
                    params={"item_laui": item["laui"], "user_laui": f"{user['laui']}"},
                ),
            )
            end_time = time.perf_counter()
            execution_time = end_time - start_time

            print(f"Request took {execution_time:.4f} seconds")
            response.status_code == 200
            permission = response.json()["permission"]

            if user_name == "test_user1":
                if item_name in ["account_folder", "trash"]:
                    assert permission == "none"
                else:
                    assert permission == "own"
            elif user_name == "root_user":
                assert permission == "own"
            else:
                assert permission == "none"

    test_user_laui = users["test_user1"]["laui"]

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/access/get/access_relations",
            method="get",
        ),
    )
    assert response.status_code == 200

    user_lauis = []
    for relation in response.json()["access_relations"]:
        user_lauis.append(relation["subject_laui"])
    assert test_user_laui in user_lauis

    response = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/admin/user/delete/{test_user_laui}",
            method="delete",
        ),
    )
    assert response.status_code == 200

    await asyncio.sleep(1)

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/access/get/access_relations",
            method="get",
        ),
    )
    assert response.status_code == 200

    user_lauis = []
    for relation in response.json()["access_relations"]:
        user_lauis.append(relation["subject_laui"])
    assert test_user_laui not in user_lauis

    license = await LicenseRepository(test_database).get_license(PydanticObjectId(license_laui))

    assert PydanticObjectId(test_user_laui) not in license.user_list


"""
async def test_check_access(client:TestClient,
                            test_database:MongoDatabase,
                            setup_catalog:dict[str,any]):
    return

    # get root items of test_user_1
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get?is_root=true",
            method='get',
            headers={
                "Cookie":f"frontend_token={test_user1_token}"
            }
        )
    )
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "items":[],
        "pagination":{
            "current_page":1,
            "per_page":0,
            "has_next":False,
            "next_page_token":None
        }
    }

    # give own access of project folder to test_user_1
    assert response.status_code == 200
    data = response.json()

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get?is_root=true",
            method='get',
            headers={
                "Cookie":f"frontend_token={test_user1_token}"
            }
        )
    )
    assert response.status_code == 200
    data = response.json()

    val = check_sub_dict(
       {
        "items":[
            {
                "item":_get_item_from_setup_catalog(setup_catalog,"project_folder","own"),
                "children":[
                    {
                        "item":_get_item_from_setup_catalog(setup_catalog,"root_config_folder","own"),
                        "children":[],
                        "parents":[]
                    }
                ],
                "parents":[]
            }
        ],
        "pagination":{
            "current_page":1,
            "has_next":False,
            'per_page':10,
            'next_page_token':''
        }
       },
       data
    )

    print(val)

    assert val == True

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/access/get/permission",
            method='get',
            headers={
                "Cookie":f"frontend_token={test_user1_token}"
            },
            params={
                "item_laui":setup_catalog["account_folder"]["laui"],
                "user_email":test_user_email
            }
        )
    )
    assert response.status_code == 200
    data = response.json()
    assert data["permission"] == None

    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/access/get/permission",
            method='get',
            headers={
                "Cookie":f"frontend_token={test_user1_token}"
            },
            params={
                "item_laui":setup_catalog["project_folder"]["laui"],
                "user_email":test_user_email
            }
        )
    )
    assert response.status_code == 200
    data = response.json()
    assert data["permission"] == "own"

    # revoke access of test_user
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/create",
            method='post',
            json={
                "name":"project_folder",
                "parent_laui": setup_catalog["account_folder"]["laui"],
                "item_type":"folder.project",
                "access_patch":{"remove":{"owners":{ f'U{test_user_laui}':""}}}
            }
        )
    )
    assert response.status_code == 200


    # get root items of test_user_1
    response = execute_request(
        client=client,
        request=TestRequest(
            url="/api/v1/catalog/get?is_root=true",
            method='get',
            headers={
                "Cookie":f"frontend_token={test_user1_token}"
            }
        )
    )
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "items":[],
        "pagination":{
            "current_page":1,
            "per_page":0,
            "has_next":False,
            "next_page_token":None
        }
    }

    #get project directly
    response = execute_request(
        client=client,
        request=TestRequest(
            url=f"/api/v1/catalog/get?item_laui={setup_catalog["project_folder"]["laui"]}",
            method='get',
            headers={
                "Cookie":f"frontend_token={test_user1_token}"
            }
        )
    )
    print(response.json())
    assert response.status_code == 403
"""


async def _get_user_access_token(test_database: MongoDatabase, email: str) -> str:
    license_repo = LicenseRepository(test_database)
    license_service = LicenseService(license_repo)
    user_service = UserService(
        user_repo=UserRepository(test_database), license_service=license_service
    )
    session_service = get_session_service()
    existing_user = await user_service.get_user_by_email(email)
    return session_service.generate_access_token(user=existing_user, expires_in_hours=87600)


def _get_item_from_setup_catalog(setup_catalog: dict[str, any], name: str, perm: str):
    return {
        "name": name,
        "laui": setup_catalog[name]["laui"],
        "item_type": setup_catalog[name]["item_type"],
        "permission": perm,
    }


def _get_license_id_and_public_key(root_user_laui: str) -> LicenseUploadRequest:
    license_claims = LicenseClaims(
        permanent_seats=100,
        trial_seats=0,
        tier=LicenseTier.BUSINESS,
        instance_id=PydanticObjectId(root_user_laui),
    )
    import jwt

    license_id = jwt.encode(
        license_claims.model_dump(mode="json"), SessionService.load_private_key(), algorithm="RS256"
    )
    return LicenseUploadRequest(license_id=license_id, public_key=SessionService.load_public_key())


def _stable_key(obj):
    import json

    """Helper to create a sortable string key for complex types like dicts."""
    if isinstance(obj, dict):
        # Sort keys inside the dict for a deterministic JSON string
        return json.dumps(obj, sort_keys=True)
    return str(obj)


def check_sub_dict(dict1: dict, dict2: dict, path: str = "") -> bool | str:
    """
    Checks if dict1 is a nested subset of dict2. Accommodates and matches sorted lists.
    Returns True if it matches, or a dot-notated string path of the mismatch.
    """
    if not isinstance(dict2, dict):
        return path if path else "root"

    for key, val1 in dict1.items():
        current_path = f"{path}.{key}" if path else key

        if key not in dict2:
            return current_path

        val2 = dict2[key]

        # Case 1: Both are nested dictionaries
        if isinstance(val1, dict):
            result = check_sub_dict(val1, val2, current_path)
            if result is not True:
                return result

        # Case 2: Both are lists (Your new requirement)
        elif isinstance(val1, list) and isinstance(val2, list):
            # Sort both lists using our stable string helper
            sorted_l1 = sorted(val1, key=_stable_key)
            sorted_l2 = sorted(val2, key=_stable_key)

            # Since dict1 is a "subset", dict2 can have extra items,
            # but it MUST have at least as many items as dict1 to match.
            if len(sorted_l1) > len(sorted_l2):
                return current_path

            # Check items one-by-one at matching sorted indexes
            for i, item1 in enumerate(sorted_l1):
                item2 = sorted_l2[i]
                item_path = f"{current_path}[{i}]"

                # If the list items are dicts, do the nested check
                if isinstance(item1, dict):
                    result = check_sub_dict(item1, item2, item_path)
                    if result is not True:
                        return result
                # Otherwise, do a standard list item comparison
                elif item1 != item2:
                    return item_path

        # Case 3: Standard value mismatch
        elif val1 != val2:
            return current_path

    return True
