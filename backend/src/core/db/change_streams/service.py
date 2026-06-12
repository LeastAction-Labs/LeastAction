# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio
import os

import redis.asyncio as redis
from dotenv import load_dotenv

from src.common.config import Config
from src.common.context_vars.session_context import get_session_id, set_session_id
from src.common.env import ENV, get_env
from src.common.logger.logger import initialize_logger, log_info
from src.core.db.change_streams.schema import (
    AccessCreate,
    AccessPatch,
    AccessUpdate,
    ChangeStream,
    GroupPayload,
    ItemPayload,
    Link,
    LinkPayload,
)
from src.core.db.service import MongoDatabase, create_mongo_client

load_dotenv()

config = Config()
initialize_logger(config)
database_uri = os.getenv("MONGO_URI")
if get_env() == ENV.TEST:
    database_uri = os.getenv("MONGO_TEST_URI")
if not database_uri:
    raise ValueError("MONGO_URI is not set")
redis_url = os.getenv("REDIS_URL")
if not redis_url:
    raise ValueError("REDIS_URL is not set")
r = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
stream_key = "stream:events"


def items_groups_processing(change_stream: ChangeStream):

    if change_stream.operationType == "drop":
        if change_stream.collection == "items":
            return ItemPayload(action="drop")

        return GroupPayload(action="drop")

    access_patch = AccessPatch()

    if change_stream.operationType == "update":
        updated_fields = change_stream.updateDescription.updatedFields
        removed_fields = change_stream.updateDescription.removedFields

        access_update = AccessUpdate(**updated_fields)

        if access_update.access:
            if access_update.access.editors:
                editors = list(access_update.access.editors.keys())
                access_patch.editors.add.extend(editors)
            if access_update.access.viewers:
                viewers = list(access_update.access.viewers.keys())
                access_patch.viewers.add.extend(viewers)
            if access_update.access.owners:
                owners = list(access_update.access.owners.keys())
                access_patch.owners.add.extend(owners)
            if access_update.access_editors:
                access_patch.editors.add.extend(list(access_update.access_editors.keys()))
            if access_update.access_viewers:
                access_patch.viewers.add.extend(list(access_update.access_viewers.keys()))
            if access_update.access_owners:
                access_patch.owners.add.extend(list(access_update.access_owners.keys()))

        for key in updated_fields.keys():
            if key.startswith("access.editors."):
                access_patch.editors.add.append(key.split(".")[-1])
            elif key.startswith("access.viewers."):
                access_patch.viewers.add.append(key.split(".")[-1])
            elif key.startswith("access.owners."):
                access_patch.owners.add.append(key.split(".")[-1])

        for removed_field in removed_fields:
            if removed_field == "access.editors":
                access_patch.editors.remove.append("*")
            if removed_field == "access.viewers":
                access_patch.viewers.remove.append("*")
            if removed_field == "access.owners":
                access_patch.owners.remove.append("*")
            if removed_field.startswith("access.editors."):
                access_patch.editors.remove.append(removed_field.split(".")[-1])
            if removed_field.startswith("access.viewers."):
                access_patch.viewers.remove.append(removed_field.split(".")[-1])
            if removed_field.startswith("access.owners."):
                access_patch.owners.remove.append(removed_field.split(".")[-1])

    if change_stream.operationType == "insert":
        access_create = AccessCreate(**change_stream.fullDocument)
        if access_create.access.owners:
            access_patch.owners.add.extend(list(access_create.access.owners.keys()))
        if access_create.access.editors:
            access_patch.editors.add.extend(list(access_create.access.editors.keys()))
        if access_create.access.viewers:
            access_patch.viewers.add.extend(list(access_create.access.viewers.keys()))

    if change_stream.collection == "items":
        return ItemPayload(
            item_laui=str(change_stream.document_laui),
            access_patch=access_patch,
            action=change_stream.operationType,
            session_id=get_session_id(),
        )
    else:
        return GroupPayload(
            group_laui=str(change_stream.document_laui),
            access_patch=access_patch,
            action=change_stream.operationType,
            session_id=get_session_id(),
        )


def links_processing(change_stream: ChangeStream):
    link_data = change_stream.fullDocument
    if change_stream.operationType == "delete":
        link_data = change_stream.fullDocumentBeforeChange
    link = Link(**link_data)
    if not link.parent_laui:
        return
    return LinkPayload(
        item_laui=str(link.child_laui),
        parent_laui=str(link.parent_laui),
        true_parent=link.true_parent,
        action=change_stream.operationType,
    )


async def watch(active_db: MongoDatabase):
    log_info(
        "KETO",
        "change_streams",
        "status",
        f"Starting MongoDB Watcher on database: {active_db.name}",
    )

    async with await active_db.watch(
        pipeline=[], full_document_before_change="whenAvailable"
    ) as change_stream_cursor:
        log_info(
            "KETO",
            "change_streams",
            "status",
            "Successfully connected to Change Stream. Listening for changes...",
        )

        async for change in change_stream_cursor:
            try:
                collection = change.get("ns", {}).get("coll")
                doc_id = change.get("documentKey", {}).get("_id")

                cs_event = ChangeStream(**change, collection=collection, document_laui=doc_id)

                set_session_id(cs_event.session_id)
                log_info("KETO", "change_streams", "start", f"{str(cs_event.model_dump())}")

                if cs_event.collection in ["items", "groups"]:
                    payload = items_groups_processing(cs_event)

                    if (
                        payload.action in ["update", "insert"]
                        and payload.access_patch
                        and payload.access_patch.is_empty
                    ):
                        log_info(
                            "KETO",
                            "change_streams",
                            "stop",
                            f"for action: {payload.action} and collections: {cs_event.collection}, access_patch was empty so payload not sent to redis",
                        )
                        continue

                    await r.xadd(
                        stream_key, {"payload": payload.model_dump_json(exclude_none=True)}
                    )
                    log_info(
                        "KETO",
                        "change_streams",
                        "success",
                        f"{cs_event.collection[:-1]} payload: {str(payload.model_dump())} sent to Redis stream: {stream_key}",
                    )

                if cs_event.collection == "links":
                    if cs_event.operationType in ["delete", "insert"]:
                        payload = links_processing(cs_event)
                        if payload:
                            await r.xadd(stream_key, {"payload": payload.model_dump_json()})
                            log_info(
                                "KETO",
                                "change_streams",
                                "success",
                                f"link payload: {str(payload.model_dump())} sent to Redis stream: {stream_key}",
                            )
            except Exception as e:
                log_info("KETO", "change_streams", "error", f"{str(e)}")
            finally:
                set_session_id(None)


async def main():
    log_info("KETO", "change_streams", "init", "--- Service Initializing ---")
    mongo_client = await create_mongo_client(database_uri)

    db_name = "LeastAction"
    if get_env() == ENV.TEST:
        db_name = "LeastActionTest"
        log_info("KETO", "change_streams", "init", f"[TEST MODE] Using database: {db_name}")
    else:
        log_info("KETO", "change_streams", "init", f"[PROD MODE] Using database: {db_name}")

    active_db = mongo_client.get_db(db_name)
    await watch(active_db)


if __name__ == "__main__":
    asyncio.run(main())
