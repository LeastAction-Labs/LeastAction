# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import os
from contextlib import asynccontextmanager

from aioredlock import Aioredlock, LockError
from bson import ObjectId
from pydantic_mongo import PydanticObjectId

from src.common.exceptions import ResourceLockedError
from src.common.utils import load_system_config

cfg = load_system_config()
redis_url = cfg["celery"]["broker_url"]
redis_host = os.getenv("REDIS_HOST")
if redis_host:
    redis_url = redis_url.replace("localhost", redis_host)

pk_lock_manager = Aioredlock([redis_url])
laui_lock_manager = Aioredlock([redis_url])


@asynccontextmanager
async def lock_multiple_docs(doc_ids: list[str | PydanticObjectId | ObjectId]):

    processed_doc_ids = [str(doc_id) for doc_id in doc_ids]
    sorted_ids = sorted(set(processed_doc_ids))
    lock_keys = [f"lock:{sorted_id}" for sorted_id in sorted_ids]

    # We will store all acquired locks in a list to release them later
    acquired_locks = []

    try:
        for key in lock_keys:
            # We acquire locks one by one in the sorted order
            lock = await laui_lock_manager.lock(key, lock_timeout=30)
            acquired_locks.append(lock)

        yield

    finally:
        # 3. Release all acquired locks in REVERSE order
        # (Releasing in reverse is standard practice, though less critical than acquisition order)
        for lock in reversed(acquired_locks):
            try:
                await laui_lock_manager.unlock(lock)
            except Exception:
                # We catch exceptions during unlock so one failure doesn't
                # prevent other locks from being released.
                pass


@asynccontextmanager
async def lock_pk(pk: str):
    lock_key = f"lock:pk:{pk}"
    lock = None

    try:
        try:
            lock = await pk_lock_manager.lock(lock_key, lock_timeout=30)
        except LockError:
            raise ResourceLockedError(
                detail=f"Resource '{pk}' is currently being processed. Please try again later."
            )
        yield

    finally:
        if lock:
            try:
                await pk_lock_manager.unlock(lock)
            except Exception:
                pass
