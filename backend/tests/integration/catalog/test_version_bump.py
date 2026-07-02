# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
"""
Version rules enforced by the core /api/v1/catalog/create API (the "publish/create
item" path). The core is the universal safety net:

- creating an item with a negative/malformed version is rejected
- decreasing the version on update is rejected
- editing content while keeping or raising the version is allowed

(The "must bump exactly one step when editing a *published* item" rule lives in the
edit UI (SaveConfirmModal, which knows is_published) and in the Marketplace backend
on publish — not in the core create path, which cannot see publish state.)

Run against a dev environment with Mongo available:
    pytest tests/integration/catalog/test_version_bump.py -q
"""

import pytest
from fastapi.testclient import TestClient

from src.core.catalog.api_request import CreateItemResponse
from src.core.db.types import MongoDatabase
from tests.integration.schema import TestRequest
from tests.integration.utils import create_base_folders, execute_request

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def database_cleanup(test_database: MongoDatabase):
    await test_database.items.drop()
    await test_database.links.delete_many({})
    yield
    await test_database.items.drop()
    await test_database.links.drop()


def _make_usecase_parent(client: TestClient, base_folders) -> str:
    """A usecase must live under a folder.ai; create one and return its laui."""
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
    return CreateItemResponse(**ai_folder_response.json()).item_laui


def _publish(client: TestClient, base_folders, parent_laui: str, **overrides):
    """POST /catalog/create for a usecase named 'bump.usecase' (create or update by pk)."""
    body = {
        "item_type": "usecase",
        "name": "bump.usecase",
        "parent_laui": parent_laui,
        "account_laui": base_folders.account_folder_laui,
        "project_laui": base_folders.project_folder_laui,
    }
    body.update(overrides)
    return execute_request(
        client=client,
        request=TestRequest(url="/api/v1/catalog/create", method="post", json=body),
    )


@pytest.mark.parametrize("bad_version", ["-1.0.0", "0.-1.0", "0.0.-1"])
async def test_create_with_negative_version_rejected(
    client: TestClient, test_database: MongoDatabase, bad_version: str
):
    base_folders = create_base_folders(client)
    parent = _make_usecase_parent(client, base_folders)

    resp = _publish(
        client,
        base_folders,
        parent,
        version_details={"version": bad_version, "versioning_mode": "implicit"},
    )
    assert resp.status_code == 422
    assert "version" in str(resp.json()).lower()


@pytest.mark.parametrize("bad_version", ["1.2", "1.2.3.4", "a.b.c", "v1.0.0"])
async def test_create_with_malformed_version_rejected(
    client: TestClient, test_database: MongoDatabase, bad_version: str
):
    base_folders = create_base_folders(client)
    parent = _make_usecase_parent(client, base_folders)

    resp = _publish(
        client,
        base_folders,
        parent,
        version_details={"version": bad_version, "versioning_mode": "implicit"},
    )
    assert resp.status_code == 422


async def test_create_with_valid_version_accepted(client: TestClient, test_database: MongoDatabase):
    base_folders = create_base_folders(client)
    parent = _make_usecase_parent(client, base_folders)

    resp = _publish(
        client,
        base_folders,
        parent,
        version_details={"version": "0.1.0", "versioning_mode": "implicit"},
    )
    assert resp.status_code == 200


async def test_decrease_version_rejected(client: TestClient, test_database: MongoDatabase):
    base_folders = create_base_folders(client)
    parent = _make_usecase_parent(client, base_folders)

    created = _publish(
        client,
        base_folders,
        parent,
        version_details={"version": "0.2.0", "versioning_mode": "implicit"},
    )
    assert created.status_code == 200

    # Re-publish with a lower version -> rejected
    resp = _publish(
        client,
        base_folders,
        parent,
        description="changed",
        version_details={"version": "0.1.0", "versioning_mode": "implicit"},
    )
    assert resp.status_code == 422
    body = str(resp.json()).lower()
    assert "decrease" in body or "lower" in body


async def test_edit_content_same_version_allowed(client: TestClient, test_database: MongoDatabase):
    """Core allows editing local content without a bump (bump is enforced in the edit
    UI for published items, not in the core create path)."""
    base_folders = create_base_folders(client)
    parent = _make_usecase_parent(client, base_folders)

    created = _publish(
        client,
        base_folders,
        parent,
        description="original",
        version_details={"version": "0.1.0", "versioning_mode": "implicit"},
    )
    assert created.status_code == 200

    resp = _publish(
        client,
        base_folders,
        parent,
        description="edited, same version",
        version_details={"version": "0.1.0", "versioning_mode": "implicit"},
    )
    assert resp.status_code == 200


@pytest.mark.parametrize("bumped", ["0.1.1", "0.2.0", "1.0.0"])
async def test_edit_content_with_higher_version_allowed(
    client: TestClient, test_database: MongoDatabase, bumped: str
):
    base_folders = create_base_folders(client)
    parent = _make_usecase_parent(client, base_folders)

    created = _publish(
        client,
        base_folders,
        parent,
        description="original",
        version_details={"version": "0.1.0", "versioning_mode": "implicit"},
    )
    assert created.status_code == 200

    resp = _publish(
        client,
        base_folders,
        parent,
        description="edited and bumped",
        version_details={"version": bumped, "versioning_mode": "implicit"},
    )
    assert resp.status_code == 200
