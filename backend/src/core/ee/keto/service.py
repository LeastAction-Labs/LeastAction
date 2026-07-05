# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import os

import httpx
from dotenv import load_dotenv
from fastapi import Request

from src.common.exceptions import AuthorizationError
from src.core.ee.keto.schema import (
    GetRelationTuplesResponse,
    RelationTuple,
    RelationTupleParams,
    RelationTupleWithAction,
)

load_dotenv()


class KetoClient:
    def __init__(self):
        self.permission_check_url = os.getenv("KETO_READ_URL") + "/check"
        self.bacth_permission_check_url = os.getenv("KETO_READ_URL") + "/batch/check"
        self.relationships_read_url = os.getenv("KETO_READ_URL")
        self.relationships_write_url = os.getenv("KETO_WRITE_URL")
        self.client = httpx.AsyncClient()

    async def __aenter__(self):
        return self

    async def __aexit__(self):
        await self.client.close()

    async def get_relations(self, relation_tuple: RelationTupleParams):
        response = await self.client.get(
            url=self.relationships_read_url,
            params=relation_tuple.model_dump(mode="json", exclude_none=True, by_alias=True),
            follow_redirects=True,
        )
        response.raise_for_status()
        return GetRelationTuplesResponse(**response.json())

    async def check_permission(self, relation_tuple: RelationTupleParams) -> bool:
        response = await self.client.get(
            url=self.permission_check_url,
            params=relation_tuple.model_dump(mode="json", exclude_none=True, by_alias=True),
            follow_redirects=True,
        )
        if response.status_code == 403:
            raise AuthorizationError(message="unauthorized")
        response.raise_for_status()

    async def batch_check_permissions(self, relation_tuples: list[RelationTuple]) -> list[bool]:

        batches = [relation_tuples[i : i + 10] for i in range(0, len(relation_tuples), 10)]

        result = []

        for batch in batches:
            response = await self.client.post(
                url=self.bacth_permission_check_url,
                json={
                    "tuples": [
                        relation_tuple.model_dump(mode="json", exclude_none=True, by_alias=True)
                        for relation_tuple in batch
                    ]
                },
                follow_redirects=True,
            )
            response.raise_for_status()
            result.extend([res["allowed"] for res in response.json()["results"]])

        return result

    async def create_relation(self, relation_tuple: RelationTuple):
        response = await self.client.put(
            url=self.relationships_write_url,
            json=relation_tuple.model_dump(mode="json"),
            follow_redirects=True,
        )
        response.raise_for_status()

    async def delete_relation(self, relation_tuple: RelationTuple):
        response = await self.client.delete(
            url=self.relationships_write_url,
            params=relation_tuple.model_dump(exclude_none=True, mode="json", by_alias=True),
            follow_redirects=True,
        )
        response.raise_for_status()

    async def patch_relations(self, relation_tuples_with_action: list[RelationTupleWithAction]):
        response = await self.client.patch(
            url=self.relationships_write_url,
            json=[
                relation_tuple_with_action.model_dump(mode="json")
                for relation_tuple_with_action in relation_tuples_with_action
            ],
            follow_redirects=True,
        )
        response.raise_for_status()


def get_keto_client(request: Request) -> KetoClient:
    return request.app.state.keto_client
