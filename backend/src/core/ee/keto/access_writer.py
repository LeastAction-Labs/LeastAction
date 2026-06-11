# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import asyncio
import json
import os

import redis.asyncio as redis
from dotenv import load_dotenv
from pydantic import ValidationError

from src.common.config import Config
from src.common.context_vars.session_context import set_session_id
from src.common.logger.logger import initialize_logger, log_info
from src.core.db.change_streams.schema import AccessPatch, GroupPayload, ItemPayload, LinkPayload
from src.core.ee.keto.schema import (
    Action,
    Namespace,
    Relation,
    RelationTuple,
    RelationTupleWithAction,
    SubjectSet,
)
from src.core.ee.keto.service import KetoClient

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
STREAM_KEY = "stream:events"
CONSUMER_GROUP = "group:data_processors"
CONSUMER_NAME = f"worker-{os.getpid()}"

r = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)

load_dotenv()
config = Config()
initialize_logger(config)
keto_client = KetoClient()


async def process_link_payload(link_payload: LinkPayload):
    if link_payload.action == "insert":
        relation_tuple = RelationTuple(
            namespace=Namespace.ITEM,
            object=link_payload.item_laui,
            relation=Relation.TRUE_PARENT if link_payload.true_parent else Relation.FALSE_PARENTS,
            subject_set=SubjectSet(
                namespace=Namespace.ITEM, object=link_payload.parent_laui, relation=""
            ),
        )
        await keto_client.create_relation(relation_tuple)
    else:
        relation_tuple = RelationTuple(
            namespace=Namespace.ITEM,
            object=link_payload.item_laui,
            relation=Relation.TRUE_PARENT if link_payload.true_parent else Relation.FALSE_PARENTS,
            subject_id=link_payload.parent_laui,
        )
        await keto_client.delete_relation(relation_tuple)


def _get_access_relation_tuples(
    object_laui: str, object_namespace: str, subject_laui: str, relation: Relation
) -> list[RelationTuple]:

    if not subject_laui.startswith("G"):
        return [
            RelationTuple(
                namespace=object_namespace,
                relation=relation,
                object=object_laui,
                subject_id=subject_laui[1:],
            )
        ]

    target_relations = [Relation.OWNERS, Relation.EDITORS, Relation.VIEWERS]

    result = []

    for rel in target_relations:
        result.append(
            RelationTuple(
                namespace=object_namespace,
                relation=relation,
                object=object_laui,
                subject_set=SubjectSet(
                    namespace=Namespace.GROUP, relation=rel, object=subject_laui[1:]
                ),
            )
        )

    return result


async def process_access_patch(access_patch: AccessPatch, object_laui: str, object_namespace: str):
    relation_tuples_with_action: list[RelationTupleWithAction] = []

    mapping = [
        (access_patch.owners, Relation.OWNERS),
        (access_patch.editors, Relation.EDITORS),
        (access_patch.viewers, Relation.VIEWERS),
    ]

    for patch_group, relation in mapping:
        for laui in patch_group.add:
            tuples = _get_access_relation_tuples(object_laui, object_namespace, laui, relation)
            relation_tuples_with_action.extend(
                [RelationTupleWithAction(action=Action.INSERT, relation_tuple=t) for t in tuples]
            )

        for laui in patch_group.remove:
            tuples = _get_access_relation_tuples(object_laui, object_namespace, laui, relation)
            relation_tuples_with_action.extend(
                [RelationTupleWithAction(action=Action.DELETE, relation_tuple=t) for t in tuples]
            )

    if relation_tuples_with_action:
        await keto_client.patch_relations(relation_tuples_with_action)


async def process_item_payload(item_payload: ItemPayload):
    if item_payload.action == "delete":
        await keto_client.delete_relation(
            relation_tuple=RelationTuple(namespace=Namespace.ITEM, object=item_payload.item_laui)
        )
        return

    elif item_payload.action == "drop":
        await keto_client.delete_relation(relation_tuple=RelationTuple(namespace=Namespace.ITEM))
        return

    await process_access_patch(
        access_patch=item_payload.access_patch,
        object_laui=item_payload.item_laui,
        object_namespace=Namespace.ITEM,
    )


async def process_group_payload(group_payload: GroupPayload):
    if group_payload.action == "delete":
        await keto_client.delete_relation(
            relation_tuple=RelationTuple(namespace=Namespace.GROUP, object=group_payload.group_laui)
        )
        return
    elif group_payload.action == "drop":
        await keto_client.delete_relation(relation_tuple=RelationTuple(namespace=Namespace.GROUP))
        return
    await process_access_patch(
        access_patch=group_payload.access_patch,
        object_laui=group_payload.group_laui,
        object_namespace=Namespace.GROUP,
    )


async def process_payload(payload: dict[str, any], payload_type: str):
    log_info("KETO", "access_writer", "processing", f"Payload breakdown: {json.dumps(payload)}")
    if payload_type == "item":
        await process_item_payload(ItemPayload(**payload))
    elif payload_type == "link":
        await process_link_payload(LinkPayload(**payload))
    else:
        await process_group_payload(GroupPayload(**payload))


async def process_job(msg_id, data):
    try:
        payload = json.loads(data["payload"])

        set_session_id(payload.get("session_id"))
        log_info(
            "KETO",
            "access_writer",
            "start",
            f"[{CONSUMER_NAME}] Started processing task | ID: {msg_id}",
        )

        payload_type = payload.get("payload_type")
        if payload_type not in ["link", "item", "group"]:
            raise KeyError(f"Unsupported payload type: {payload_type}")

        await process_payload(payload, payload_type)
        log_info("KETO", "access_writer", "success", f"Message {msg_id} processed fully.")

    except KeyError as e:
        log_info("KETO", "access_writer", "error", f"Malformed data in {msg_id}: {e}")
    except ValidationError as e:
        log_info("KETO", "access_writer", "validation_error", f"Failure in {msg_id} | Details: {e}")
    finally:
        set_session_id(None)


async def main():
    log_info("KETO", "access_writer", "init", f"Starting {CONSUMER_NAME} worker...")

    try:
        await r.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True)
        log_info("KETO", "access_writer", "init", f"Consumer group '{CONSUMER_GROUP}' initialized.")
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            log_info("KETO", "access_writer", "critical", f"Redis error: {e}")
            raise e
        log_info(
            "KETO",
            "access_writer",
            "init",
            f"Consumer group '{CONSUMER_GROUP}' exists. Resuming...",
        )

    while True:
        try:
            streams = await r.xreadgroup(
                CONSUMER_GROUP, CONSUMER_NAME, {STREAM_KEY: ">"}, count=1, block=2000
            )

            if not streams:
                continue

            for _stream, messages in streams:
                for msg_id, msg_data in messages:
                    await process_job(msg_id, msg_data)
                    await r.xack(STREAM_KEY, CONSUMER_GROUP, msg_id)
                    log_info("KETO", "access_writer", "ack", f"Message {msg_id} acknowledged.")

        except Exception as e:
            log_info("KETO", "access_writer", "error", f"Worker runtime exception: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_info("KETO", "access_writer", "init", "KeyboardInterrupt: Worker stopping...")
# delete , insert , update

# documentKey and _id is there to get the item id , 'ns' -> { 'db' and 'coll' , db and collections name} # so we are concerned about mostly the items and users table
# what about soft links , how will u handle that when a soft link will get created i will get it and create a relation between the child item and the false_parents
# this is simple


# when an item gets created then we will create 2 relation tuples.
# parent_laui is true_parent of item_laui
# get the access field and use it to get the owner of the item
# access.owner is owner of item_laui

# when an item gets updated then we are only concerned about change in the access field
# documentKey._id will give us the item_laui
# then we have updateDescription field , we will use that
# i think process the data and cleaning up the data on the sender is side cleaner then doing it on the listener side , this way we will not be sending unnecessary data to queue.

# only take soft links
# or we can take both and take only access field from items.

# when user gets deleted then we will delete all the groups and items owned by him.

# all the editors and viewers field will look like this --> editors : {"x" : 1 }  this is better then using a list
# so we are only concerned about
