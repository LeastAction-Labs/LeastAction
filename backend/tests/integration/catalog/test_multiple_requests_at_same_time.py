# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import pytest

from src.core.db.types import MongoDatabase

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


"""
This testcase is there to confirm the schema manager bug exists or not
We will send 2 simulataneous create requests to create 2 different item_types

"""
