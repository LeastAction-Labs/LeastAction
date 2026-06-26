# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from fastapi import Request

from src.core.db.types import MongoClient, MongoDatabase


class MongoDBClient:
    def __init__(self, uri: str):
        self.client: MongoClient = MongoClient(uri)

    async def close_connection(self):
        return await self.client.close()

    async def ping(self):
        await self.client.admin.command("ping")

    def get_db(self, db: str = "LeastAction") -> MongoDatabase:
        return self.client[db]

    async def cleanup_db(self, db: str = "LeastAction"):
        db = self.get_db()
        collections = await db.list_collection_names()
        for collection in collections:
            if collection != "users":
                await db[collection].delete_many({})


async def create_mongo_client(uri: str) -> MongoDBClient:
    client = MongoDBClient(uri)
    try:
        await client.ping()
    except Exception as e:
        print("Failed to connect to the mongodb", e)
        raise e
    return client


def get_mongo_client(request: Request) -> MongoDBClient:
    return request.app.state.mongo_client
