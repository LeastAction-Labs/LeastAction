# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
# DO NOT CHANGE thefile name(conftest.py), it automatically initializes the fixtures and
# the name is pytest specific
import os
from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient

from main import app
from src.common.env import ENV
from src.core.db.types import MongoDatabase
from tests.integration.utils import get_system_access_token, get_test_database


@pytest.fixture(autouse=True)
def setup_env():
    os.environ["ENV"] = ENV.TEST.value


# This is required for using the session scoped async fixtures as per
# https://anyio.readthedocs.io/en/stable/testing.html#using-async-fixtures-with-higher-scopes
@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture()
async def test_database() -> AsyncGenerator[MongoDatabase, None]:

    db = await get_test_database()

    existing_collections = await db.list_collection_names()
    if "links" not in existing_collections:
        await db.create_collection("links")
    await db.command({"collMod": "links", "changeStreamPreAndPostImages": {"enabled": True}})

    yield db

    await db.client_ref.close()


@pytest.fixture()
async def client():
    os.environ["ENV"] = ENV.TEST.value
    with TestClient(app) as client:
        access_token = await get_system_access_token()
        client.headers = {
            "Cookie": f"frontend_token={access_token};",
            "X-System-Auth-Token": access_token,
        }
        yield client


@pytest.fixture(scope="session")
async def unauthenticated_client():
    os.environ["ENV"] = ENV.TEST.value
    with TestClient(app) as client:
        yield client
