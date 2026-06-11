# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from pydantic_mongo import PydanticObjectId
from pymongo import ASCENDING, IndexModel

from src.common.exceptions import NotFoundError
from src.common.logger.logger import log_error
from src.core.catalog.link.schema import CreateLink, CreateLinkInDB, Link
from src.core.db.transaction import session_context
from src.core.db.types import MongoDatabase


class LinkRepository:
    def __init__(self, db: MongoDatabase):
        self.db = db
        self.collection_name = "links"

    async def create_index(self):
        indexes = [
            IndexModel([("child_laui", ASCENDING), ("true_parent", ASCENDING)]),
            IndexModel([("child_laui", ASCENDING), ("parent_laui", ASCENDING)]),
            IndexModel([("parent_laui", ASCENDING), ("child_type", ASCENDING)]),
            IndexModel([("parent_laui", ASCENDING), ("true_parent", ASCENDING)]),
        ]
        await self.db[self.collection_name].create_indexes(indexes)

    async def get_link_by_pk(
        self, child_laui: PydanticObjectId, parent_laui: PydanticObjectId | None = None
    ) -> Link:
        try:
            session = session_context.get()

            link = await self.db[self.collection_name].find_one(
                {"parent_laui": parent_laui, "child_laui": child_laui}, session=session
            )

            if link is None:
                log_error(
                    "api",
                    "link_repository",
                    "find_link",
                    f"Link not found with parent_laui: {parent_laui}, child_laui: {child_laui}",
                )
                log_error(
                    "api_traceback",
                    "link_repository",
                    "find_link",
                    f"Link not found with parent_laui: {parent_laui}, child_laui: {child_laui}",
                )
                raise NotFoundError(
                    message=f"Link not found with parent_laui: {parent_laui}, child_laui: {child_laui}"
                )
            return Link(**link)
        except Exception as e:
            log_error("api", "link_repository", "find_link", str(e))
            log_error("api_traceback", "link_repository", "find_link", str(e))
            raise e

    async def create_link(self, link: CreateLink):
        try:
            session = session_context.get()
            link = CreateLinkInDB(**link.model_dump(), created_at=datetime.now(UTC))
            created_link = await self.db[self.collection_name].insert_one(
                link.model_dump(), session=session
            )
            return created_link.inserted_id
        except Exception as e:
            log_error("api", "link_repository", "create_link", str(e))
            log_error("api_traceback", "link_repository", "create_link", str(e))
            raise e

    async def find_links(self, filter: dict[str, Any], offset: int = 0, limit: int = 0):
        try:
            session = session_context.get()
            links = (
                await self.db[self.collection_name]
                .find(filter, skip=offset, limit=limit, session=session)
                .to_list(length=None)
            )
            return [Link(**link) for link in links]
        except Exception as e:
            log_error("api", "link_repository", "find_links", str(e))
            log_error("api_traceback", "link_repository", "find_links", str(e))
            raise e

    async def check_next_page_exists(
        self, filter: dict[str, Any], offset: int = 0, limit: int = 0
    ) -> bool:
        try:
            session = session_context.get()
            has_next = (
                True
                if await self.db[self.collection_name]
                .find(filter, skip=offset + limit, limit=1, session=session)
                .to_list(length=None)
                else False
            )
            return has_next
        except Exception as e:
            log_error("api", "link_repository", "check_next_page_exists", str(e))
            log_error("api_traceback", "link_repository", "check_next_page_exists", str(e))
            raise e

    async def parent_links_lookup(self, child_laui: PydanticObjectId, depth: int) -> list[Link]:
        try:
            session = session_context.get()
            pipeline = [
                {"$match": {"child_laui": child_laui, "true_parent": True}},
                {
                    "$graphLookup": {
                        "from": "links",
                        "startWith": "$parent_laui",
                        "connectFromField": "parent_laui",
                        "connectToField": "child_laui",
                        "maxDepth": depth,
                        "as": "links",
                        "restrictSearchWithMatch": {"true_parent": True},
                    }
                },
            ]

            links = await (
                await self.db[self.collection_name].aggregate(pipeline=pipeline, session=session)
            ).to_list(length=None)
            if links:
                root_link = links[0]
                sorted_links = sorted(
                    (links[0]["links"]), key=lambda item: item["created_at"], reverse=True
                )
                link_list = [Link(**root_link)]
                for link in sorted_links:
                    link_list.append(Link(**link))
                return link_list
            return []
        except Exception as e:
            log_error("api", "link_repository", "parent_links_lookup", str(e))
            log_error("api_traceback", "link_repository", "parent_links_lookup", str(e))
            raise e

    async def children_links_lookup(
        self, link_laui: PydanticObjectId, true_parent: bool | None = None
    ) -> list[Link]:
        try:
            session = session_context.get()

            graph_lookup_dict = {
                "from": "links",
                "startWith": "$child_laui",
                "connectFromField": "child_laui",
                "connectToField": "parent_laui",
                "as": "links",
            }

            if true_parent is not None:
                graph_lookup_dict["restrictSearchWithMatch"] = {"true_parent": true_parent}

            pipeline = [{"$match": {"_id": link_laui}}, {"$graphLookup": graph_lookup_dict}]

            pipeline_output = await (
                await self.db[self.collection_name].aggregate(pipeline=pipeline, session=session)
            ).to_list(length=None)
            if pipeline_output:
                result = []
                for link in pipeline_output[0]["links"]:
                    result.append(Link(**link))
                return result
            return []
        except Exception as e:
            log_error("api", "link_repository", "child_links_lookup", str(e))
            log_error("api_traceback", "link_repository", "child_links_lookup", str(e))
            raise e

    async def delete_links(self, link_lauis: list[PydanticObjectId]):
        try:
            session = session_context.get()
            await self.db[self.collection_name].delete_many(
                {"_id": {"$in": link_lauis}}, session=session
            )
        except Exception as e:
            log_error("api", "link_repository", "delete_links", str(e))
            log_error("api_traceback", "link_repository", "delete_links", str(e))
            raise e


def get_link_repository(request: Request):
    return request.app.state.link_repository
